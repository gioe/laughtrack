"""
Enhanced rate limiter with anti-detection features for Tixr API requests.
Provides comprehensive request pacing, failure handling, and human-like behavior patterns.
"""

import asyncio
import random
import time
from collections import deque
from enum import Enum
from typing import Any, Dict, Optional

from laughtrack.foundation.models.types import JSONDict

from .config import (
    DEFAULT_SAFETY_CONFIG,
    TixrConfigLevel,
    TixrRateLimitConfig,
    TixrSafetyConfig,
    get_config_for_level,
)


class RequestStatus(Enum):
    """Status of a request attempt."""

    SUCCESS = "success"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    BLOCKED = "blocked"


class RequestRecord:
    """Record of a single request for tracking purposes."""

    def __init__(
        self, url: str, timestamp: float, status: RequestStatus, delay_applied: float = 0.0, error_message: str = None
    ):
        self.url = url
        self.timestamp = timestamp
        self.status = status
        self.delay_applied = delay_applied
        self.error_message = error_message


class TixrAntiDetectionLimiter:
    """
    Advanced rate limiter with human-like behavior patterns to avoid detection.

    Features:
    - Configurable rate limiting with multiple presets
    - Exponential backoff on errors
    - Burst request protection
    - Request history tracking
    - Statistical analysis of request patterns
    """

    def __init__(
        self,
        config_level: TixrConfigLevel = TixrConfigLevel.BALANCED,
        rate_config: Optional[TixrRateLimitConfig] = None,
        safety_config: Optional[TixrSafetyConfig] = None,
    ):
        """
        Initialize the rate limiter.

        Args:
            config_level: Predefined configuration level
            rate_config: Custom rate limiting configuration (overrides config_level)
            safety_config: Custom safety configuration
        """
        # Use custom config or load from level
        self.rate_config = rate_config or get_config_for_level(config_level)
        self.safety_config = safety_config or DEFAULT_SAFETY_CONFIG

        # Request tracking
        self.last_request_time: Optional[float] = None
        self.request_history: deque = deque(maxlen=1000)  # Keep last 1000 requests
        self.session_start = time.time()

        # Error tracking
        self.consecutive_errors = 0
        self.total_requests = 0
        self.total_errors = 0

        # Burst tracking
        self.burst_requests = 0
        self.last_burst_reset = time.time()

        # Backoff state
        self.current_backoff_delay = 0.0
        self.last_error_time: Optional[float] = None

        # Statistics
        self.stats = {
            "total_delay_applied": 0.0,
            "max_delay_applied": 0.0,
            "avg_delay": 0.0,
            "requests_by_hour": {},
        }

    def wait_if_needed(self, url: str) -> float:
        """
        Wait appropriate time before making request to appear human-like.

        Args:
            url: The URL being requested (for logging/tracking)

        Returns:
            Actual delay applied in seconds
        """
        if not self.safety_config.enable_rate_limiting:
            return 0.0

        current_time = time.time()
        delay_applied = 0.0

        try:
            # Check hourly rate limit
            if self._exceeds_hourly_limit():
                wait_time = self._time_until_next_hour()
                if self.safety_config.enable_logging:
                    print(f"⏰ Hourly rate limit reached. Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                delay_applied += wait_time
                self._reset_session()

            # Check burst protection
            if self._exceeds_burst_limit():
                burst_wait = self.rate_config.burst_cooldown
                if self.safety_config.enable_logging:
                    print(f"⚡ Burst limit reached. Cooling down for {burst_wait:.1f} seconds...")
                time.sleep(burst_wait)
                delay_applied += burst_wait
                self._reset_burst_counter()

            # Calculate standard delay
            base_delay = self._calculate_base_delay()
            error_backoff = self._calculate_error_backoff()
            total_delay = max(base_delay, error_backoff)

            # Apply delay if needed
            if self.last_request_time is not None:
                elapsed = current_time - self.last_request_time
                if elapsed < total_delay:
                    wait_time = total_delay - elapsed
                    if self.safety_config.enable_logging and wait_time > 0.1:
                        print(
                            f"🤖 Anti-detection delay: {wait_time:.1f}s (base: {base_delay:.1f}s, backoff: {error_backoff:.1f}s)"
                        )
                    time.sleep(wait_time)
                    delay_applied += wait_time

            # Update tracking
            self._update_request_tracking(url, delay_applied)

            return delay_applied

        except Exception as e:
            if self.safety_config.enable_logging:
                print(f"⚠️ Error in rate limiter: {e}")
            return delay_applied

    async def wait_if_needed_async(self, url: str) -> float:
        """Async version of wait_if_needed."""
        # For simple delays, we can use the sync version
        # For more complex async patterns, this could be extended
        delay = self.wait_if_needed(url)
        if delay > 0:
            await asyncio.sleep(0.01)  # Yield control briefly
        return delay

    def record_success(self, url: str) -> None:
        """Record a successful request."""
        self.consecutive_errors = 0
        self.current_backoff_delay = 0.0
        self._record_request(url, RequestStatus.SUCCESS)

        # Reset burst counter if we're past the cooldown period
        if time.time() - self.last_burst_reset > self.rate_config.burst_cooldown:
            self.burst_requests = 0

    def record_error(self, url: str, error_message: Optional[str] = None, status_code: Optional[int] = None) -> None:
        """Record a failed request and update backoff accordingly."""
        self.consecutive_errors += 1
        self.total_errors += 1
        self.last_error_time = time.time()

        # Determine error type and adjust backoff
        if status_code in [429, 503]:  # Rate limiting
            status = RequestStatus.RATE_LIMITED
            self.current_backoff_delay = min(
                self.current_backoff_delay * self.safety_config.error_backoff_multiplier,
                self.rate_config.max_backoff_delay,
            )
        elif status_code == 403:  # Likely blocked
            status = RequestStatus.BLOCKED
            self.current_backoff_delay = self.rate_config.max_backoff_delay
        else:  # General error
            status = RequestStatus.ERROR
            if self.rate_config.enable_exponential_backoff:
                self.current_backoff_delay = min(
                    max(self.rate_config.min_delay, self.current_backoff_delay * self.rate_config.backoff_multiplier),
                    self.rate_config.max_backoff_delay,
                )

        self._record_request(url, status, error_message=error_message)

        if self.safety_config.enable_logging:
            print(
                f"❌ Request error recorded. Consecutive errors: {self.consecutive_errors}, "
                f"Backoff delay: {self.current_backoff_delay:.1f}s"
            )

    def should_stop_requests(self) -> bool:
        """Check if we should stop making requests due to too many errors."""
        return (
            self.consecutive_errors >= self.safety_config.max_consecutive_errors
            and self.safety_config.max_consecutive_errors > 0
        )

    def get_statistics(self) -> JSONDict:
        """Get comprehensive statistics about request patterns."""
        current_time = time.time()
        session_duration = current_time - self.session_start

        # Calculate rates
        if session_duration > 0:
            requests_per_hour = (self.total_requests / session_duration) * 3600
            error_rate = (self.total_errors / max(self.total_requests, 1)) * 100
        else:
            requests_per_hour = 0
            error_rate = 0

        # Recent request analysis
        recent_requests = [r for r in self.request_history if current_time - r.timestamp < 3600]  # Last hour

        return {
            "session_duration_seconds": session_duration,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "consecutive_errors": self.consecutive_errors,
            "error_rate_percent": error_rate,
            "requests_per_hour": requests_per_hour,
            "recent_requests_count": len(recent_requests),
            "current_backoff_delay": self.current_backoff_delay,
            "burst_requests_used": self.burst_requests,
            "total_delay_applied": self.stats["total_delay_applied"],
            "average_delay": self.stats["avg_delay"],
            "max_delay_applied": self.stats["max_delay_applied"],
            "rate_limit_config": {
                "min_delay": self.rate_config.min_delay,
                "max_delay": self.rate_config.max_delay,
                "max_requests_per_hour": self.rate_config.max_requests_per_hour,
                "burst_limit": self.rate_config.max_burst_requests,
            },
        }

    def reset_state(self) -> None:
        """Reset the rate limiter state (useful for testing or recovery)."""
        self.last_request_time = None
        self.consecutive_errors = 0
        self.current_backoff_delay = 0.0
        self.burst_requests = 0
        self.last_burst_reset = time.time()
        self.session_start = time.time()
        self.request_history.clear()
        self.stats = {
            "total_delay_applied": 0.0,
            "max_delay_applied": 0.0,
            "avg_delay": 0.0,
            "requests_by_hour": {},
        }

    def _calculate_base_delay(self) -> float:
        """Calculate base delay with randomization."""
        if self.safety_config.enable_randomization:
            return random.uniform(self.rate_config.min_delay, self.rate_config.max_delay)
        else:
            return (self.rate_config.min_delay + self.rate_config.max_delay) / 2

    def _calculate_error_backoff(self) -> float:
        """Calculate additional delay due to errors."""
        if self.consecutive_errors == 0:
            return 0.0
        return min(self.current_backoff_delay, self.rate_config.max_backoff_delay)

    def _exceeds_hourly_limit(self) -> bool:
        """Check if we're approaching hourly request limit."""
        current_time = time.time()
        session_duration = current_time - self.session_start

        if session_duration < 3600:  # Less than 1 hour
            return self.total_requests >= self.rate_config.max_requests_per_hour

        # For sessions longer than 1 hour, check rolling window
        cutoff_time = current_time - 3600
        recent_requests = sum(1 for r in self.request_history if r.timestamp > cutoff_time)
        return recent_requests >= self.rate_config.max_requests_per_hour

    def _exceeds_burst_limit(self) -> bool:
        """Check if we're exceeding burst request limits."""
        current_time = time.time()

        # Reset burst counter if cooldown period has passed
        if current_time - self.last_burst_reset > self.rate_config.burst_cooldown:
            self.burst_requests = 0
            self.last_burst_reset = current_time
            return False

        return self.burst_requests >= self.rate_config.max_burst_requests

    def _time_until_next_hour(self) -> float:
        """Calculate time to wait until next hour boundary."""
        session_duration = time.time() - self.session_start
        return 3600 - (session_duration % 3600)

    def _reset_session(self) -> None:
        """Reset session counters."""
        self.session_start = time.time()
        self.total_requests = 0
        # Don't reset error tracking as that should persist

    def _reset_burst_counter(self) -> None:
        """Reset burst request counter."""
        self.burst_requests = 0
        self.last_burst_reset = time.time()

    def _update_request_tracking(self, url: str, delay_applied: float) -> None:
        """Update internal tracking after a request."""
        self.last_request_time = time.time()
        self.total_requests += 1
        self.burst_requests += 1

        # Update statistics
        self.stats["total_delay_applied"] += delay_applied
        self.stats["max_delay_applied"] = max(self.stats["max_delay_applied"], delay_applied)
        if self.total_requests > 0:
            self.stats["avg_delay"] = self.stats["total_delay_applied"] / self.total_requests

    def _record_request(self, url: str, status: RequestStatus, error_message: Optional[str] = None) -> None:
        """Record a request in the history."""
        record = RequestRecord(
            url=url,
            timestamp=time.time(),
            status=status,
            delay_applied=0.0,  # This could be enhanced to track per-request delays
            error_message=error_message,
        )
        self.request_history.append(record)


# Global instances for different use cases
tixr_rate_limiter = TixrAntiDetectionLimiter(TixrConfigLevel.BALANCED)
tixr_conservative_limiter = TixrAntiDetectionLimiter(TixrConfigLevel.CONSERVATIVE)
tixr_aggressive_limiter = TixrAntiDetectionLimiter(TixrConfigLevel.AGGRESSIVE)


def get_rate_limiter(level: TixrConfigLevel = TixrConfigLevel.BALANCED) -> TixrAntiDetectionLimiter:
    """Get a rate limiter instance for the specified configuration level."""
    if level == TixrConfigLevel.CONSERVATIVE:
        return tixr_conservative_limiter
    elif level == TixrConfigLevel.AGGRESSIVE:
        return tixr_aggressive_limiter
    else:
        return tixr_rate_limiter


def create_custom_limiter(
    rate_config: TixrRateLimitConfig, safety_config: TixrSafetyConfig
) -> TixrAntiDetectionLimiter:
    """Create a custom rate limiter with specific configuration."""
    return TixrAntiDetectionLimiter(
        config_level=TixrConfigLevel.BALANCED,  # Will be overridden by rate_config
        rate_config=rate_config,
        safety_config=safety_config,
    )
