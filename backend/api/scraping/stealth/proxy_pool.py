"""backend/api/scraping/stealth/proxy_pool.py — Advanced proxy management with health checks."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class ProxyPool:
    """Round-robin proxy pool with dead-proxy detection and automatic recovery."""

    _DEAD_TTL_SECONDS: int = 300  # 5 minutes

    def __init__(self, proxy_list: list[str], *, healthcheck_url: str) -> None:
        self._proxies: list[str] = list(proxy_list)
        self._healthcheck_url = healthcheck_url
        self._dead: dict[str, float] = {}  # proxy → expiry timestamp
        self._index: int = 0
        self._bg_task: asyncio.Task | None = None

    async def get_proxy(self) -> Optional[str]:
        """Return the next healthy proxy in round-robin order, or None if all are dead."""
        if not self._proxies:
            return None
        now = time.time()
        # Expire dead-proxy records whose TTL has passed
        self._dead = {p: t for p, t in self._dead.items() if t > now}
        healthy = [p for p in self._proxies if p not in self._dead]
        if not healthy:
            return None  # All proxies dead — fall back to direct
        proxy = healthy[self._index % len(healthy)]
        self._index = (self._index + 1) % len(healthy)
        return proxy

    async def mark_dead(self, proxy: str) -> None:
        """Blacklist a proxy for _DEAD_TTL_SECONDS seconds."""
        self._dead[proxy] = time.time() + self._DEAD_TTL_SECONDS

    async def health_check_all(self) -> None:
        """Check each proxy against the configured health endpoint and resurrect recovered proxies."""
        import httpx
        for proxy in list(self._proxies):
            try:
                async with httpx.AsyncClient(proxy=proxy, timeout=5.0) as client:
                    resp = await client.get(self._healthcheck_url)
                    if resp.status_code == 200 and proxy in self._dead:
                        del self._dead[proxy]
            except Exception:
                await self.mark_dead(proxy)

    def start_background_healthcheck(self, interval_seconds: int = 300) -> asyncio.Task:
        """Start a background asyncio task that periodically health-checks all proxies."""
        async def _loop() -> None:
            try:
                while True:
                    await asyncio.sleep(interval_seconds)
                    await self.health_check_all()
                    now = time.time()
                    alive = [p for p in self._proxies if p not in self._dead or self._dead[p] <= now]
                    dead_count = len(self._proxies) - len(alive)
                    logger.info(
                        "[proxy_pool] healthcheck: %d alive, %d dead",
                        len(alive),
                        dead_count,
                    )
            except asyncio.CancelledError:
                logger.info("[proxy_pool] background healthcheck cancelled")
                return

        self._bg_task = asyncio.create_task(_loop(), name="proxy_healthcheck")
        return self._bg_task


# Module-level singleton — lazy-initialised from settings on first use
_pool_instance: Optional[ProxyPool] = None


def _get_pool() -> Optional[ProxyPool]:
    global _pool_instance
    if _pool_instance is None:
        from api.config import settings
        proxies = settings.SCRAPING_PROXY_LIST
        if proxies:
            _pool_instance = ProxyPool(
                proxies,
                healthcheck_url=settings.SCRAPING_PROXY_HEALTH_CHECK_URL,
            )
    return _pool_instance


async def get_proxy() -> Optional[str]:
    """Return next healthy proxy, or None (falls back to direct connection)."""
    pool = _get_pool()
    if pool is None:
        return None
    return await pool.get_proxy()


async def mark_proxy_dead(proxy: str) -> None:
    """Mark a proxy as dead in the module-level pool."""
    pool = _get_pool()
    if pool is not None:
        await pool.mark_dead(proxy)
