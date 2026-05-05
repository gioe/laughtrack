"""Resolve and cache the residential-proxy egress IP per scraper-key per run.

When a residential-proxy fetch returns ``None`` the existing WARN tells
on-call that a proxied request failed but not whether the egress IP itself
was blocked vs. the target being down or 5xx-ing. This module captures the
egress IP on the *first* None-fetch per scraper-key per run by routing a
tiny GET through the same ``RESIDENTIAL_PROXY_URL``, so on-call can
cross-check against Decodo's dashboard or known-block lists.

Caching strategy
----------------
The cache is keyed by scraper key and lives for the lifetime of the
process. Subsequent failures for the same key reuse the cached IP without
re-resolving — a long nightly scrape that hits hundreds of proxied URLs
only burns one extra round-trip per scraper. Concurrent worker loops may
briefly race into the cold-cache path; a duplicate resolve is harmless
(both calls produce the same answer) and the alternative (locking the
network call) would serialise unrelated scrapers.

Failure modes
-------------
* Network error / non-200 from the IP echo service → cache the
  ``"<unresolved>"`` sentinel. Subsequent failures for the same key still
  log the sentinel rather than falling back to a re-resolve loop, so a
  globally broken egress doesn't multiply log noise.
* ``proxy_url`` empty/None or ``scraper_key`` empty → return ``None``
  without caching or making any network call. Today the existing call
  sites already gate on ``residential_was_auto_applied``, but the
  defensive check keeps the helper safe to use elsewhere.
"""

from __future__ import annotations

import threading
from typing import Dict, Optional

from curl_cffi.requests import AsyncSession

UNRESOLVED = "<unresolved>"
_IP_ECHO_URL = "https://api.ipify.org"
_IP_ECHO_TIMEOUT_SEC = 5

_lock = threading.Lock()
_cache: Dict[str, str] = {}


async def resolve_egress_ip(
    scraper_key: Optional[str], proxy_url: Optional[str]
) -> Optional[str]:
    """Return the residential egress IP for *scraper_key*, cached per run.

    First call for a key issues a GET to the IP echo service through
    *proxy_url* and caches the result. Subsequent calls for the same key
    return the cached value without re-resolving. Returns ``None`` (no
    network call, no cache write) when *proxy_url* is empty or
    *scraper_key* is empty.
    """
    if not scraper_key or not proxy_url:
        return None
    with _lock:
        cached = _cache.get(scraper_key)
    if cached is not None:
        return cached
    resolved = await _fetch_egress_ip(proxy_url)
    with _lock:
        return _cache.setdefault(scraper_key, resolved or UNRESOLVED)


async def _fetch_egress_ip(proxy_url: str) -> Optional[str]:
    """Issue a single GET through *proxy_url* and return the egress IP string.

    Returns ``None`` on any failure (network error, non-200, empty body)
    so the caller can substitute the ``"<unresolved>"`` sentinel —
    distinguishing "we tried and failed" from "we never tried" in logs.
    """
    proxies = {"http": proxy_url, "https": proxy_url}
    try:
        async with AsyncSession() as session:
            response = await session.get(
                _IP_ECHO_URL,
                proxies=proxies,
                timeout=_IP_ECHO_TIMEOUT_SEC,
            )
            if response.status_code == 200 and response.text:
                return response.text.strip()
    except Exception:
        # The egress IP is a diagnostic signal, not a hard requirement —
        # any failure (timeout, DNS, malformed response) just means we log
        # "<unresolved>" so the rest of the WARN still surfaces normally.
        pass
    return None


def reset_cache() -> None:
    """Clear the per-process egress IP cache. Test-only."""
    with _lock:
        _cache.clear()
