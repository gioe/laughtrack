"""Shared circuit breaker for the SeatEngine API.

Opens after N consecutive failures across all SeatEngine venues, preventing
subsequent clubs from making HTTP calls until the breaker resets after a
configurable cooldown. This avoids hammering a downed API with 80+ retry
attempts while still allowing early venues a few retry chances.
"""

import threading
import time
from typing import Optional

from laughtrack.foundation.exceptions import CircuitBreakerOpenError
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.config.config_manager import ConfigManager


class SeatEngineCircuitBreaker:
    """Singleton circuit breaker shared across all 80 SeatEngine scraper instances.

    States:
    - CLOSED (normal): HTTP calls proceed. Failure counter increments on each failed call.
    - OPEN: Circuit tripped. check_open() raises CircuitBreakerOpenError immediately,
      skipping the HTTP call entirely. Resets automatically after cooldown_seconds.

    Thread-safe: uses threading.Lock so it works correctly when scrapers run
    concurrently via asyncio.gather across a thread pool.
    """

    _instance: Optional["SeatEngineCircuitBreaker"] = None
    _class_lock = threading.Lock()

    def __new__(cls) -> "SeatEngineCircuitBreaker":
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._init()
                    cls._instance = instance
        return cls._instance

    def _init(self) -> None:
        self._failure_count = 0
        self._open_since: Optional[float] = None
        self._state_lock = threading.Lock()
        self._threshold: int = int(ConfigManager.get_config("api", "seatengine_cb_threshold", 10))
        self._cooldown: float = float(ConfigManager.get_config("api", "seatengine_cb_cooldown", 300))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        """True if the circuit breaker is currently open (failing fast)."""
        with self._state_lock:
            return self._is_open_unlocked()

    def check_open(self) -> None:
        """Raise CircuitBreakerOpenError if the breaker is open.

        Call this at the start of any SeatEngine HTTP method to fail fast
        without making a network request when the API is known to be down.
        """
        with self._state_lock:
            if self._is_open_unlocked():
                elapsed = time.monotonic() - self._open_since  # type: ignore[operator]
                remaining = max(0.0, self._cooldown - elapsed)
                raise CircuitBreakerOpenError(
                    f"SeatEngine circuit breaker is open — API appears to be down. "
                    f"Failing fast without HTTP call. Resets in {remaining:.0f}s."
                )

    def record_failure(self) -> None:
        """Record a consecutive failure. Opens the breaker when threshold is reached."""
        with self._state_lock:
            self._failure_count += 1
            if self._failure_count >= self._threshold and self._open_since is None:
                self._open_since = time.monotonic()
                Logger.warn(
                    f"SeatEngine circuit breaker OPENED after {self._failure_count} consecutive "
                    f"failures. Remaining clubs will fail fast for {self._cooldown:.0f}s."
                )

    def record_success(self) -> None:
        """Record a successful response. Resets the failure counter and closes the breaker."""
        with self._state_lock:
            if self._failure_count > 0 or self._open_since is not None:
                Logger.info("SeatEngine circuit breaker reset after successful response")
            self._failure_count = 0
            self._open_since = None

    # ------------------------------------------------------------------
    # Introspection (for tests / monitoring)
    # ------------------------------------------------------------------

    @property
    def failure_count(self) -> int:
        with self._state_lock:
            return self._failure_count

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def cooldown(self) -> float:
        return self._cooldown

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    @classmethod
    def reset_for_testing(cls) -> None:
        """Destroy the singleton so the next instantiation starts fresh.

        For use in tests only — never call in production code.
        """
        with cls._class_lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _is_open_unlocked(self) -> bool:
        """Check open state. Must be called with _state_lock already held."""
        if self._open_since is None:
            return False
        elapsed = time.monotonic() - self._open_since
        if elapsed >= self._cooldown:
            Logger.info(f"SeatEngine circuit breaker cooldown elapsed ({elapsed:.0f}s) — resetting")
            self._failure_count = 0
            self._open_since = None
            return False
        return True
