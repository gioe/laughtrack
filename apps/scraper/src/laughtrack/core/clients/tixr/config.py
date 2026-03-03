"""
Comprehensive configuration for Tixr.com API integration.
Provides anti-detection settings, rate limiting, and client behavior configuration.
"""

from dataclasses import dataclass
from enum import Enum


class TixrConfigLevel(Enum):
    """Configuration levels for different usage scenarios."""

    CONSERVATIVE = "conservative"  # Maximum safety, minimum detection risk
    BALANCED = "balanced"  # Good performance with safety
    AGGRESSIVE = "aggressive"  # Maximum performance, higher risk


@dataclass
class TixrRateLimitConfig:
    """Rate limiting configuration for Tixr API requests."""

    min_delay: float
    max_delay: float
    max_requests_per_hour: int
    max_requests_per_day: int
    max_burst_requests: int
    burst_cooldown: float
    enable_exponential_backoff: bool = True
    backoff_multiplier: float = 2.0
    max_backoff_delay: float = 60.0


@dataclass
class TixrSafetyConfig:
    """Safety and anti-detection configuration."""

    enable_rate_limiting: bool = True
    enable_randomization: bool = True
    enable_logging: bool = True
    max_consecutive_errors: int = 5
    error_backoff_multiplier: float = 2.0
    enable_user_agent_rotation: bool = False
    enable_header_randomization: bool = False
    respect_robots_txt: bool = True


@dataclass
class TixrApiConfig:
    """API endpoint and request configuration."""

    base_api_url: str = "https://www.tixr.com/api/events"
    base_url: str = "https://www.tixr.com"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    verify_ssl: bool = True
    follow_redirects: bool = True


# Predefined configuration levels
_CONFIG_LEVELS = {
    TixrConfigLevel.CONSERVATIVE: TixrRateLimitConfig(
        min_delay=3.0,
        max_delay=10.0,
        max_requests_per_hour=200,
        max_requests_per_day=400,
        max_burst_requests=2,
        burst_cooldown=45.0,
    ),
    TixrConfigLevel.BALANCED: TixrRateLimitConfig(
        min_delay=2.0,
        max_delay=8.0,
        max_requests_per_hour=300,
        max_requests_per_day=500,
        max_burst_requests=3,
        burst_cooldown=30.0,
    ),
    TixrConfigLevel.AGGRESSIVE: TixrRateLimitConfig(
        min_delay=1.0,
        max_delay=5.0,
        max_requests_per_hour=500,
        max_requests_per_day=1000,
        max_burst_requests=5,
        burst_cooldown=15.0,
    ),
}

# Default configuration (BALANCED)
DEFAULT_RATE_LIMITS = _CONFIG_LEVELS[TixrConfigLevel.BALANCED]
DEFAULT_SAFETY_CONFIG = TixrSafetyConfig()
DEFAULT_API_CONFIG = TixrApiConfig()

# Legacy configuration for backward compatibility
TIXR_RATE_LIMITS = {
    "min_delay": DEFAULT_RATE_LIMITS.min_delay,
    "max_delay": DEFAULT_RATE_LIMITS.max_delay,
    "max_requests_per_hour": DEFAULT_RATE_LIMITS.max_requests_per_hour,
    "max_requests_per_day": DEFAULT_RATE_LIMITS.max_requests_per_day,
    "max_burst_requests": DEFAULT_RATE_LIMITS.max_burst_requests,
    "burst_cooldown": DEFAULT_RATE_LIMITS.burst_cooldown,
}

SAFETY_CONFIG = {
    "enable_rate_limiting": DEFAULT_SAFETY_CONFIG.enable_rate_limiting,
    "enable_randomization": DEFAULT_SAFETY_CONFIG.enable_randomization,
    "enable_logging": DEFAULT_SAFETY_CONFIG.enable_logging,
    "max_consecutive_errors": DEFAULT_SAFETY_CONFIG.max_consecutive_errors,
    "error_backoff_multiplier": DEFAULT_SAFETY_CONFIG.error_backoff_multiplier,
}

# Enhanced user agent rotation
TIXR_USER_AGENTS = [
    # macOS Chrome (primary)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    # Windows Chrome (alternative)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    # macOS Safari (variation)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
]

# DataDome-specific configuration
DATADOME_CONFIG = {
    "enable_protection": True,
    "cookie_name": "datadome",
    "challenge_detection_keywords": ["captcha", "challenge", "verification"],
    "blocked_status_codes": [403, 429],
    "retry_after_block": True,
    "max_block_retries": 2,
    "block_retry_delay": 30.0,
}


def get_config_for_level(level: TixrConfigLevel) -> TixrRateLimitConfig:
    """Get rate limiting configuration for specified level."""
    return _CONFIG_LEVELS[level]


def get_recommended_config(expected_daily_volume: int) -> TixrConfigLevel:
    """
    Get recommended configuration level based on expected daily volume.

    Args:
        expected_daily_volume: Expected number of API requests per day

    Returns:
        Recommended configuration level
    """
    if expected_daily_volume <= 200:
        return TixrConfigLevel.CONSERVATIVE
    elif expected_daily_volume <= 500:
        return TixrConfigLevel.BALANCED
    else:
        return TixrConfigLevel.AGGRESSIVE


# Environment-specific overrides (can be set via environment variables)
ENV_CONFIG_OVERRIDES = {
    "TIXR_MIN_DELAY": "min_delay",
    "TIXR_MAX_DELAY": "max_delay",
    "TIXR_MAX_REQUESTS_PER_HOUR": "max_requests_per_hour",
    "TIXR_MAX_REQUESTS_PER_DAY": "max_requests_per_day",
    "TIXR_ENABLE_RATE_LIMITING": "enable_rate_limiting",
    "TIXR_ENABLE_LOGGING": "enable_logging",
}
