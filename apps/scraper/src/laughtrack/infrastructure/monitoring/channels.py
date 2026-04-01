import json
from abc import ABC
from typing import List

from laughtrack.domain.entities.email import EmailMessage
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.email.service import EmailService

from gioe_libs.alerting import (  # noqa: F401
    DiscordAlertChannel,
    WebhookAlertChannel,
)


class AlertChannel(ABC):
    """Abstract base class for alert channels."""


class EmailAlertChannel(AlertChannel):
    """Email alert channel using static EmailService."""

    def __init__(self, recipients: List[str]):
        self.recipients = recipients

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
