from datetime import datetime
from typing import Dict, List, Optional

from laughtrack.core.clients.tixr.tixr_failure_monitor import FailureType, TixrFailureMonitor

from .alerts import Alert, AlertSeverity
from .base_system import BaseAlertSystem


class TixrAlertSystem(BaseAlertSystem):
    """
    Tixr-specific alert system that uses TixrFailureMonitor to detect alert conditions.
    """

    def __init__(self, failure_monitor: TixrFailureMonitor, channels, logger=None):
        super().__init__(channels=channels, logger=logger)
        self.failure_monitor = failure_monitor

    async def detect_alerts(self) -> List[Alert]:
        alerts: List[Alert] = []

        high_failure_alert = self._check_high_failure_rate()
        if high_failure_alert:
            alerts.append(high_failure_alert)

        cookie_issue_alert = self._check_cookie_issues()
        if cookie_issue_alert:
            alerts.append(cookie_issue_alert)

        consecutive_alert = self._check_consecutive_failures()
        if consecutive_alert:
            alerts.append(consecutive_alert)

        degradation_alert = self._check_service_degradation()
        if degradation_alert:
            alerts.append(degradation_alert)

        return alerts

    def get_metrics(self) -> Dict:
        return self.failure_monitor.export_metrics()

    def _check_high_failure_rate(self) -> Optional[Alert]:
        stats = self.failure_monitor.get_current_stats()

        if stats.failure_rate > 50.0:
            return Alert(
                id="tixr_high_failure_rate",
                title="Tixr API High Failure Rate",
                description=f"Tixr API failure rate is {stats.failure_rate:.1f}% over the last {self.failure_monitor.window_minutes} minutes",
                severity=AlertSeverity.CRITICAL,
                timestamp=datetime.utcnow(),
                source="tixr_failure_monitor",
                metadata={
                    "failure_rate": stats.failure_rate,
                    "total_failures": stats.total_failures,
                    "window_minutes": self.failure_monitor.window_minutes,
                    "failures_by_type": {ft.value: count for ft, count in stats.failures_by_type.items()},
                },
            )
        elif stats.failure_rate > 25.0:
            return Alert(
                id="tixr_elevated_failure_rate",
                title="Tixr API Elevated Failure Rate",
                description=f"Tixr API failure rate is {stats.failure_rate:.1f}% over the last {self.failure_monitor.window_minutes} minutes",
                severity=AlertSeverity.HIGH,
                timestamp=datetime.utcnow(),
                source="tixr_failure_monitor",
                metadata={
                    "failure_rate": stats.failure_rate,
                    "total_failures": stats.total_failures,
                    "window_minutes": self.failure_monitor.window_minutes,
                },
            )

        return None

    def _check_cookie_issues(self) -> Optional[Alert]:
        if self.failure_monitor.is_cookie_issue_detected():
            pattern = self.failure_monitor.get_failure_pattern(30)

            datadome_failures = pattern.get(FailureType.DATADOME_COOKIE, 0) + pattern.get(
                FailureType.DATADOME_CAPTCHA, 0
            )

            return Alert(
                id="tixr_datadome_cookie_issue",
                title="Tixr DataDome Cookie Issue Detected",
                description=f"Detected {datadome_failures} DataDome-related failures in the last 30 minutes. Cookie may need refresh.",
                severity=AlertSeverity.HIGH,
                timestamp=datetime.utcnow(),
                source="tixr_failure_monitor",
                metadata={
                    "datadome_failures": datadome_failures,
                    "failure_pattern": {ft.value: count for ft, count in pattern.items()},
                    "suggested_action": "refresh_datadome_cookie",
                },
            )

        return None

    def _check_consecutive_failures(self) -> Optional[Alert]:
        stats = self.failure_monitor.get_current_stats()

        if stats.consecutive_failures >= 10:
            return Alert(
                id="tixr_consecutive_failures",
                title="Tixr API Consecutive Failures",
                description=f"Tixr API has {stats.consecutive_failures} consecutive failures",
                severity=AlertSeverity.CRITICAL,
                timestamp=datetime.utcnow(),
                source="tixr_failure_monitor",
                metadata={
                    "consecutive_failures": stats.consecutive_failures,
                    "last_failure": stats.last_failure.isoformat() if stats.last_failure else None,
                },
            )
        elif stats.consecutive_failures >= 5:
            return Alert(
                id="tixr_multiple_failures",
                title="Tixr API Multiple Consecutive Failures",
                description=f"Tixr API has {stats.consecutive_failures} consecutive failures",
                severity=AlertSeverity.MEDIUM,
                timestamp=datetime.utcnow(),
                source="tixr_failure_monitor",
                metadata={"consecutive_failures": stats.consecutive_failures},
            )

        return None

    def _check_service_degradation(self) -> Optional[Alert]:
        current_rate = self.failure_monitor.get_failure_rate(30)
        previous_rate = self.failure_monitor.get_failure_rate(60)

        if current_rate > 15.0 and current_rate > previous_rate * 2:
            return Alert(
                id="tixr_service_degradation",
                title="Tixr API Service Degradation",
                description=f"Tixr API failure rate increased from {previous_rate:.1f}% to {current_rate:.1f}%",
                severity=AlertSeverity.MEDIUM,
                timestamp=datetime.utcnow(),
                source="tixr_failure_monitor",
                metadata={
                    "current_failure_rate": current_rate,
                    "previous_failure_rate": previous_rate,
                    "degradation_factor": current_rate / max(previous_rate, 1.0),
                },
            )

        return None

    def _has_condition_improved(self, alert: Alert) -> bool:
        if alert.id in ["tixr_high_failure_rate", "tixr_elevated_failure_rate"]:
            current_rate = self.failure_monitor.get_failure_rate(30)
            return current_rate < 10.0

        if alert.id in ["tixr_consecutive_failures", "tixr_multiple_failures"]:
            stats = self.failure_monitor.get_current_stats()
            return stats.consecutive_failures < 2

        if alert.id == "tixr_datadome_cookie_issue":
            return not self.failure_monitor.is_cookie_issue_detected(15)

        return False
