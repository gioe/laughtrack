"""Monitoring service package (public path preserved)."""

import asyncio
from datetime import timedelta
from typing import List, Optional, cast

from laughtrack.foundation.models.types import JSONDict
from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
from laughtrack.infrastructure.monitoring.alert_system import (
    DiscordAlertChannel,
    EmailAlertChannel,
    WebhookAlertChannel,
)
from laughtrack.infrastructure.monitoring.providers.base import FailureMonitorProtocol, MonitoringProvider
from laughtrack.infrastructure.monitoring.providers.tixr import TixrMonitoringProvider
from laughtrack.foundation.infrastructure.logger.logger import Logger


class MonitoringService:
    def __init__(self, config: Optional[MonitoringConfig] = None, provider: Optional[MonitoringProvider] = None):
        self.config = config or MonitoringConfig.default()
        self._provider = provider or TixrMonitoringProvider()
        self.failure_monitor = self._provider.create_failure_monitor(self.config)
        self.alert_system = self._create_alert_system()
        self._monitoring_task = None
        self._monitoring_running = False

    def _create_alert_system(self):  # type: ignore[no-untyped-def]
        channels: list
        try:
            build_channels = getattr(self._provider, "build_channels", None)
            if callable(build_channels):
                channels = cast(list, build_channels(self.config))
            else:
                channels = self._build_channels_default()
        except Exception:  # pragma: no cover
            channels = self._build_channels_default()
        return self._provider.create_alert_system(self.failure_monitor, channels, self.config)

    def _build_channels_default(self) -> list:  # type: ignore[override]
        channels = []
        if self.config.is_email_configured() and self.config.alert_recipients:
            channels.append(EmailAlertChannel(recipients=self.config.alert_recipients))
            Logger.info(f"Email alerts configured for {len(self.config.alert_recipients)} recipients")
        if self.config.is_discord_configured() and self.config.discord_webhook_url:
            channels.append(DiscordAlertChannel(webhook_url=self.config.discord_webhook_url))
            Logger.info("Discord alerts configured")
        if self.config.is_webhook_configured() and self.config.webhook_url:
            channels.append(
                WebhookAlertChannel(webhook_url=self.config.webhook_url, headers=self.config.webhook_headers or {})
            )
            Logger.info("Webhook alerts configured")
        if not channels:
            Logger.warn("No alert channels configured - monitoring will run without alerts")
        return channels

    def get_failure_monitor(self) -> FailureMonitorProtocol:
        return self.failure_monitor

    async def start_background_monitoring(self, check_interval_minutes: Optional[int] = None) -> None:
        if self._monitoring_running:
            Logger.warn("Background monitoring is already running")
            return
        if not self.alert_system:
            Logger.warn("Alert system not initialized - background monitoring disabled")
            return
        interval = check_interval_minutes or self.config.alert_check_interval_minutes
        self._monitoring_running = True
        self._monitoring_task = asyncio.create_task(self._background_monitoring_loop(interval))
        Logger.info(f"Started background monitoring with {interval}-minute intervals")

    async def stop_background_monitoring(self) -> None:
        if not self._monitoring_running:
            return
        self._monitoring_running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:  # pragma: no cover
                pass
        Logger.info("Stopped background monitoring")

    async def check_alerts_now(self) -> List[JSONDict]:
        if not self.alert_system:
            return []
        alerts = await self.alert_system.check_and_alert()
        return [
            {
                "id": alert.id,
                "title": alert.title,
                "severity": alert.severity.value,
                "timestamp": alert.timestamp.isoformat(),
                "description": alert.description,
            }
            for alert in alerts
        ]

    def get_monitoring_summary(self) -> JSONDict:
        summary = {
            "monitoring_active": self._monitoring_running,
            "failure_monitor": self.failure_monitor.export_metrics(),
            "alert_system": None,
        }
        if self.alert_system:
            summary["alert_system"] = self.alert_system.get_alert_summary()
        return summary

    def get_failure_stats(self, window_minutes: Optional[int] = None) -> JSONDict:
        stats = self.failure_monitor.get_current_stats()
        if window_minutes:
            failure_rate = self.failure_monitor.get_failure_rate(window_minutes)
            failure_pattern = self.failure_monitor.get_failure_pattern(window_minutes)
        else:
            failure_rate = stats.failure_rate
            failure_pattern = stats.failures_by_type
        return {
            "failure_rate_percent": failure_rate,
            "total_requests": stats.total_requests,
            "total_failures": stats.total_failures,
            "consecutive_failures": stats.consecutive_failures,
            "failures_by_type": {
                (failure_type.value if hasattr(failure_type, "value") else str(failure_type)): count
                for failure_type, count in failure_pattern.items()
            },
            "last_failure": stats.last_failure.isoformat() if stats.last_failure else None,
            "is_cookie_issue_detected": self.failure_monitor.is_cookie_issue_detected(),
            "window_minutes": window_minutes or self.failure_monitor.window_minutes,
        }

    def get_active_alerts(self) -> List[JSONDict]:
        if not self.alert_system:
            return []
        return [
            {
                "id": alert.id,
                "title": alert.title,
                "severity": alert.severity.value,
                "timestamp": alert.timestamp.isoformat(),
                "description": alert.description,
                "metadata": alert.metadata,
            }
            for alert in self.alert_system.get_active_alerts()
        ]

    def resolve_alert(self, alert_id: str) -> bool:
        if not self.alert_system:
            return False
        return self.alert_system.resolve_alert(alert_id)

    async def _background_monitoring_loop(self, check_interval_minutes: int) -> None:
        check_interval = timedelta(minutes=check_interval_minutes)
        while self._monitoring_running:
            try:
                if self.alert_system:
                    await self.alert_system.check_and_alert()
                await asyncio.sleep(check_interval.total_seconds())
            except asyncio.CancelledError:  # pragma: no cover
                break
            except Exception as e:  # pragma: no cover
                Logger.error(f"Error in background monitoring loop: {e}")
                await asyncio.sleep(60)

__all__ = ["MonitoringService"]
