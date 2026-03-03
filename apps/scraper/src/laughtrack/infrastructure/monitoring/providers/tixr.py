from __future__ import annotations

from datetime import timedelta
from typing import Optional

from laughtrack.core.clients.tixr.tixr_failure_monitor import TixrFailureMonitor
from typing import cast
from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
from laughtrack.infrastructure.monitoring.alert_system import (
    EmailAlertChannel,
    SlackAlertChannel,
    WebhookAlertChannel,
)
from laughtrack.infrastructure.monitoring.tixr_alert_system import TixrAlertSystem
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .base import FailureMonitorProtocol, MonitoringProvider


class TixrMonitoringProvider(MonitoringProvider):
    def create_failure_monitor(self, config: MonitoringConfig) -> TixrFailureMonitor:
        return TixrFailureMonitor(
            window_minutes=config.failure_window_minutes,
            max_events_stored=config.max_events_stored,
            logger=None,
        )

    def create_alert_system(
        self, monitor: FailureMonitorProtocol, channels: list, config: MonitoringConfig
    ) -> Optional[TixrAlertSystem]:
        if not channels:
            Logger.warn("No alert channels configured - monitoring will run without alerts")
            return None

        # monitor is a TixrFailureMonitor in this provider
        alert_system = TixrAlertSystem(
            failure_monitor=cast(TixrFailureMonitor, monitor), channels=channels, logger=None
        )
        alert_system.check_interval = timedelta(minutes=config.alert_check_interval_minutes)
        alert_system.alert_cooldown = timedelta(minutes=config.alert_cooldown_minutes)
        return alert_system

    @staticmethod
    def build_channels(config: MonitoringConfig) -> list:
        channels = []
        if config.is_email_configured() and config.alert_recipients:
            channels.append(EmailAlertChannel(recipients=config.alert_recipients))
            Logger.info(f"Email alerts configured for {len(config.alert_recipients)} recipients")
        if config.is_slack_configured() and config.slack_webhook_url:
            channels.append(SlackAlertChannel(webhook_url=config.slack_webhook_url, channel=config.slack_channel))
            Logger.info("Slack alerts configured")
        if config.is_webhook_configured() and config.webhook_url:
            channels.append(WebhookAlertChannel(webhook_url=config.webhook_url, headers=config.webhook_headers or {}))
            Logger.info("Webhook alerts configured")
        return channels
