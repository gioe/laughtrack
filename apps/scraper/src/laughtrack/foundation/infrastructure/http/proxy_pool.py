"""
Rotating proxy pool for HTTP requests.

Reads proxy URLs from the SCRAPER_PROXY_LIST environment variable
(comma-separated list or file path) and provides per-request or
per-session rotation with failure tracking and automatic retirement
of bad proxies.
"""

import os
from typing import Dict, List, Optional, Set

from laughtrack.foundation.infrastructure.logger.logger import Logger


class ProxyPool:
    """Manages a pool of HTTP proxies with rotation and failure tracking.

    Usage::

        pool = ProxyPool.from_env()          # returns None when env var unset
        if pool:
            proxy_url = pool.get_proxy()     # "http://host:port" or None
            pool.report_success(proxy_url)
            # or
            pool.report_failure(proxy_url)   # retires after max_failures hits
    """

    PER_REQUEST = "per_request"
    PER_SESSION = "per_session"

    def __init__(
        self,
        proxies: List[str],
        rotation: str = PER_REQUEST,
        max_failures: int = 3,
    ) -> None:
        """
        Args:
            proxies: List of proxy URLs (e.g. ["http://host:8080", ...])
            rotation: "per_request" rotates after every get_proxy() call;
                      "per_session" keeps the same proxy until rotate() is
                      called explicitly.
            max_failures: How many consecutive failures before a proxy is
                          retired from the active pool.
        """
        if not proxies:
            raise ValueError("ProxyPool requires at least one proxy URL")

        self._proxies: List[str] = list(proxies)
        self._rotation = rotation
        self._max_failures = max_failures
        self._failure_counts: Dict[str, int] = {p: 0 for p in self._proxies}
        self._retired: Set[str] = set()
        self._index: int = 0

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(
        cls,
        env_var: str = "SCRAPER_PROXY_LIST",
        rotation: str = PER_REQUEST,
        max_failures: int = 3,
    ) -> Optional["ProxyPool"]:
        """Build a ProxyPool from an environment variable.

        The env var can be:
        - A comma-separated list of proxy URLs:
          ``SCRAPER_PROXY_LIST=http://p1:8080,http://p2:8080``
        - A path to a file with one proxy URL per line:
          ``SCRAPER_PROXY_LIST=/etc/proxies.txt``

        Returns ``None`` when the variable is unset or empty so callers
        can branch on ``if pool:`` without special-casing.
        """
        raw = os.environ.get(env_var, "").strip()
        if not raw:
            return None

        # File path takes precedence over comma-separated list
        if os.path.isfile(raw):
            try:
                with open(raw) as fh:
                    proxies = [line.strip() for line in fh if line.strip()]
            except OSError as exc:
                Logger.warn(f"[ProxyPool] Could not read proxy file {raw!r}: {exc}", {})
                return None
        else:
            proxies = [p.strip() for p in raw.split(",") if p.strip()]

        if not proxies:
            return None

        Logger.debug(
            f"[ProxyPool] Loaded {len(proxies)} proxies (rotation={rotation})",
            {"env_var": env_var},
        )
        return cls(proxies=proxies, rotation=rotation, max_failures=max_failures)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def active_proxies(self) -> List[str]:
        """Proxy URLs that have not been retired."""
        return [p for p in self._proxies if p not in self._retired]

    @property
    def rotation(self) -> str:
        return self._rotation

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def get_proxy(self) -> Optional[str]:
        """Return the current proxy URL.

        When rotation is PER_REQUEST, the index advances automatically
        after each call so successive calls return different proxies.

        Returns ``None`` when all proxies have been retired.
        """
        active = self.active_proxies
        if not active:
            Logger.warn("[ProxyPool] All proxies retired; sending requests without a proxy", {})
            return None

        idx = self._index % len(active)
        proxy_url = active[idx]

        if self._rotation == self.PER_REQUEST:
            self._index = (idx + 1) % len(active)

        return proxy_url

    def rotate(self) -> None:
        """Advance to the next active proxy.

        Call this explicitly when using PER_SESSION rotation to move to
        the next proxy (e.g. at the start of a new scraping session).
        """
        active = self.active_proxies
        if active:
            self._index = (self._index + 1) % len(active)

    def report_success(self, proxy_url: str) -> None:
        """Decrement the failure counter for *proxy_url* on success."""
        if proxy_url in self._failure_counts:
            self._failure_counts[proxy_url] = max(0, self._failure_counts[proxy_url] - 1)

    def report_failure(self, proxy_url: str) -> None:
        """Increment failure counter; retire the proxy when threshold is reached."""
        if proxy_url not in self._failure_counts:
            self._failure_counts[proxy_url] = 0
        self._failure_counts[proxy_url] += 1
        if (
            proxy_url not in self._retired
            and self._failure_counts[proxy_url] >= self._max_failures
        ):
            self._retired.add(proxy_url)
            Logger.warn(
                f"[ProxyPool] Proxy {proxy_url!r} retired after "
                f"{self._max_failures} failures",
                {},
            )
