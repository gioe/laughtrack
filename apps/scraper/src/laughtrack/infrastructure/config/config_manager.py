import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ConfigManager:
    """
    Singleton class to manage configuration across the application.
    Loads configuration from environment variables and provides a centralized access point.

    Supported configuration sections:
    - database: Database connection settings
    - email: Email/SMTP configuration for notifications
    - scraper: Web scraping and request settings
    - api: External API keys and tokens (Eventbrite, Ticketmaster)
    - monitoring: Alert thresholds and notification settings

    Usage examples:
        # Instance-based usage (traditional)
        config = ConfigManager()
        db_config = config.get_database_config()

        # Class-based usage (no instantiation needed)
        db_config = ConfigManager.get_database_configuration()
        api_config = ConfigManager.get_api_configuration()

        # Direct value access
        db_host = ConfigManager.get_config('database', 'host')
        eventbrite_token = ConfigManager.get_config('api', 'eventbrite_token')
    """

    _instance = None
    _config: JSONDict = {}
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _clean_password(self, password: Optional[str]) -> str:
        """Clean non-breaking spaces and other problematic characters from password."""
        if not password:
            return ""

        # Replace non-breaking spaces (\xa0) with regular spaces
        cleaned = password.replace("\xa0", " ")

        # Strip quotes if present (from .env file)
        cleaned = cleaned.strip('"').strip("'")

        return cleaned

    def _load_config(self) -> None:
        """Load configuration from environment variables."""
        if self._loaded:
            return

        # Load .env file if it exists, searching up the tree
        def _find_env_file() -> Optional[Path]:
            # 1) explicit path override
            override = os.getenv("LAUGHTRACK_DOTENV_PATH")
            if override:
                p = Path(override)
                if p.exists():
                    return p

            # 2) search parents from this file up to repo root
            for parent in Path(__file__).resolve().parents:
                candidate = parent / ".env"
                if candidate.exists():
                    return candidate
            return None

        env_path = _find_env_file()
        if env_path:
            load_dotenv(dotenv_path=env_path, encoding="utf-8")

        # Database configuration
        _db_port_raw = os.getenv("DATABASE_PORT")
        if _db_port_raw:
            try:
                _db_port = int(_db_port_raw)
            except ValueError:
                raise ValueError(
                    f"DATABASE_PORT must be a valid integer, got: {_db_port_raw!r}"
                )
            if not (1 <= _db_port <= 65535):
                raise ValueError(
                    f"DATABASE_PORT must be between 1 and 65535, got: {_db_port}"
                )
        else:
            _db_port = None

        self._config["database"] = {
            "name": os.getenv("DATABASE_NAME"),
            "user": os.getenv("DATABASE_USER"),
            "host": os.getenv("DATABASE_HOST"),
            "password": os.getenv("DATABASE_PASSWORD"),
            "port": _db_port,
        }

        # Email configuration
        _smtp_port_raw = os.getenv("EMAIL_SMTP_PORT") or "587"
        try:
            _smtp_port = int(_smtp_port_raw)
        except ValueError:
            raise ValueError(
                f"EMAIL_SMTP_PORT must be a valid integer, got: {_smtp_port_raw!r}"
            )
        if not (1 <= _smtp_port <= 65535):
            raise ValueError(
                f"EMAIL_SMTP_PORT must be between 1 and 65535, got: {_smtp_port}"
            )

        self._config["email"] = {
            "sendgrid_api_key": os.getenv("SENDGRID_API_KEY"),
            "from_email": os.getenv("EMAIL_FROM_EMAIL", "admin@laugh-track.com"),
            "from_name": os.getenv("EMAIL_FROM_NAME", "Laughtrack"),
            # SMTP configuration for native email sending
            "smtp_server": os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": _smtp_port,
            "smtp_username": os.getenv("EMAIL_SMTP_USERNAME"),
            "smtp_password": self._clean_password(os.getenv("EMAIL_SMTP_PASSWORD")),
            "smtp_use_tls": os.getenv("EMAIL_SMTP_USE_TLS", "true").lower() == "true",
            "smtp_use_ssl": os.getenv("EMAIL_SMTP_USE_SSL", "false").lower() == "true",
        }

        # Scraper configuration
        _request_timeout_raw = os.getenv("REQUEST_TIMEOUT") or "30"
        try:
            _request_timeout = int(_request_timeout_raw)
        except ValueError:
            raise ValueError(
                f"REQUEST_TIMEOUT must be a valid integer, got: {_request_timeout_raw!r}"
            )

        _max_retries_raw = os.getenv("MAX_RETRIES") or "3"
        try:
            _max_retries = int(_max_retries_raw)
        except ValueError:
            raise ValueError(
                f"MAX_RETRIES must be a valid integer, got: {_max_retries_raw!r}"
            )

        _rate_limit_raw = os.getenv("RATE_LIMIT") or "10"
        try:
            _rate_limit = float(_rate_limit_raw)
        except ValueError:
            raise ValueError(
                f"RATE_LIMIT must be a valid number, got: {_rate_limit_raw!r}"
            )

        self._config["scraper"] = {
            "max_workers": min(32, (os.cpu_count() or 4) + 4),
            "request_timeout": _request_timeout,
            "max_retries": _max_retries,
            "rate_limit": _rate_limit,  # Requests per second
        }

        # API configuration
        _seatengine_venue_scan_max_id_raw = os.getenv("SEATENGINE_VENUE_SCAN_MAX_ID") or "700"
        try:
            _seatengine_venue_scan_max_id = int(_seatengine_venue_scan_max_id_raw)
        except ValueError:
            raise ValueError(
                f"SEATENGINE_VENUE_SCAN_MAX_ID must be a valid integer, got: {_seatengine_venue_scan_max_id_raw!r}"
            )

        _seatengine_cb_threshold_raw = os.getenv("SEATENGINE_CB_THRESHOLD") or "10"
        try:
            _seatengine_cb_threshold = int(_seatengine_cb_threshold_raw)
        except ValueError:
            raise ValueError(
                f"SEATENGINE_CB_THRESHOLD must be a valid integer, got: {_seatengine_cb_threshold_raw!r}"
            )

        _seatengine_cb_cooldown_raw = os.getenv("SEATENGINE_CB_COOLDOWN") or "300"
        try:
            _seatengine_cb_cooldown = int(_seatengine_cb_cooldown_raw)
        except ValueError:
            raise ValueError(
                f"SEATENGINE_CB_COOLDOWN must be a valid integer, got: {_seatengine_cb_cooldown_raw!r}"
            )

        self._config["api"] = {
            "eventbrite_token": os.getenv("EVENTBRITE_PRIVATE_TOKEN"),
            "ticketmaster_api_key": os.getenv("TICKETMASTER_API_KEY"),
            "seatengine_auth_token": os.getenv("SEATENGINE_AUTH_TOKEN", "your-seatengine-auth-token"),
            "seatengine_venue_scan_max_id": _seatengine_venue_scan_max_id,
            "seatengine_cb_threshold": _seatengine_cb_threshold,
            "seatengine_cb_cooldown": _seatengine_cb_cooldown,
            "songkick_api_key": os.getenv("SONGKICK_API_KEY"),
            "bandsintown_app_id": os.getenv("BANDSINTOWN_APP_ID"),
        }

        # Monitoring configuration
        self._config["monitoring"] = {
            "alert_recipients": os.getenv("ALERT_RECIPIENTS", "").split(",") if os.getenv("ALERT_RECIPIENTS") else [],
            "failure_rate_warning_threshold": float(os.getenv("FAILURE_RATE_WARNING_THRESHOLD", "25.0")),
            "failure_rate_critical_threshold": float(os.getenv("FAILURE_RATE_CRITICAL_THRESHOLD", "50.0")),
            "enable_background_monitoring": os.getenv("ENABLE_BACKGROUND_MONITORING", "true").lower()
            in ("true", "1", "yes", "on"),
            "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL"),
            "monitoring_webhook_url": os.getenv("MONITORING_WEBHOOK_URL"),
        }

        self._loaded = True
        Logger.info("Configuration loaded successfully")

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            section: Configuration section (e.g., 'database', 'email')
            key: Configuration key
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        if section not in self._config:
            return default
        return self._config[section].get(key, default)

    def get_section(self, section: str) -> JSONDict:
        """
        Get an entire configuration section.

        Args:
            section: Configuration section

        Returns:
            Dictionary of configuration values in the section
        """
        return self._config.get(section, {})

    def get_database_config(self) -> JSONDict:
        """Get database configuration."""
        return self.get_section("database")

    def get_email_config(self) -> JSONDict:
        """Get email configuration."""
        return self.get_section("email")

    def get_scraper_config(self) -> JSONDict:
        """Get scraper configuration."""
        return self.get_section("scraper")

    def get_api_config(self) -> JSONDict:
        """Get API configuration."""
        return self.get_section("api")

    def get_monitoring_config(self) -> JSONDict:
        """Get monitoring configuration."""
        return self.get_section("monitoring")

    # Class methods for direct access without instantiation
    @classmethod
    def get_instance(cls) -> "ConfigManager":
        """Get the singleton instance."""
        return cls()

    @classmethod
    def get_config(cls, section: str, key: str, default: Any = None) -> Any:
        """Class method to get a configuration value without instantiation."""
        return cls().get(section, key, default)

    @classmethod
    def get_config_section(cls, section: str) -> JSONDict:
        """Class method to get an entire configuration section without instantiation."""
        return cls().get_section(section)

    @classmethod
    def get_database_configuration(cls) -> JSONDict:
        """Class method to get database configuration without instantiation."""
        return cls().get_database_config()

    @classmethod
    def get_email_configuration(cls) -> JSONDict:
        """Class method to get email configuration without instantiation."""
        return cls().get_email_config()

    @classmethod
    def get_scraper_configuration(cls) -> JSONDict:
        """Class method to get scraper configuration without instantiation."""
        return cls().get_scraper_config()

    @classmethod
    def get_api_configuration(cls) -> JSONDict:
        """Class method to get API configuration without instantiation."""
        return cls().get_api_config()

    @classmethod
    def get_monitoring_configuration(cls) -> JSONDict:
        """Class method to get monitoring configuration without instantiation."""
        return cls().get_monitoring_config()
