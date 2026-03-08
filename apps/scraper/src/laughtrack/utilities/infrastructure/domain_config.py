"""
Per-domain rate-limiting and anti-detection configuration.

Each scraping domain declares its rate strategy, delays, session-rotation
behaviour, and whether anti-detection applies via a DomainConfig instance.
The unified RateLimiter reads these configs at runtime.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from laughtrack.foundation.infrastructure.http.browser_profile import (
    BUILTIN_PROFILES,
    BrowserProfile,
)


@dataclass
class DomainConfig:
    """
    Canonical configuration for a single scraping domain.

    Two modes:
    - Simple RPS mode (enable_anti_detection=False): enforces a minimum
      interval between requests based on requests_per_second.
    - Anti-detection mode (enable_anti_detection=True): applies human-like
      random delays, session rotation, and exponential backoff on errors.
    """

    # --- Simple RPS mode ---
    requests_per_second: float = 1.0

    # --- Anti-detection mode ---
    enable_anti_detection: bool = False
    min_delay: float = 2.0  # seconds
    max_delay: float = 5.0  # seconds

    # Session rotation
    session_request_limit: int = 50   # rotate after this many requests
    session_duration_secs: int = 3600  # rotate after this many seconds

    # Error backoff
    error_backoff_base: float = 5.0   # base seconds added per error
    peak_hour_multiplier: float = 1.2  # multiplier during 09:00-18:00

    # Full browser profiles cycled per session.  Leave empty to use BUILTIN_PROFILES.
    browser_profiles: List[BrowserProfile] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default per-domain configs
# ---------------------------------------------------------------------------

# Kept for backward-compatibility with callers that still reference this name.
BUILTIN_USER_AGENTS: List[str] = [p.user_agent for p in BUILTIN_PROFILES]

DEFAULT_DOMAIN_CONFIGS: Dict[str, "DomainConfig"] = {
    # Tixr: conservative anti-detection settings
    "www.tixr.com": DomainConfig(
        enable_anti_detection=True,
        min_delay=4.0,
        max_delay=12.0,
        session_request_limit=20,
        session_duration_secs=2400,
        error_backoff_base=15.0,
        peak_hour_multiplier=2.0,
    ),
    # Eventbrite: simple RPS (API key usage — 0.5 RPS = 1 req/2s)
    "eventbrite.com": DomainConfig(requests_per_second=0.5),
    "www.eventbriteapi.com": DomainConfig(requests_per_second=0.5),
    # Comedy venues
    "comedycellar.com": DomainConfig(requests_per_second=1.0),
    "thestandnyc.com": DomainConfig(requests_per_second=1.0),
    "eastvillecomedy.com": DomainConfig(requests_per_second=2.0),
}
