from typing import Any, Dict

from laughtrack.domain.entities.email import EmailMessage
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.infrastructure.email.providers.base import EmailProvider


class MockEmailProvider(EmailProvider):
    """Mock email provider for testing and development."""

    def __init__(self, config: JSONDict):
        self.default_from_email = config.get("from_email", "admin@laugh-track.com")
        self.default_from_name = config.get("from_name", "Laughtrack Scraper")

    def is_configured(self) -> bool:
        """Mock provider is always configured."""
        return True

    def send_email(self, message: EmailMessage) -> bool:
        """Mock email sending - just logs the email details."""
        to_emails = message.to_emails if isinstance(message.to_emails, list) else [message.to_emails]

        Logger.info(f"[MOCK EMAIL] To: {to_emails}, Subject: {message.subject}")
        Logger.info(f"[MOCK EMAIL] HTML content length: {len(message.html_content)} chars")

        return True
