import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from laughtrack.domain.entities.email import EmailMessage
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.infrastructure.email.service import EmailService

from .alerts import Alert


class AlertChannel(ABC):
    """Abstract base class for alert channels."""

    @abstractmethod
    async def send_alert(self, alert: Alert) -> bool:
        """
        Send an alert through this channel.

        Args:
            alert: The alert to send

        Returns:
            True if alert was sent successfully, False otherwise
        """


class EmailAlertChannel(AlertChannel):
    """Email alert channel using static EmailService."""

    def __init__(self, recipients: List[str]):
        self.recipients = recipients

    async def send_alert(self, alert: Alert) -> bool:
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


class SlackAlertChannel(AlertChannel):
    """Slack alert channel (placeholder for future implementation)."""

    def __init__(self, webhook_url: str, channel: str = "#alerts"):
        self.webhook_url = webhook_url
        self.channel = channel

    async def send_alert(self, alert: Alert) -> bool:
        # TODO: Implement Slack webhook integration
        Logger.warning(f"[SLACK] {alert.severity.value}: {alert.title} (Slack not implemented)")
        return True


class WebhookAlertChannel(AlertChannel):
    """Generic webhook alert channel."""

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}

    async def send_alert(self, alert: Alert) -> bool:
        try:
            import requests

            payload = {
                "id": alert.id,
                "title": alert.title,
                "description": alert.description,
                "severity": alert.severity.value,
                "timestamp": alert.timestamp.isoformat(),
                "source": alert.source,
                "metadata": alert.metadata,
            }

            response = requests.post(self.webhook_url, json=payload, headers=self.headers, timeout=10)

            return response.status_code == 200
        except Exception as e:
            Logger.error(f"Failed to send webhook alert: {e}")
            return False
