"""
Per-domain rate-limiting and anti-detection configuration.

Each scraping domain declares its rate strategy, delays, session-rotation
behaviour, and whether anti-detection applies via a DomainConfig instance.
The unified RateLimiter reads these configs at runtime.
"""

from dataclasses import dataclass, field
from typing import Dict, List


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

    # User agents cycled per session (leave empty to use built-in defaults)
    user_agents: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default per-domain configs
# ---------------------------------------------------------------------------

BUILTIN_USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
]

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
