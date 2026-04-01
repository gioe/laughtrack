import json
from abc import ABC, abstractmethod
from typing import List

from laughtrack.domain.entities.email import EmailMessage
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.email.service import EmailService

from .alerts import Alert

from gioe_libs.alerting import (  # noqa: F401
    DiscordAlertChannel,
    WebhookAlertChannel,
)


class AlertChannel(ABC):
    """Abstract base class for alert channels."""

    @abstractmethod
    def send_alert(self, alert: Alert) -> bool:
        """Send an alert through this channel."""


class EmailAlertChannel(AlertChannel):
    """Email alert channel using static EmailService."""

    def __init__(self, recipients: List[str]):
        self.recipients = recipients

    def send_alert(self, alert: Alert) -> bool:
        return self.send_from_local(alert)

    def send(self, alert) -> bool:
        """Send a gioe_libs Alert via email."""
        try:
            subject = f"[{alert.severity.value.upper()}] {alert.title}"
            body = f"""Alert: {alert.title}
Severity: {alert.severity.value}

Description:
{alert.message}

Metadata:
{json.dumps(alert.metadata, indent=2, default=str)}
"""
            message = EmailMessage(
                to_emails=self.recipients,
                subject=subject,
                html_content=body.replace("\n", "<br>\n"),
                text_content=body,
            )
            return EmailService.send_email(message)
        except Exception as e:
            Logger.error(f"Failed to send email alert: {e}")
            return False

    def send_from_local(self, alert: Alert) -> bool:
        """Send a local Alert via email (used internally)."""
        try:
            subject = f"[{alert.severity.value.upper()}] {alert.title}"
            body = f"""
Alert: {alert.title}
Severity: {alert.severity.value}
Timestamp: {alert.timestamp.isoformat()}
Source: {alert.source}

Description:
{alert.description}

Metadata:
{json.dumps(alert.metadata, indent=2)}
            """
            message = EmailMessage(
                to_emails=self.recipients,
                subject=subject,
                html_content=body.replace("\n", "<br>\n"),
                text_content=body,
            )
            return EmailService.send_email(message)
        except Exception as e:
            Logger.error(f"Failed to send email alert: {e}")
            return False
