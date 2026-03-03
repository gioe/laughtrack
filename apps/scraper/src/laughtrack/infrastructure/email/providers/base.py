from abc import ABC, abstractmethod

from laughtrack.domain.entities.email import EmailMessage


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    def send_email(self, message: EmailMessage) -> bool:
        """Send an email message."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
