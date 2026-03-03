import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

from laughtrack.domain.entities.email import EmailMessage
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict
from laughtrack.infrastructure.config.config_manager import ConfigManager
from laughtrack.infrastructure.email.providers.base import EmailProvider


class SMTPProvider(EmailProvider):
    """Native SMTP email provider implementation."""

    def __init__(self, config: Optional[JSONDict] = None):

        if config is None:
            config = ConfigManager().get_email_configuration()

        self.smtp_server: str = config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port: int = config.get("smtp_port", 587)
        self.username: Optional[str] = config.get("smtp_username")
        self.password: Optional[str] = config.get("smtp_password")
        self.use_tls: bool = config.get("smtp_use_tls", True)
        self.use_ssl: bool = config.get("smtp_use_ssl", False)

        # From/name configuration from ConfigManager
        self.default_from_email: str = config.get("from_email", "admin@laugh-track.com")
        self.default_from_name: str = config.get("from_name", "Laughtrack")

    def is_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(self.username and self.password and self.smtp_server)

    def send_email(self, message: EmailMessage) -> bool:
        """Send email via SMTP."""
        if not self.is_configured():
            Logger.warn("SMTP credentials not configured (username, password, server required)")
            return False

        to_emails = None  # Ensure defined for exception block
        try:
            # Prepare email addresses
            to_emails = message.to_emails if isinstance(message.to_emails, list) else [message.to_emails]
            from_email = message.from_email or self.default_from_email
            from_name = message.from_name or self.default_from_name

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = str(Header(message.subject, "utf-8"))
            # Fix: formataddr expects str, Header(...).encode() returns bytes
            msg["From"] = formataddr((str(Header(from_name, "utf-8")), from_email))
            msg["To"] = ", ".join(to_emails)

            # Set charset for the message
            msg.set_charset("utf-8")

            if message.reply_to:
                msg["Reply-To"] = message.reply_to

            # Add text content if provided
            if message.text_content:
                text_part = MIMEText(message.text_content, "plain", "utf-8")
                msg.attach(text_part)

            # Add HTML content if provided
            if message.html_content:
                html_part = MIMEText(message.html_content, "html", "utf-8")
                msg.attach(html_part)

            # Send email
            context = ssl.create_default_context()

            username = self.username or ""
            password = self.password or ""

            if self.use_ssl:
                # Use SSL (usually port 465)
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(username, password)
                    server.sendmail(from_email, to_emails, msg.as_string())
            else:
                # Use TLS (usually port 587)
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls(context=context)
                    server.login(username, password)
                    server.sendmail(from_email, to_emails, msg.as_string())

            Logger.info(f"Email sent successfully to {to_emails}")
            return True

        except Exception as e:
            Logger.error(f"Error sending email to {to_emails if to_emails else '[unknown]'}: {str(e)}")
            return False
