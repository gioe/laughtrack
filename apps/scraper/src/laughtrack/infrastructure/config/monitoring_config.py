import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from laughtrack.infrastructure.config.config_manager import ConfigManager


@dataclass
class MonitoringConfig:
    """Configuration for the monitoring system."""

    # Failure monitoring settings
    failure_window_minutes: int = 60
    max_events_stored: int = 1000

    # Alert thresholds
    failure_rate_warning_threshold: float = 25.0
    failure_rate_critical_threshold: float = 50.0
    consecutive_failure_threshold: int = 5

    # Alert timing
    alert_check_interval_minutes: int = 5
    alert_cooldown_minutes: int = 30

    # Email settings
    alert_recipients: Optional[List[str]] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None

    # Slack settings
    slack_webhook_url: Optional[str] = None
    slack_channel: str = "#alerts"

    # Webhook settings
    webhook_url: Optional[str] = None
    webhook_headers: Optional[Dict[str, str]] = None

    # Background monitoring
    enable_background_monitoring: bool = True

    def __post_init__(self):
        """Initialize default values and validate config."""
        if self.alert_recipients is None:
            self.alert_recipients = []

        if self.webhook_headers is None:
            self.webhook_headers = {}

        # Load from environment variables if not set
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration from environment variables using ConfigManager."""
        # Get monitoring configuration from ConfigManager
        monitoring_config = ConfigManager.get_monitoring_configuration()
        email_config = ConfigManager.get_email_configuration()

        # Email configuration from ConfigManager
        if not self.smtp_host:
            self.smtp_host = email_config.get("smtp_server")
        if not self.smtp_username:
            self.smtp_username = email_config.get("smtp_username")
        if not self.smtp_password:
            self.smtp_password = email_config.get("smtp_password")
        if not self.email_from:
            self.email_from = email_config.get("from_email")

        # Monitoring-specific configuration from ConfigManager
        if not self.slack_webhook_url:
            self.slack_webhook_url = monitoring_config.get("slack_webhook_url")
        if not self.webhook_url:
            self.webhook_url = monitoring_config.get("monitoring_webhook_url")
        if not self.alert_recipients:
            self.alert_recipients = monitoring_config.get("alert_recipients", [])

        # Update thresholds from ConfigManager
        self.failure_rate_warning_threshold = monitoring_config.get(
            "failure_rate_warning_threshold", self.failure_rate_warning_threshold
        )
        self.failure_rate_critical_threshold = monitoring_config.get(
            "failure_rate_critical_threshold", self.failure_rate_critical_threshold
        )
        self.enable_background_monitoring = monitoring_config.get(
            "enable_background_monitoring", self.enable_background_monitoring
        )

    @classmethod
    def from_env(cls) -> "MonitoringConfig":
        """Create configuration instance loading all values from ConfigManager."""
        return cls()

    @classmethod
    def default(cls) -> "MonitoringConfig":
        """Create configuration with default values."""
        return cls()

    def is_email_configured(self) -> bool:
        """Check if email alerting is properly configured."""
        return bool(
            self.smtp_host and self.smtp_username and self.smtp_password and self.email_from and self.alert_recipients
        )

    def is_slack_configured(self) -> bool:
        """Check if Slack alerting is properly configured."""
        return bool(self.slack_webhook_url)

    def is_webhook_configured(self) -> bool:
        """Check if webhook alerting is properly configured."""
        return bool(self.webhook_url)

    def get_configured_channels(self) -> List[str]:
        """Get list of configured alert channels."""
        channels = []
        if self.is_email_configured():
            channels.append("email")
        if self.is_slack_configured():
            channels.append("slack")
        if self.is_webhook_configured():
            channels.append("webhook")
        return channels

    def validate(self) -> List[str]:
        """
        Validate the configuration and return list of issues.

        Returns:
            List of validation error messages
        """
        issues = []

        # Check that at least one alert channel is configured
        if not self.get_configured_channels():
            issues.append("No alert channels configured (email, Slack, or webhook)")

        # Validate thresholds
        if self.failure_rate_warning_threshold >= self.failure_rate_critical_threshold:
            issues.append("Warning threshold must be less than critical threshold")

        if self.failure_rate_warning_threshold < 0 or self.failure_rate_critical_threshold > 100:
            issues.append("Failure rate thresholds must be between 0 and 100")

        if self.consecutive_failure_threshold < 1:
            issues.append("Consecutive failure threshold must be at least 1")

        # Validate timing settings
        if self.alert_check_interval_minutes < 1:
            issues.append("Alert check interval must be at least 1 minute")

        if self.alert_cooldown_minutes < 1:
            issues.append("Alert cooldown must be at least 1 minute")

        # Validate email configuration if partially configured
        email_fields = [self.smtp_host, self.smtp_username, self.smtp_password, self.email_from]
        email_configured_count = sum(1 for field in email_fields if field)

        if 0 < email_configured_count < len(email_fields):
            issues.append(
                "Email configuration is incomplete (need all of: smtp_host, smtp_username, smtp_password, email_from)"
            )

        return issues
