from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from gioe_libs.alerting import Alert as GioeAlert
from gioe_libs.alerting import AlertSeverity as GioeSeverity

from .alerts import Alert
from .channels import AlertChannel


class BaseAlertSystem(ABC):
    """
    Generic alert system:
    - Deduplication, cooldown, and history
    - Channel fan-out
    - Pluggable detection via detect_alerts()
    """

    def __init__(
        self,
        channels: List[AlertChannel],
        logger=None,
        check_interval: timedelta = timedelta(minutes=5),
        alert_cooldown: timedelta = timedelta(minutes=30),
        max_history: int = 1000,
    ):
        self.channels = channels
        self.logger = logger

        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.last_check: Optional[datetime] = None

        self.check_interval = check_interval
        self.alert_cooldown = alert_cooldown
        self.max_history = max_history

    async def check_and_alert(self) -> List[Alert]:
        now = datetime.utcnow()

        if self.last_check and now - self.last_check < self.check_interval:
            return []

        self.last_check = now
        triggered_alerts: List[Alert] = []

        alerts_to_trigger = await self.detect_alerts()

        for alert in alerts_to_trigger:
            if self._should_trigger_alert(alert):
                await self._trigger_alert(alert)
                triggered_alerts.append(alert)

        self._cleanup_resolved_alerts()
        return triggered_alerts

    def resolve_alert(self, alert_id: str) -> bool:
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()

            del self.active_alerts[alert_id]
            self.alert_history.append(alert)

            self._log_info(f"Alert {alert_id} manually resolved")
            return True
        return False

    def get_active_alerts(self) -> List[Alert]:
        return list(self.active_alerts.values())

    def get_alert_summary(self) -> Dict:
        active_alerts = self.get_active_alerts()
        severity_counts: Dict[str, int] = {}
        for alert in active_alerts:
            severity_counts[alert.severity.value] = severity_counts.get(alert.severity.value, 0) + 1

        return {
            "active_alerts_count": len(active_alerts),
            "severity_breakdown": severity_counts,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "failure_monitor_stats": self.get_metrics(),
        }

    @abstractmethod
    async def detect_alerts(self) -> List[Alert]:
        """Return a list of alerts that should be considered for triggering."""

    def get_metrics(self) -> Dict:
        """Optional metrics for summary; subclasses can override."""
        return {}

    def _should_trigger_alert(self, alert: Alert) -> bool:
        now = datetime.utcnow()

        if alert.id in self.active_alerts:
            return False

        for historical_alert in reversed(self.alert_history):
            if historical_alert.id == alert.id and now - historical_alert.timestamp < self.alert_cooldown:
                return False

        return True

    _DISCORD_EMBED_LIMIT = 2048

    async def _trigger_alert(self, alert: Alert) -> None:
        self.active_alerts[alert.id] = alert

        description = alert.description
        if len(description) > self._DISCORD_EMBED_LIMIT:
            description = description[: self._DISCORD_EMBED_LIMIT - 3] + "..."

        gioe_alert = GioeAlert(
            title=alert.title,
            message=description,
            severity=GioeSeverity(alert.severity.value),
            metadata=alert.metadata,
        )

        for channel in self.channels:
            try:
                success = channel.send(gioe_alert)
                if success:
                    self._log_info(f"Alert {alert.id} sent successfully via {type(channel).__name__}")
                else:
                    self._log_warning(f"Failed to send alert {alert.id} via {type(channel).__name__}")
            except Exception as e:
                self._log_error(f"Error sending alert {alert.id} via {type(channel).__name__}: {e}")

        self._log_info(f"Alert triggered: {alert.title} (severity: {alert.severity.value})")

    def _cleanup_resolved_alerts(self) -> None:
        now = datetime.utcnow()
        to_resolve: List[str] = []

        for alert_id, alert in self.active_alerts.items():
            if now - alert.timestamp > timedelta(hours=4):
                if self._has_condition_improved(alert):
                    to_resolve.append(alert_id)

        for alert_id in to_resolve:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = now
            del self.active_alerts[alert_id]
            self.alert_history.append(alert)
            self._log_info(f"Auto-resolved alert {alert_id}")

        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history :]

    def _has_condition_improved(self, alert: Alert) -> bool:
        """Subclasses can implement smarter checks; defaults to False."""
        return False

    def _log_info(self, message: str) -> None:
        if self.logger and hasattr(self.logger, "log_info"):
            self.logger.log_info(message)
        elif self.logger and hasattr(self.logger, "info"):
            self.logger.info(message)

    def _log_warning(self, message: str) -> None:
        if self.logger and hasattr(self.logger, "log_warning"):
            self.logger.log_warning(message)
        elif self.logger and hasattr(self.logger, "warning"):
            self.logger.warning(message)

    def _log_error(self, message: str) -> None:
        if self.logger and hasattr(self.logger, "log_error"):
            self.logger.log_error(message)
        elif self.logger and hasattr(self.logger, "error"):
            self.logger.error(message)
