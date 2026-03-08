"""
Unified rate-limiting infrastructure for all scraping domains.

A single RateLimiter singleton reads per-domain DomainConfig objects and
applies either simple RPS-based limiting or full anti-detection behaviour
(human-like delays, session rotation, exponential backoff) depending on the
domain's configuration.

Consolidates three previously separate systems into one.
"""

import asyncio
import hashlib
import random
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from laughtrack.foundation.infrastructure.http.browser_profile import (
    BUILTIN_PROFILES,
    BrowserProfile,
)
from laughtrack.foundation.models.types import ScrapingTarget

from .domain_config import BUILTIN_USER_AGENTS, DEFAULT_DOMAIN_CONFIGS, DomainConfig


# ---------------------------------------------------------------------------
# Internal session state (used only in anti-detection mode)
# ---------------------------------------------------------------------------


@dataclass
class _RequestSession:
    """Tracks per-domain session state for anti-detection rate limiting."""

    domain: str
    start_time: datetime
    request_count: int
    last_request: datetime
    consecutive_errors: int
    user_agent: str        # derived from profile.user_agent; kept for backward compat
    session_id: str
    profile: Optional[BrowserProfile] = None  # full fingerprint profile for this session


# ---------------------------------------------------------------------------
# Unified rate limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """
    Singleton rate limiter that coordinates requests across all scrapers.

    Per-domain behaviour is driven by DomainConfig:
    - Simple RPS mode  (enable_anti_detection=False): enforces a minimum
      interval derived from requests_per_second.
    - Anti-detection mode (enable_anti_detection=True): applies randomised
      human-like delays, session rotation, and exponential backoff.

    The async path (await_if_needed) always uses asyncio.sleep — it never
    blocks the event loop.
    """

    _instance: Optional["RateLimiter"] = None
    _class_lock = threading.Lock()

    def __new__(cls) -> "RateLimiter":
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._initialized = False
                    cls._instance = obj
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        # Per-domain configs (seeded from built-in defaults)
        self._domain_configs: Dict[str, DomainConfig] = dict(DEFAULT_DOMAIN_CONFIGS)
        self._default_config = DomainConfig()  # fallback

        # RPS-mode state
        self._last_request: Dict[str, float] = {}
        self._domain_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._async_domain_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = threading.Lock()

        # Anti-detection session state
        self._sessions: Dict[str, _RequestSession] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._sessions_write_lock = threading.Lock()  # guards sync writes to _sessions

        self._initialized = True

    # ------------------------------------------------------------------
    # Public configuration API
    # ------------------------------------------------------------------

    def set_domain_config(self, domain: str, config: DomainConfig) -> None:
        """Register or replace the full DomainConfig for a domain."""
        with self._global_lock:
            self._domain_configs[domain] = config

    def set_domain_limit(self, domain: str, requests_per_second: float) -> None:
        """
        Convenience method: update only the RPS for a domain.

        Creates a new DomainConfig (simple RPS mode) if the domain has no
        existing config; otherwise updates requests_per_second in place.
        """
        with self._global_lock:
            existing = self._domain_configs.get(domain)
            if existing is None:
                self._domain_configs[domain] = DomainConfig(requests_per_second=requests_per_second)
            else:
                # Preserve all other settings, only update RPS
                self._domain_configs[domain] = DomainConfig(
                    requests_per_second=requests_per_second,
                    enable_anti_detection=existing.enable_anti_detection,
                    min_delay=existing.min_delay,
                    max_delay=existing.max_delay,
                    session_request_limit=existing.session_request_limit,
                    session_duration_secs=existing.session_duration_secs,
                    error_backoff_base=existing.error_backoff_base,
                    peak_hour_multiplier=existing.peak_hour_multiplier,
                    browser_profiles=existing.browser_profiles,
                )

    def get_domain_limit(self, domain: str) -> float:
        """Return the configured RPS for a domain."""
        return self._get_config(domain).requests_per_second

    def record_request_error(self, domain: str) -> None:
        """
        Increment the consecutive error counter for a domain's anti-detection session.

        Call this after an HTTP error (e.g. 429, 5xx) so that exponential backoff
        in _calculate_anti_detection_delay takes effect on the next request.
        """
        with self._sessions_write_lock:
            session = self._sessions.get(domain)
            if session is not None:
                session.consecutive_errors += 1

    def record_request_success(self, domain: str) -> None:
        """Reset the consecutive error counter for a domain after a successful request."""
        with self._sessions_write_lock:
            session = self._sessions.get(domain)
            if session is not None:
                session.consecutive_errors = 0

    def get_domain_user_agent(self, domain: str) -> Optional[str]:
        """
        Return the current session's User-Agent string for a domain, if one exists.

        Callers in anti-detection mode can use this to set the User-Agent header
        on outgoing requests, ensuring the rotated agent is actually applied.
        Returns None when the domain has no active anti-detection session.
        """
        session = self._sessions.get(domain)
        return session.user_agent if session is not None else None

    def get_domain_profile(self, domain: str) -> Optional[BrowserProfile]:
        """
        Return the current session's BrowserProfile for a domain, if one exists.

        Callers in anti-detection mode can use this to build a full set of
        browser-identity headers that are coherent with the TLS fingerprint
        (curl-cffi impersonation target) selected for this session.
        Returns None when the domain has no active anti-detection session.
        """
        session = self._sessions.get(domain)
        return session.profile if session is not None else None

    # ------------------------------------------------------------------
    # Main rate-limiting interface
    # ------------------------------------------------------------------

    async def await_if_needed(self, target: ScrapingTarget) -> None:
        """
        Async rate limiting — awaits if necessary; never blocks the event loop.

        Dispatches to anti-detection or simple RPS mode based on DomainConfig.
        """
        if not self._is_url(target):
            return

        domain = self._extract_domain(target)
        config = self._get_config(domain)

        if config.enable_anti_detection:
            await self._anti_detection_wait(domain, config)
        else:
            await self._rps_wait(domain, config)

    def wait_if_needed(self, url: str) -> None:
        """
        Synchronous rate limiting (simple RPS mode only).

        Use await_if_needed from async contexts.  Do not mix sync and async
        calls for the same domain from concurrent threads.
        """
        if not self._is_url(url):
            return

        domain = self._extract_domain(url)
        config = self._get_config(domain)

        with self._domain_locks[domain]:
            wait_time = self._rps_wait_time(domain, config)
            if wait_time:
                time.sleep(wait_time)
            self._last_request[domain] = time.time()

    # ------------------------------------------------------------------
    # RPS mode internals
    # ------------------------------------------------------------------

    async def _rps_wait(self, domain: str, config: DomainConfig) -> None:
        async with self._get_async_lock(domain):
            wait_time = self._rps_wait_time(domain, config)
            if wait_time:
                await asyncio.sleep(wait_time)
            self._last_request[domain] = time.time()

    def _rps_wait_time(self, domain: str, config: DomainConfig) -> Optional[float]:
        min_interval = 1.0 / config.requests_per_second
        now = time.time()
        last = self._last_request.get(domain, 0)
        elapsed = now - last
        if elapsed < min_interval:
            return min_interval - elapsed
        return None

    def _get_async_lock(self, domain: str) -> asyncio.Lock:
        return self._async_domain_locks.setdefault(domain, asyncio.Lock())

    # ------------------------------------------------------------------
    # Anti-detection mode internals
    # ------------------------------------------------------------------

    async def _anti_detection_wait(self, domain: str, config: DomainConfig) -> None:
        async with self._get_session_lock(domain):
            session = self._get_or_create_session(domain, config)
            delay = self._calculate_anti_detection_delay(session, config)

            time_since_last = (datetime.now() - session.last_request).total_seconds()
            actual_delay = max(0.0, delay - time_since_last)

            if actual_delay > 0:
                await asyncio.sleep(actual_delay)

            session.last_request = datetime.now()
            session.request_count += 1

    def _get_session_lock(self, domain: str) -> asyncio.Lock:
        return self._session_locks.setdefault(domain, asyncio.Lock())

    def _get_or_create_session(self, domain: str, config: DomainConfig) -> _RequestSession:
        now = datetime.now()

        if domain in self._sessions:
            session = self._sessions[domain]
            age = (now - session.start_time).total_seconds()
            needs_rotation = (
                session.request_count >= config.session_request_limit
                or age > config.session_duration_secs
                or session.consecutive_errors >= 3
            )
            if not needs_rotation:
                return session

        profiles = config.browser_profiles or BUILTIN_PROFILES
        profile = random.choice(profiles)
        session = _RequestSession(
            domain=domain,
            start_time=now,
            request_count=0,
            last_request=now - timedelta(seconds=config.max_delay),
            consecutive_errors=0,
            user_agent=profile.user_agent,
            session_id=self._make_session_id(domain),
            profile=profile,
        )
        self._sessions[domain] = session
        return session

    def _calculate_anti_detection_delay(self, session: _RequestSession, config: DomainConfig) -> float:
        base = random.uniform(config.min_delay, config.max_delay)
        jitter = random.uniform(-0.5, 1.0)
        delay = base + jitter

        # Peak-hour slowdown (09:00–18:00 local time)
        if 9 <= datetime.now().hour <= 18:
            delay *= config.peak_hour_multiplier

        # Exponential backoff on consecutive errors (cap at 8×)
        if session.consecutive_errors > 0:
            multiplier = min(2 ** session.consecutive_errors, 8)
            delay += config.error_backoff_base * multiplier

        # Progressive slowdown as session approaches its limit
        if config.session_request_limit > 0:
            progress = session.request_count / config.session_request_limit
            if progress > 0.7:
                delay *= 1.5

        return max(delay, 1.0)

    @staticmethod
    def _make_session_id(domain: str) -> str:
        data = f"{domain}_{time.time()}_{random.randint(10000, 99999)}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_config(self, domain: str) -> DomainConfig:
        return self._domain_configs.get(domain, self._default_config)

    @staticmethod
    def _extract_domain(url: str) -> str:
        if "://" in url:
            url = url.split("://", 1)[1]
        return url.split("/")[0].lower()

    @staticmethod
    def _is_url(target: str) -> bool:
        return target.startswith(("http://", "https://")) or "." in target

    # ------------------------------------------------------------------
    # Monitoring / stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Dict]:
        """Return rate-limiting statistics for all known domains."""
        with self._global_lock:
            stats = {}
            for domain, config in self._domain_configs.items():
                last = self._last_request.get(domain, 0)
                entry: Dict = {
                    "mode": "anti_detection" if config.enable_anti_detection else "rps",
                    "requests_per_second": config.requests_per_second,
                    "last_request": datetime.fromtimestamp(last) if last else None,
                    "time_since_last": time.time() - last if last else None,
                }
                if config.enable_anti_detection and domain in self._sessions:
                    s = self._sessions[domain]
                    entry["session_id"] = s.session_id
                    entry["session_requests"] = s.request_count
                    entry["consecutive_errors"] = s.consecutive_errors
                stats[domain] = entry
            return stats

    def reset_domain(self, domain: str) -> None:
        """Reset all rate-limiting state for a domain."""
        with self._domain_locks[domain]:
            self._last_request.pop(domain, None)
        with self._sessions_write_lock:
            self._sessions.pop(domain, None)
