import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from curl_cffi.requests import AsyncSession

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


class DiscordAlertChannel(AlertChannel):
    """Discord alert channel via incoming webhook."""

    _SEVERITY_COLORS = {
        "low": 0x36A64F,
        "medium": 0xFFCC00,
        "high": 0xFF8800,
        "critical": 0xCC0000,
    }

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_alert(self, alert: Alert) -> bool:
        try:
            color = self._SEVERITY_COLORS.get(alert.severity.value, 0x888888)
            embed: Dict = {
                "title": f"[{alert.severity.value.upper()}] {alert.title}",
                "description": alert.description,
                "color": color,
                "fields": [
                    {"name": "Source", "value": alert.source, "inline": True},
                    {"name": "Severity", "value": alert.severity.value, "inline": True},
                    {"name": "Time", "value": alert.timestamp.isoformat(), "inline": True},
                ],
            }
            if alert.metadata:
                embed["footer"] = {"text": json.dumps(alert.metadata)}

            payload = {"embeds": [embed]}

            async with AsyncSession(timeout=10) as session:
                response = await session.post(self.webhook_url, json=payload)
                if response.status_code in (200, 204):
                    return True
                body = response.text
                Logger.error(f"Discord webhook returned {response.status_code}: {body}")
                return False
        except Exception as e:
            Logger.error(f"Failed to send Discord alert: {e}")
            return False


class WebhookAlertChannel(AlertChannel):
    """Generic webhook alert channel."""

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}

    async def send_alert(self, alert: Alert) -> bool:
        try:
            payload = {
                "id": alert.id,
                "title": alert.title,
                "description": alert.description,
                "severity": alert.severity.value,
                "timestamp": alert.timestamp.isoformat(),
                "source": alert.source,
                "metadata": alert.metadata,
            }

            async with AsyncSession(timeout=10) as session:
                response = await session.post(self.webhook_url, json=payload, headers=self.headers)
                if response.status_code == 200:
                    return True
                body = response.text
                Logger.error(f"Webhook returned {response.status_code}: {body}")
                return False
        except Exception as e:
            Logger.error(f"Failed to send webhook alert: {e}")
            return False
