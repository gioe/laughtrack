from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.entities.club.model import Club


class FailureType(Enum):
    """Types of Tixr API failures."""

    DATADOME_COOKIE = "datadome_cookie"
    DATADOME_CAPTCHA = "datadome_captcha"
    RATE_LIMITING = "rate_limiting"
    AUTOMATION_DETECTION = "automation_detection"
    NETWORK_ERROR = "network_error"
    UNKNOWN_403 = "unknown_403"
    OTHER = "other"


@dataclass
class FailureEvent:
    """Represents a single failure event."""

    timestamp: datetime
    event_id: str
    status_code: int
    failure_type: FailureType
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: Optional[str] = None
    request_headers: Dict[str, str] = field(default_factory=dict)
    club_id: Optional[int] = None
    additional_context: JSONDict = field(default_factory=dict)


@dataclass
class FailureStats:
    """Aggregated failure statistics."""

    total_requests: int = 0
    total_failures: int = 0
    failure_rate: float = 0.0
    failures_by_type: Dict[FailureType, int] = field(default_factory=dict)
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0


class TixrFailureMonitor:
    """
    Monitors Tixr API failures, classifies them, and tracks patterns.

    This class provides:
    - Real-time failure detection and classification
    - Failure rate monitoring with configurable time windows
    - Pattern analysis for different types of failures
    - Integration points for alerting systems
    """

    def __init__(self, window_minutes: int = 60, max_events_stored: int = 1000, logger=None):
        """
        Initialize the failure monitor.

        Args:
            window_minutes: Time window for calculating failure rates
            max_events_stored: Maximum number of failure events to keep in memory
            logger: Logger instance for monitoring activities
        """
        self.window_minutes = window_minutes
        self.max_events_stored = max_events_stored
        self.logger = logger

        # Storage for failure events
        self.failure_events: List[FailureEvent] = []
        self.success_count = 0
        self.total_requests = 0

        # Cache for computed statistics
        self._stats_cache: Optional[FailureStats] = None
        self._stats_cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=1)

    def record_request_result(
        self,
        event_id: str,
        status_code: int,
        response_headers: Dict[str, str],
        response_body: Optional[str] = None,
        request_headers: Optional[Dict[str, str]] = None,
        club: Optional[Club] = None,
    ) -> Optional[FailureEvent]:
        """
        Record the result of a Tixr API request.

        Args:
            event_id: The Tixr event ID that was requested
            status_code: HTTP status code of the response
            response_headers: Response headers from Tixr
            response_body: Response body (for failure analysis)
            request_headers: Request headers sent to Tixr
            club: Club instance for context

        Returns:
            FailureEvent if this was a failure, None if success
        """
        self.total_requests += 1

        # DataDome sometimes serves interstitials with HTTP 200 — the status
        # code alone is not a reliable success signal. Inspect the response
        # first so those blocks land in the aggregator instead of silently
        # inflating the success count.
        if status_code == 200 and self._detect_datadome(response_headers, response_body) is None:
            self.success_count += 1
            self._invalidate_stats_cache()
            return None

        # Classify the failure
        failure_type = self._classify_failure(status_code, response_headers, response_body)

        # Create failure event
        failure_event = FailureEvent(
            timestamp=datetime.utcnow(),
            event_id=event_id,
            status_code=status_code,
            failure_type=failure_type,
            response_headers=response_headers or {},
            response_body=response_body,
            request_headers=request_headers or {},
            club_id=club.id if club else None,
            additional_context=self._extract_additional_context(response_headers, response_body),
        )

        # Store the failure event
        self._store_failure_event(failure_event)

        # Log the failure
        self._log_failure(failure_event)

        return failure_event

    def get_current_stats(self, force_refresh: bool = False) -> FailureStats:
        """
        Get current failure statistics.

        Args:
            force_refresh: Whether to force recalculation of stats

        Returns:
            Current failure statistics
        """
        now = datetime.utcnow()

        # Check if cache is valid
        if (
            not force_refresh
            and self._stats_cache
            and self._stats_cache_time
            and now - self._stats_cache_time < self._cache_ttl
        ):
            return self._stats_cache

        # Calculate fresh stats
        stats = self._calculate_stats()

        # Update cache
        self._stats_cache = stats
        self._stats_cache_time = now

        return stats

    def get_failure_rate(self, minutes: Optional[int] = None) -> float:
        """
        Get failure rate for a specific time window.

        Args:
            minutes: Time window in minutes (defaults to instance window)

        Returns:
            Failure rate as a percentage (0.0 to 100.0)
        """
        window = minutes or self.window_minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=window)

        # Count failures and successes in the window
        recent_failures = [event for event in self.failure_events if event.timestamp >= cutoff_time]

        # For successes, we need to estimate based on total requests
        # This is a simplification - in production, you might want to track
        # success events explicitly
        total_recent_requests = len(recent_failures) + max(0, self.success_count)

        if total_recent_requests == 0:
            return 0.0

        return (len(recent_failures) / total_recent_requests) * 100.0

    def get_failure_pattern(self, minutes: int = 60) -> Dict[FailureType, int]:
        """
        Get failure patterns for a specific time window.

        Args:
            minutes: Time window in minutes

        Returns:
            Dictionary mapping failure types to counts
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        recent_failures = [event for event in self.failure_events if event.timestamp >= cutoff_time]

        pattern = {}
        for failure in recent_failures:
            pattern[failure.failure_type] = pattern.get(failure.failure_type, 0) + 1

        return pattern

    def is_cookie_issue_detected(self, minutes: int = 30) -> bool:
        """
        Check if recent failures suggest a DataDome cookie issue.

        Args:
            minutes: Time window to check

        Returns:
            True if cookie issues are detected
        """
        pattern = self.get_failure_pattern(minutes)

        datadome_failures = pattern.get(FailureType.DATADOME_COOKIE, 0) + pattern.get(FailureType.DATADOME_CAPTCHA, 0)

        total_failures = sum(pattern.values())

        # If more than 50% of recent failures are DataDome-related
        return total_failures > 0 and (datadome_failures / total_failures) > 0.5

    def should_alert(
        self, failure_rate_threshold: float = 25.0, consecutive_failure_threshold: int = 5
    ) -> Tuple[bool, List[str]]:
        """
        Determine if an alert should be triggered.

        Args:
            failure_rate_threshold: Failure rate percentage that triggers alert
            consecutive_failure_threshold: Number of consecutive failures that triggers alert

        Returns:
            Tuple of (should_alert, list_of_reasons)
        """
        should_alert = False
        reasons = []

        stats = self.get_current_stats()

        # Check failure rate
        if stats.failure_rate > failure_rate_threshold:
            should_alert = True
            reasons.append(f"Failure rate {stats.failure_rate:.1f}% exceeds threshold {failure_rate_threshold}%")

        # Check consecutive failures
        if stats.consecutive_failures >= consecutive_failure_threshold:
            should_alert = True
            reasons.append(
                f"Consecutive failures ({stats.consecutive_failures}) exceed threshold ({consecutive_failure_threshold})"
            )

        # Check for specific patterns
        if self.is_cookie_issue_detected():
            should_alert = True
            reasons.append("DataDome cookie issues detected")

        # Check if all recent requests are failing
        recent_pattern = self.get_failure_pattern(30)
        if sum(recent_pattern.values()) >= 10:  # At least 10 failures
            should_alert = True
            reasons.append("High volume of recent failures detected")

        return should_alert, reasons

    def _classify_failure(
        self, status_code: int, response_headers: Dict[str, str], response_body: Optional[str]
    ) -> FailureType:
        """
        Classify the type of failure based on response characteristics.

        Args:
            status_code: HTTP status code
            response_headers: Response headers
            response_body: Response body

        Returns:
            Classified failure type
        """
        # DataDome can flag a response with any status code (including 200), so
        # check the DataDome indicators before bucketing by status.
        datadome = self._detect_datadome(response_headers, response_body)
        if datadome is not None:
            return datadome

        if status_code != 403:
            if status_code == 429:
                return FailureType.RATE_LIMITING
            elif status_code >= 500:
                return FailureType.NETWORK_ERROR
            else:
                return FailureType.OTHER

        if response_body:
            body_lower = response_body.lower()
            # Other automation detection patterns
            if any(pattern in body_lower for pattern in ["bot", "automation", "crawler", "robot", "scraping"]):
                return FailureType.AUTOMATION_DETECTION

        return FailureType.UNKNOWN_403

    @staticmethod
    def _detect_datadome(
        response_headers: Dict[str, str], response_body: Optional[str]
    ) -> Optional[FailureType]:
        """
        Detect a DataDome interstitial from response headers and body.

        HTTP/2 lowercases header names by default, so the x-datadome marker
        can arrive as any case variant — match case-insensitively.

        Returns:
            DATADOME_CAPTCHA for captcha challenges, DATADOME_COOKIE for other
            DataDome markers, or None when no DataDome signature is present.
        """
        if response_headers and any(k.lower() == "x-datadome" for k in response_headers):
            return FailureType.DATADOME_COOKIE
        if response_body:
            body_lower = response_body.lower()
            if "datadome" in body_lower or "captcha-delivery.com" in body_lower:
                if "captcha" in body_lower:
                    return FailureType.DATADOME_CAPTCHA
                return FailureType.DATADOME_COOKIE
        return None

    def _extract_additional_context(self, response_headers: Dict[str, str], response_body: Optional[str]) -> JSONDict:
        """
        Extract additional context from the response for debugging.

        Args:
            response_headers: Response headers
            response_body: Response body

        Returns:
            Dictionary with additional context
        """
        context = {}

        for key, value in (response_headers or {}).items():
            key_lower = key.lower()
            if key_lower == "x-datadome":
                context["datadome_id"] = value
            elif key_lower == "x-ratelimit-remaining":
                context["rate_limit_remaining"] = value

        if response_body and "captcha-delivery.com" in response_body:
            context["has_captcha_challenge"] = True

        return context

    def _store_failure_event(self, failure_event: FailureEvent) -> None:
        """
        Store a failure event, managing memory limits.

        Args:
            failure_event: The failure event to store
        """
        self.failure_events.append(failure_event)

        # Trim old events if we exceed the limit
        if len(self.failure_events) > self.max_events_stored:
            # Remove oldest events
            self.failure_events = self.failure_events[-self.max_events_stored :]

        # Invalidate stats cache
        self._invalidate_stats_cache()

    def _calculate_stats(self) -> FailureStats:
        """
        Calculate current failure statistics.

        Returns:
            Calculated failure statistics
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self.window_minutes)

        # Get failures in the current window
        window_failures = [event for event in self.failure_events if event.timestamp >= window_start]

        # Calculate failure counts by type
        failures_by_type = {}
        for failure in window_failures:
            failures_by_type[failure.failure_type] = failures_by_type.get(failure.failure_type, 0) + 1

        # Calculate consecutive failures (from the end)
        consecutive_failures = 0
        for i in range(len(self.failure_events) - 1, -1, -1):
            if self.failure_events[i].timestamp >= window_start:
                consecutive_failures += 1
            else:
                break

        # Calculate failure rate
        total_window_requests = len(window_failures) + max(0, self.success_count)
        failure_rate = 0.0
        if total_window_requests > 0:
            failure_rate = (len(window_failures) / total_window_requests) * 100.0

        # Find last success and failure times
        last_failure = None
        if self.failure_events:
            last_failure = max(event.timestamp for event in self.failure_events)

        # For last success, this is simplified - in production you might track success events
        last_success = None

        return FailureStats(
            total_requests=self.total_requests,
            total_failures=len(self.failure_events),
            failure_rate=failure_rate,
            failures_by_type=failures_by_type,
            last_success=last_success,
            last_failure=last_failure,
            consecutive_failures=consecutive_failures,
        )

    def _invalidate_stats_cache(self) -> None:
        """Invalidate the statistics cache."""
        self._stats_cache = None
        self._stats_cache_time = None

    def _log_failure(self, failure_event: FailureEvent) -> None:
        """
        Log a failure event.

        Args:
            failure_event: The failure event to log
        """
        if not self.logger:
            return

        message = (
            f"Tixr API failure: event_id={failure_event.event_id}, "
            f"status={failure_event.status_code}, "
            f"type={failure_event.failure_type.value}"
        )

        if hasattr(self.logger, "log_warning"):
            self.logger.log_warning(message)
        elif hasattr(self.logger, "warning"):
            self.logger.warning(message)

    def export_metrics(self) -> JSONDict:
        """
        Export metrics for external monitoring systems.

        Returns:
            Dictionary containing all relevant metrics
        """
        stats = self.get_current_stats()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_requests": stats.total_requests,
            "total_failures": stats.total_failures,
            "failure_rate_percent": stats.failure_rate,
            "consecutive_failures": stats.consecutive_failures,
            "failures_by_type": {failure_type.value: count for failure_type, count in stats.failures_by_type.items()},
            "last_failure": stats.last_failure.isoformat() if stats.last_failure else None,
            "window_minutes": self.window_minutes,
            "is_cookie_issue_detected": self.is_cookie_issue_detected(),
        }
