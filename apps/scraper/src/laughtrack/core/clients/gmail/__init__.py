"""Gmail API client for reading incoming emails."""

from .client import EmailInboxClient, GmailMessage

__all__ = [
    "EmailInboxClient",
    "GmailMessage",
]
