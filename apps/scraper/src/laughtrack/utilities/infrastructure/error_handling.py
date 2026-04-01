"""
Common error handling patterns and utilities for scrapers.

This module provides standardized error handling, retry logic, and error
classification for different types of scraping failures.
"""

import asyncio
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, cast

from curl_cffi.requests import RequestsError

from laughtrack.foundation.exceptions import (
    DataError,
    ErrorClassifier,
    ErrorSeverity,
    NetworkError,
    RateLimitError,
    ScrapingError,
)
from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.infrastructure.logger.logger import Logger


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a specific attempt."""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random

            delay = delay * (0.5 + random.random() * 0.5)

        return delay


class ErrorHandler:
    """Handles errors with retry logic and logging."""

    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.retry_config = retry_config or RetryConfig()
        self.error_counts: Dict[str, int] = {}

    async def execute_with_retry(self, operation: Callable, operation_name: str, *args, **kwargs) -> Any:
        """
        Execute an operation with retry logic.

        Args:
            operation: Async function to execute
            operation_name: Name for logging purposes
            *args, **kwargs: Arguments to pass to operation

        Returns:
            Operation result

        Raises:
            ScrapingError: If all retry attempts fail
        """
        last_error = None

        for attempt in range(1, self.retry_config.max_attempts + 1):
            try:
                result = await operation(*args, **kwargs)

                # Reset error count on success
                if operation_name in self.error_counts:
                    del self.error_counts[operation_name]

                return result

            except Exception as e:
                # Classify the error
                if isinstance(e, RequestsError):
                    classified_error = ErrorClassifier.classify_http_error(e)
                elif isinstance(e, ScrapingError):
                    classified_error = e
                else:
                    classified_error = ErrorClassifier.classify_data_error(e, operation_name)

                last_error = classified_error

                # Track error count
                self.error_counts[operation_name] = self.error_counts.get(operation_name, 0) + 1

                # Log the error
                Logger.warn(
                    f"Attempt {attempt}/{self.retry_config.max_attempts} failed for {operation_name}: {str(e)}",
                )

                # Check if we should retry
                if not self._should_retry(classified_error, attempt):
                    break

                # Calculate and apply delay
                if attempt < self.retry_config.max_attempts:
                    delay = self.retry_config.get_delay(attempt)

                    # Handle rate limiting with custom delay
                    if isinstance(classified_error, RateLimitError) and classified_error.retry_after:
                        delay = max(delay, classified_error.retry_after)

                    Logger.info(f"Retrying {operation_name} in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)

        # All attempts failed
        status_suffix = (
            f": HTTP {last_error.status_code}"
            if isinstance(last_error, NetworkError) and last_error.status_code is not None
            else ""
        )
        # 4xx errors are deterministic (resource doesn't exist or is forbidden) — downgrade to WARNING
        if isinstance(last_error, NetworkError) and last_error.status_code is not None and 400 <= last_error.status_code < 500:
            Logger.warn(f"Not retrying {operation_name} — deterministic failure{status_suffix}")
        else:
            Logger.error(f"All attempts failed for {operation_name}{status_suffix}")

        if last_error:
            raise last_error
        else:
            raise ScrapingError(f"Operation {operation_name} failed after {self.retry_config.max_attempts} attempts")

    def _should_retry(self, error: ScrapingError, attempt: int) -> bool:
        """Determine if we should retry based on error type and attempt count."""
        if attempt >= self.retry_config.max_attempts:
            return False

        # Don't retry fatal errors
        if error.severity == ErrorSeverity.FATAL:
            return False

        # Don't retry high severity errors
        if error.severity == ErrorSeverity.HIGH:
            return False

        # Retry network and rate limit errors
        if isinstance(error, (NetworkError, RateLimitError)):
            # Don't retry 4xx client errors — they are deterministic failures.
            # (429 is classified as RateLimitError, not NetworkError, so it is unaffected.)
            if isinstance(error, NetworkError) and error.status_code is not None and 400 <= error.status_code < 500:
                return False
            return True

        # Retry data errors only once
        if isinstance(error, DataError):
            return attempt == 1

        return True

    def get_error_stats(self) -> JSONDict:
        """Get error statistics."""
        return {
            "total_operations_with_errors": len(self.error_counts),
            "error_counts": self.error_counts.copy(),
            "most_problematic_operations": sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        }
