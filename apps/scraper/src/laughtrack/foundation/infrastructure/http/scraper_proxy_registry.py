"""Cached registry of scraper keys configured to use the residential proxy.

The ``scrapers`` table (created in
``20260504143000_add_scrapers_table``) is the source of truth: any row with
``use_residential_proxy = true`` will route through ``RESIDENTIAL_PROXY_URL``
when ``HttpClient.fetch_html`` is called with that scraper key.

Loading strategy
----------------
The set is loaded lazily on first access and cached for the lifetime of the
process — same shape as ``ProxyPool.from_env()``: configuration that doesn't
need to change mid-run, fetched once to keep per-fetch overhead at zero.

Failure modes
-------------
* DB unreachable / table missing / query failure → log a WARN and return
  an empty set so the scraper keeps running with no scrapers proxied. The
  alternative (raising) would take the entire nightly run down whenever
  Neon auto-suspends — the proxy is an optimisation, not a hard dependency.
* Test isolation → ``reset_cache()`` clears the cached set so each test
  starts from a known-empty cache.
"""

from __future__ import annotations

import os
import threading
from typing import FrozenSet, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger

_lock = threading.Lock()
_cached_keys: Optional[FrozenSet[str]] = None


def _load_from_db() -> FrozenSet[str]:
    """Query the ``scrapers`` table for keys with ``use_residential_proxy = true``.

    Returns an empty frozenset on any failure (missing table, DB unreachable,
    config not loaded) and logs a WARN so the operator still sees the
    degradation in nightly logs.
    """
    try:
        # Imported here to keep this module importable from tests that don't
        # set up the full ConfigManager environment.
        from laughtrack.infrastructure.database.connection import create_connection

        conn = create_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT key FROM scrapers WHERE use_residential_proxy = TRUE"
                )
                rows = cursor.fetchall()
        finally:
            conn.close()
        return frozenset(row[0] for row in rows)
    except Exception as exc:
        Logger.warn(
            f"[ScraperProxyRegistry] failed to load proxy allowlist from DB: "
            f"{exc}. No scrapers will route through the residential proxy "
            f"this run.",
            {},
        )
        return frozenset()


def proxy_enabled_keys() -> FrozenSet[str]:
    """Return the cached set of scraper keys with ``use_residential_proxy=true``.

    First call queries the DB; subsequent calls return the cached set.
    Thread-safe so that concurrent worker loops racing into the cold-cache
    path don't issue duplicate queries.
    """
    global _cached_keys
    if _cached_keys is not None:
        return _cached_keys
    with _lock:
        if _cached_keys is None:
            _cached_keys = _load_from_db()
        return _cached_keys


def reset_cache() -> None:
    """Clear the cached set. Test-only — production code should not call this."""
    global _cached_keys
    with _lock:
        _cached_keys = None


def log_proxy_status() -> None:
    """Announce residential-proxy wiring at startup.

    Surfaces the four states (configured + needed, configured + unused,
    unset + needed, unset + unused) so a missing ``RESIDENTIAL_PROXY_URL``
    secret produces one loud line at run start instead of being detectable
    only via downstream WARNs. The ``configured + needed`` and
    ``unset + needed`` cases log WARN so the line survives the default
    ``LAUGHTRACK_LOG_CONSOLE_LEVEL=WARNING`` filter that the GHA nightly
    schedule runs under; ``configured + unused`` logs INFO; ``unset + unused``
    is silent.
    """
    proxy_url = os.environ.get("RESIDENTIAL_PROXY_URL") or None
    allowlisted = sorted(proxy_enabled_keys())
    if allowlisted and proxy_url:
        Logger.warn(
            f"[ResidentialProxy] configured — {len(allowlisted)} scraper(s) "
            f"allowlisted: {', '.join(allowlisted)}",
            {},
        )
    elif allowlisted and not proxy_url:
        Logger.warn(
            f"[ResidentialProxy] RESIDENTIAL_PROXY_URL unset — "
            f"{len(allowlisted)} allowlisted scraper(s) will use direct "
            f"egress: {', '.join(allowlisted)}",
            {},
        )
    elif proxy_url and not allowlisted:
        Logger.info(
            "[ResidentialProxy] RESIDENTIAL_PROXY_URL set but no scrapers "
            "have use_residential_proxy=true",
            {},
        )
