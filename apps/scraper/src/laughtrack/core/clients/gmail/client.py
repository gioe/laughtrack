import base64
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class GmailMessage:
    """Represents a single Gmail message with its metadata and body content."""

    message_id: str
    thread_id: str
    subject: str
    sender: str
    date: str
    snippet: str
    html_body: Optional[str] = field(default=None)
    text_body: Optional[str] = field(default=None)


class EmailInboxClient:
    """
    Client for reading emails from a Gmail inbox via the Gmail API.

    Authenticates using OAuth2 credentials (client_id, client_secret, refresh_token)
    loaded from environment variables. Supports listing unread emails filtered by
    sender domain and fetching full email content by message ID.

    Required environment variables:
        GMAIL_CLIENT_ID      — OAuth2 client ID
        GMAIL_CLIENT_SECRET  — OAuth2 client secret
        GMAIL_REFRESH_TOKEN  — OAuth2 refresh token for the target Gmail account

    Usage:
        client = EmailInboxClient()
        emails = client.list_unread_emails("ticketmaster.com")
        for email in emails:
            detail = client.fetch_email(email.message_id)
    """

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self) -> None:
        self._client_id = os.environ.get("GMAIL_CLIENT_ID", "")
        self._client_secret = os.environ.get("GMAIL_CLIENT_SECRET", "")
        self._refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN", "")
        self._service = None

    def _build_service(self):
        """Build and return an authenticated Gmail API service object."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=None,
            refresh_token=self._refresh_token,
            client_id=self._client_id,
            client_secret=self._client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        creds.refresh(Request())
        return build("gmail", "v1", credentials=creds)

    def _get_service(self):
        """Return a cached Gmail API service, creating it on first call."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def list_unread_emails(self, sender_domain: str) -> List[GmailMessage]:
        """
        List unread emails filtered by sender domain.

        Args:
            sender_domain: Domain to filter by (e.g. "ticketmaster.com").
                           Matches any sender whose address ends with @<domain>.

        Returns:
            List of GmailMessage objects with full body content fetched.
        """
        service = self._get_service()
        query = f"is:unread from:@{sender_domain}"

        Logger.debug(f"[EmailInboxClient] Listing unread emails from domain: {sender_domain}")

        result = service.users().messages().list(userId="me", q=query).execute()
        raw_messages = result.get("messages", [])

        emails: List[GmailMessage] = []
        for msg in raw_messages:
            email = self.fetch_email(msg["id"])
            if email is not None:
                emails.append(email)

        Logger.debug(f"[EmailInboxClient] Found {len(emails)} unread emails from @{sender_domain}")
        return emails

    def fetch_email(self, message_id: str) -> Optional[GmailMessage]:
        """
        Fetch the full email content for a given message ID.

        Args:
            message_id: The Gmail message ID to retrieve.

        Returns:
            GmailMessage with metadata and body, or None if retrieval fails.
        """
        service = self._get_service()

        try:
            msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        except Exception as exc:
            Logger.debug(f"[EmailInboxClient] Failed to fetch message {message_id}: {exc}")
            return None

        payload = msg.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        html_body, text_body = self._extract_bodies(payload)

        return GmailMessage(
            message_id=msg["id"],
            thread_id=msg["threadId"],
            subject=headers.get("Subject", ""),
            sender=headers.get("From", ""),
            date=headers.get("Date", ""),
            snippet=msg.get("snippet", ""),
            html_body=html_body,
            text_body=text_body,
        )

    def _extract_bodies(self, payload: dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Recursively extract HTML and plain-text bodies from a message payload.

        Args:
            payload: The 'payload' dict from a Gmail API message response.

        Returns:
            Tuple of (html_body, text_body), either may be None.
        """
        html_body: Optional[str] = None
        text_body: Optional[str] = None

        mime_type = payload.get("mimeType", "")

        if mime_type == "text/html":
            html_body = self._decode_body(payload.get("body", {}).get("data", ""))
        elif mime_type == "text/plain":
            text_body = self._decode_body(payload.get("body", {}).get("data", ""))
        elif mime_type.startswith("multipart/"):
            for part in payload.get("parts", []):
                part_mime = part.get("mimeType", "")
                if part_mime == "text/html" and html_body is None:
                    html_body = self._decode_body(part.get("body", {}).get("data", ""))
                elif part_mime == "text/plain" and text_body is None:
                    text_body = self._decode_body(part.get("body", {}).get("data", ""))
                elif part_mime.startswith("multipart/"):
                    nested_html, nested_text = self._extract_bodies(part)
                    html_body = html_body or nested_html
                    text_body = text_body or nested_text

        return html_body, text_body

    @staticmethod
    def _decode_body(data: str) -> Optional[str]:
        """Decode a base64url-encoded email body string."""
        if not data:
            return None
        try:
            return base64.urlsafe_b64decode(data).decode("utf-8")
        except Exception:
            return None
