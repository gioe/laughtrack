from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from laughtrack.domain.entities.email import EmailMessage, EmailTemplate
from laughtrack.foundation.models.types import JSONDict
from laughtrack.infrastructure.config.config_manager import ConfigManager
from laughtrack.infrastructure.email.providers import EmailProvider, MockEmailProvider, SMTPProvider
from laughtrack.infrastructure.email.templates import EmailTemplateRegistry, EmailTemplateRenderer
from laughtrack.utilities.infrastructure.email.utils import EmailUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


class EmailService:
    """
    Generic email service supporting multiple providers and templates.
    Static class with class-level state for application-wide email functionality.
    """

    # Class-level state
    _provider: Optional[EmailProvider] = None
    _renderer: Optional[EmailTemplateRenderer] = None
    _template_registry: Optional[EmailTemplateRegistry] = None
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Initialize the service if not already initialized."""
        if cls._initialized:
            return

        # Initialize with default provider
        config_manager = ConfigManager()
        email_config = config_manager.get_email_configuration()

        # Use mock provider if no real SMTP config
        if not email_config.get("smtp_username") or not email_config.get("smtp_password"):
            cls._provider = MockEmailProvider(email_config)
        else:
            cls._provider = SMTPProvider(email_config)

        cls._renderer = EmailTemplateRenderer()
        cls._template_registry = EmailTemplateRegistry()
        cls._initialized = True

        if not cls._provider.is_configured():
            Logger.warn(f"Email provider {type(cls._provider).__name__} not configured")

    @classmethod
    def initialize_with_provider(cls, provider: EmailProvider) -> None:
        """Initialize the service with a custom provider."""
        cls._provider = provider
        cls._renderer = EmailTemplateRenderer()
        cls._template_registry = EmailTemplateRegistry()
        cls._initialized = True

        if not cls._provider.is_configured():
            Logger.warn(f"Email provider {type(cls._provider).__name__} not configured")

    @classmethod
    def register_template(cls, template: EmailTemplate) -> None:
        """Register a new email template."""
        cls._ensure_initialized()
        assert cls._template_registry is not None
        cls._template_registry.register_template(template)

    @classmethod
    def send_email(cls, message: EmailMessage) -> bool:
        """Send a single email message."""
        cls._ensure_initialized()
        assert cls._provider is not None
        return cls._provider.send_email(message)

    @classmethod
    def send_templated_email(cls, template_id: str, to_emails: Union[str, List[str]], data: JSONDict) -> bool:
        """Send an email using a registered template."""
        cls._ensure_initialized()
        assert cls._template_registry is not None
        assert cls._renderer is not None

        if not cls._template_registry.has_template(template_id):
            Logger.error(f"Template '{template_id}' not found")
            return False

        template = cls._template_registry.get_template(template_id)

        # Add to_emails to data for rendering
        data = data.copy()
        data["to_emails"] = to_emails

        message = cls._renderer.render_template(template, data)
        return cls.send_email(message)

    @classmethod
    def send_dashboard_report_from_file(
        cls,
        dashboard_path: Optional[Union[str, Path]] = None,
        wrap_for_email: bool = True,
    ) -> bool:
        """Send dashboard report email by reading HTML from file."""
        if dashboard_path is None:
            dashboard_path = EmailUtils.get_default_dashboard_path()

        dashboard_html = EmailUtils.read_dashboard_html(dashboard_path)
        if dashboard_html is None:
            Logger.error(f"Could not read dashboard file: {dashboard_path}")
            return False

        if wrap_for_email:
            dashboard_html = EmailUtils.create_email_wrapper_html(dashboard_html)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return cls.send_templated_email(
            "dashboard_report", cls._load_email_recipients(), {"dashboard_html": dashboard_html, "timestamp": timestamp}
        )

    @classmethod
    def send_scraping_session_summary(cls, session_summary: JSONDict) -> bool:
        """Send a summary email after a scraping session."""
        return cls.send_templated_email("session_summary", cls._load_email_recipients(), session_summary)

    @classmethod
    def _load_email_recipients(cls) -> List[str]:
        """Load email recipients from configuration."""
        # Hardcoded fallback email
        DEFAULT_EMAIL_RECIPIENT = "admin@laugh-track.com"

        try:
            config = ConfigManager()
            email_config = config.get_section("email")
            recipients = email_config.get("scraping_report_recipients", [])

            # If recipients is a string, convert to list
            if isinstance(recipients, str):
                recipients = [recipients]

            # If no recipients configured, use hardcoded default
            if not recipients:
                recipients = [DEFAULT_EMAIL_RECIPIENT]

            return recipients
        except Exception as e:
            Logger.warn(f"Could not load email recipients: {e}")
            # Return hardcoded default as fallback
            Logger.info(f"Using fallback email recipient: {DEFAULT_EMAIL_RECIPIENT}")
            return [DEFAULT_EMAIL_RECIPIENT]
