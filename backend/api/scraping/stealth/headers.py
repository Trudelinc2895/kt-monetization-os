"""backend/api/scraping/stealth/headers.py — Stable browser fingerprint profiles."""
from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Optional

_PROFILES: dict[str, dict[str, object]] = {
    "chrome-windows": {
        "name": "chrome-windows",
        "ua": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "accept_language": "en-US,en;q=0.9",
        "locale": "en-US",
        "languages": ["en-US", "en"],
        "sec_ch_ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec_ch_ua_platform": '"Windows"',
        "platform": "Win32",
        "webgl_vendor": "Intel Inc.",
        "webgl_renderer": "Intel Iris OpenGL Engine",
        "canvas_shift": 1,
    },
    "chrome-macos": {
        "name": "chrome-macos",
        "ua": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ),
        "accept_language": "en-US,en;q=0.9",
        "locale": "en-US",
        "languages": ["en-US", "en"],
        "sec_ch_ua": '"Chromium";v="123", "Google Chrome";v="123", "Not-A.Brand";v="99"',
        "sec_ch_ua_platform": '"macOS"',
        "platform": "MacIntel",
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple GPU",
        "canvas_shift": 1,
    },
    "firefox-linux": {
        "name": "firefox-linux",
        "ua": "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "accept_language": "en-US,en;q=0.5",
        "locale": "en-US",
        "languages": ["en-US", "en"],
        "sec_ch_ua": "",
        "sec_ch_ua_platform": "",
        "platform": "Linux x86_64",
        "webgl_vendor": "Intel Open Source Technology Center",
        "webgl_renderer": "Mesa DRI Intel(R) UHD Graphics 620",
        "canvas_shift": 1,
    },
}
_DEFAULT_PROFILE = "chrome-windows"


def available_stealth_profiles() -> list[str]:
    return list(_PROFILES.keys())


def get_stealth_profile(*, profile_name: str | None = None, seed: str | None = None) -> dict[str, object]:
    if profile_name and profile_name not in {"", "auto"}:
        profile = _PROFILES.get(profile_name)
        if profile is None:
            raise ValueError(f"Unknown stealth profile: {profile_name}")
        return deepcopy(profile)

    if not seed:
        return deepcopy(_PROFILES[_DEFAULT_PROFILE])

    names = available_stealth_profiles()
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], byteorder="big") % len(names)
    return deepcopy(_PROFILES[names[index]])


def build_stealth_headers(
    profile: Optional[dict[str, object]] = None,
    *,
    profile_name: str | None = None,
    seed: str | None = None,
) -> dict[str, str]:
    p = profile if profile is not None else get_stealth_profile(profile_name=profile_name, seed=seed)
    headers: dict[str, str] = {
        "User-Agent": str(p["ua"]),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": str(p["accept_language"]),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
    }
    if p.get("sec_ch_ua"):
        headers["Sec-CH-UA"] = str(p["sec_ch_ua"])
        headers["Sec-CH-UA-Mobile"] = "?0"
        headers["Sec-CH-UA-Platform"] = str(p["sec_ch_ua_platform"])
    return headers
