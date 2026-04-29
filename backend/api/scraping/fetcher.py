from __future__ import annotations

import asyncio
import logging
import random
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from api.config import settings
from api.scraping.security import validate_redirect, validate_safe_url

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
except Exception:  # pragma: no cover
    async_playwright = None

# Bot-detection page keywords
_BOT_DETECTION_KEYWORDS = (
    "captcha",
    "challenge",
    "verify you are human",
    "cf-browser-verification",
    "cloudflare ray id",
    "please verify you",
    "attention required",
    "ddos-guard",
    "just a moment",
)


def _check_content_safety(html: str, url: str) -> bool:
    """Return False if the response looks like a bot-detection page."""
    lower = html.lower()
    for keyword in _BOT_DETECTION_KEYWORDS:
        if keyword in lower:
            logger.warning(
                "[fetcher] bot_detection_page detected url=%s keyword=%r",
                url,
                keyword,
            )
            return False
    return True


class BrowserPool:
    def __init__(self, size: int) -> None:
        self._sem = asyncio.Semaphore(size)
        self._pw = None
        self._browser = None
        self._last_used: float = 0.0
        self._zombie_task: asyncio.Task | None = None

    async def _ensure_browser(self):
        if async_playwright is None:
            raise HTTPException(status_code=503, detail="Playwright not installed")
        if self._browser is None:
            self._pw = await asyncio.wait_for(async_playwright().start(), timeout=30)
            self._browser = await asyncio.wait_for(
                self._pw.chromium.launch(headless=True), timeout=30
            )
        return self._browser

    async def _close_browser(self) -> None:
        """Close and reset the browser instance."""
        try:
            if self._browser is not None:
                await self._browser.close()
        except Exception:
            pass
        finally:
            self._browser = None
        try:
            if self._pw is not None:
                await self._pw.stop()
        except Exception:
            pass
        finally:
            self._pw = None

    async def _zombie_killer(self) -> None:
        """Background task: close browsers idle for > 10 minutes every 5 minutes."""
        while True:
            try:
                await asyncio.sleep(300)  # check every 5 minutes
                if self._browser is not None:
                    idle_seconds = time.monotonic() - self._last_used
                    if idle_seconds > 600:  # 10 minutes idle
                        logger.info(
                            "[fetcher] zombie_killer closing idle browser idle=%.0fs",
                            idle_seconds,
                        )
                        await self._close_browser()
            except asyncio.CancelledError:
                logger.info("[fetcher] zombie_killer cancelled")
                return
            except Exception as exc:
                logger.warning("[fetcher] zombie_killer error: %s", exc)

    def start_zombie_killer(self) -> asyncio.Task:
        """Start the background zombie-killer task."""
        self._zombie_task = asyncio.create_task(self._zombie_killer(), name="playwright_zombie_killer")
        return self._zombie_task

    @asynccontextmanager
    async def page(self) -> AsyncIterator:
        async with self._sem:
            browser = await self._ensure_browser()
            context = await asyncio.wait_for(browser.new_context(), timeout=30)
            page = await asyncio.wait_for(context.new_page(), timeout=15)
            self._last_used = time.monotonic()
            try:
                yield page
            finally:
                self._last_used = time.monotonic()
                try:
                    await page.close()
                except Exception:
                    pass
                try:
                    await context.close()
                except Exception:
                    pass


_browser_pool = BrowserPool(settings.SCRAPING_BROWSER_POOL_SIZE)


def _choose_proxy() -> str | None:
    if not settings.SCRAPING_PROXY_ROTATION_ENABLED:
        return None
    proxies = settings.SCRAPING_PROXY_LIST
    if not proxies:
        return None
    return random.choice(proxies)


async def _choose_proxy_stealth() -> str | None:
    """Return a proxy using the stealth ProxyPool (round-robin + dead detection)."""
    if not settings.SCRAPING_PROXY_ROTATION_ENABLED:
        return None
    from api.scraping.stealth.proxy_pool import get_proxy
    return await get_proxy()


async def _sleep_jitter() -> None:
    if settings.SCRAPING_JITTER_MAX_MS <= 0:
        return
    if settings.SCRAPING_STEALTH_MODE:
        from api.scraping.stealth.behavior import human_jitter
        await human_jitter(settings.SCRAPING_JITTER_MIN_MS, settings.SCRAPING_JITTER_MAX_MS)
    else:
        ms = random.randint(settings.SCRAPING_JITTER_MIN_MS, settings.SCRAPING_JITTER_MAX_MS)
        await asyncio.sleep(ms / 1000.0)


def _validate_content_type(content_type_header: str) -> str:
    header = (content_type_header or "").split(";", 1)[0].strip().lower()
    if not header:
        raise HTTPException(status_code=415, detail="Missing content-type")
    if header not in settings.SCRAPING_ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported content-type: {header}")
    return header


async def _fetch_http(normalized_url: str) -> tuple[int, str, str]:
    timeout = httpx.Timeout(settings.SCRAPING_TIMEOUT_SECONDS)

    if settings.SCRAPING_STEALTH_MODE and settings.SCRAPING_PROXY_ROTATION_ENABLED:
        proxy = await _choose_proxy_stealth()
    else:
        proxy = _choose_proxy()

    if settings.SCRAPING_STEALTH_MODE and settings.SCRAPING_STEALTH_HEADER_ROTATION:
        from api.scraping.stealth.headers import build_stealth_headers
        req_headers = build_stealth_headers()
    else:
        req_headers = {"User-Agent": settings.SCRAPING_USER_AGENT}

    current_url = normalized_url

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, proxy=proxy) as client:
        for _ in range(settings.SCRAPING_MAX_REDIRECTS + 1):
            try:
                response = await client.get(current_url, headers=req_headers)
            except Exception as exc:
                if settings.SCRAPING_STEALTH_MODE and proxy:
                    from api.scraping.stealth.proxy_pool import mark_proxy_dead
                    await mark_proxy_dead(proxy)
                raise exc
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location", "")
                if not location:
                    raise HTTPException(status_code=502, detail="Redirect without location")
                current_url = validate_redirect(current_url, location)
                continue

            content_type = _validate_content_type(response.headers.get("content-type", ""))
            body_bytes = response.content
            if len(body_bytes) > settings.SCRAPING_MAX_RESPONSE_BYTES:
                raise HTTPException(status_code=413, detail="Response too large")
            await _sleep_jitter()
            return response.status_code, content_type, body_bytes.decode("utf-8", errors="replace")

    raise HTTPException(status_code=508, detail="Too many redirects")


async def _fetch_playwright(normalized_url: str) -> tuple[int, str, str]:
    await _sleep_jitter()
    proxy = _choose_proxy()
    if proxy:
        logger.warning("Proxy rotation with Playwright uses HTTP path fallback for this request")
        return await _fetch_http(normalized_url)

    async with _browser_pool.page() as page:
        if settings.SCRAPING_STEALTH_MODE:
            from api.scraping.stealth.fingerprint import apply_stealth_patches
            await apply_stealth_patches(page)

        response = await page.goto(
            normalized_url,
            wait_until="domcontentloaded",
            timeout=int(settings.SCRAPING_TIMEOUT_SECONDS * 1000),
        )
        final_url = page.url
        safe_final = validate_safe_url(final_url)
        if urlsplit(safe_final).hostname != urlsplit(final_url).hostname:
            raise HTTPException(status_code=403, detail="Redirect target blocked")

        if settings.SCRAPING_STEALTH_MODE and settings.SCRAPING_STEALTH_SCROLL_SIMULATE:
            from api.scraping.stealth.behavior import simulate_scroll
            await simulate_scroll(page)

        html = await page.content()

        # Check for bot-detection pages
        if not _check_content_safety(html, normalized_url):
            if settings.SCRAPING_STEALTH_MODE and settings.SCRAPING_PROXY_ROTATION_ENABLED:
                from api.scraping.stealth.proxy_pool import mark_proxy_dead, get_proxy
                burned_proxy = await get_proxy()
                if burned_proxy:
                    await mark_proxy_dead(burned_proxy)
            raise HTTPException(status_code=403, detail="Bot detection page — request blocked")

        body_bytes = html.encode("utf-8", errors="replace")
        if len(body_bytes) > settings.SCRAPING_MAX_RESPONSE_BYTES:
            raise HTTPException(status_code=413, detail="Response too large")

        status_code = 200 if response is None else response.status
        return status_code, "text/html", html


async def fetch_url(normalized_url: str, *, render_js: bool) -> tuple[int, str, str, str]:
    if render_js:
        code, content_type, body = await _fetch_playwright(normalized_url)
        return code, content_type, body, "playwright"

    code, content_type, body = await _fetch_http(normalized_url)
    return code, content_type, body, "http"



def _choose_proxy() -> str | None:
    if not settings.SCRAPING_PROXY_ROTATION_ENABLED:
        return None
    proxies = settings.SCRAPING_PROXY_LIST
    if not proxies:
        return None
    return random.choice(proxies)


async def _choose_proxy_stealth() -> str | None:
    """Return a proxy using the stealth ProxyPool (round-robin + dead detection)."""
    if not settings.SCRAPING_PROXY_ROTATION_ENABLED:
        return None
    from api.scraping.stealth.proxy_pool import get_proxy
    return await get_proxy()


async def _sleep_jitter() -> None:
    if settings.SCRAPING_JITTER_MAX_MS <= 0:
        return
    if settings.SCRAPING_STEALTH_MODE:
        from api.scraping.stealth.behavior import human_jitter
        await human_jitter(settings.SCRAPING_JITTER_MIN_MS, settings.SCRAPING_JITTER_MAX_MS)
    else:
        ms = random.randint(settings.SCRAPING_JITTER_MIN_MS, settings.SCRAPING_JITTER_MAX_MS)
        await asyncio.sleep(ms / 1000.0)


def _validate_content_type(content_type_header: str) -> str:
    header = (content_type_header or "").split(";", 1)[0].strip().lower()
    if not header:
        raise HTTPException(status_code=415, detail="Missing content-type")
    if header not in settings.SCRAPING_ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported content-type: {header}")
    return header


async def _fetch_http(normalized_url: str) -> tuple[int, str, str]:
    timeout = httpx.Timeout(settings.SCRAPING_TIMEOUT_SECONDS)

    if settings.SCRAPING_STEALTH_MODE and settings.SCRAPING_PROXY_ROTATION_ENABLED:
        proxy = await _choose_proxy_stealth()
    else:
        proxy = _choose_proxy()

    if settings.SCRAPING_STEALTH_MODE and settings.SCRAPING_STEALTH_HEADER_ROTATION:
        from api.scraping.stealth.headers import build_stealth_headers
        req_headers = build_stealth_headers()
    else:
        req_headers = {"User-Agent": settings.SCRAPING_USER_AGENT}

    current_url = normalized_url

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, proxy=proxy) as client:
        for _ in range(settings.SCRAPING_MAX_REDIRECTS + 1):
            try:
                response = await client.get(current_url, headers=req_headers)
            except Exception as exc:
                if settings.SCRAPING_STEALTH_MODE and proxy:
                    from api.scraping.stealth.proxy_pool import mark_proxy_dead
                    await mark_proxy_dead(proxy)
                raise exc
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location", "")
                if not location:
                    raise HTTPException(status_code=502, detail="Redirect without location")
                current_url = validate_redirect(current_url, location)
                continue

            content_type = _validate_content_type(response.headers.get("content-type", ""))
            body_bytes = response.content
            if len(body_bytes) > settings.SCRAPING_MAX_RESPONSE_BYTES:
                raise HTTPException(status_code=413, detail="Response too large")
            await _sleep_jitter()
            return response.status_code, content_type, body_bytes.decode("utf-8", errors="replace")

    raise HTTPException(status_code=508, detail="Too many redirects")


async def _fetch_playwright(normalized_url: str) -> tuple[int, str, str]:
    await _sleep_jitter()
    proxy = _choose_proxy()
    if proxy:
        logger.warning("Proxy rotation with Playwright uses HTTP path fallback for this request")
        return await _fetch_http(normalized_url)

    async with _browser_pool.page() as page:
        if settings.SCRAPING_STEALTH_MODE:
            from api.scraping.stealth.fingerprint import apply_stealth_patches
            await apply_stealth_patches(page)

        response = await page.goto(
            normalized_url,
            wait_until="domcontentloaded",
            timeout=int(settings.SCRAPING_TIMEOUT_SECONDS * 1000),
        )
        final_url = page.url
        safe_final = validate_safe_url(final_url)
        if urlsplit(safe_final).hostname != urlsplit(final_url).hostname:
            raise HTTPException(status_code=403, detail="Redirect target blocked")

        if settings.SCRAPING_STEALTH_MODE and settings.SCRAPING_STEALTH_SCROLL_SIMULATE:
            from api.scraping.stealth.behavior import simulate_scroll
            await simulate_scroll(page)

        html = await page.content()
        body_bytes = html.encode("utf-8", errors="replace")
        if len(body_bytes) > settings.SCRAPING_MAX_RESPONSE_BYTES:
            raise HTTPException(status_code=413, detail="Response too large")

        status_code = 200 if response is None else response.status
        return status_code, "text/html", html


async def fetch_url(normalized_url: str, *, render_js: bool) -> tuple[int, str, str, str]:
    if render_js:
        code, content_type, body = await _fetch_playwright(normalized_url)
        return code, content_type, body, "playwright"

    code, content_type, body = await _fetch_http(normalized_url)
    return code, content_type, body, "http"

