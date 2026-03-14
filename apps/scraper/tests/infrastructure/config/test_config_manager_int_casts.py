"""
Unit tests for ConfigManager int/float cast validation.

Verifies that EMAIL_SMTP_PORT, REQUEST_TIMEOUT, MAX_RETRIES, and RATE_LIMIT
raise clear ValueErrors when set to non-numeric strings.
"""

import sys
from unittest.mock import patch

import pytest


def _import_config_manager():
    """Import ConfigManager fresh (after singleton reset)."""
    for key in list(sys.modules.keys()):
        if "laughtrack.infrastructure.config.config_manager" in key:
            del sys.modules[key]
    from laughtrack.infrastructure.config.config_manager import ConfigManager  # noqa: PLC0415

    ConfigManager._instance = None
    ConfigManager._loaded = False
    ConfigManager._config = {}
    return ConfigManager


class TestSmtpPortValidation:
    def test_non_numeric_smtp_port_raises(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"EMAIL_SMTP_PORT": "not_a_port"}, clear=False):
            with pytest.raises(ValueError, match="EMAIL_SMTP_PORT must be a valid integer"):
                ConfigManager()

    def test_float_string_smtp_port_raises(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"EMAIL_SMTP_PORT": "58.7"}, clear=False):
            with pytest.raises(ValueError, match="EMAIL_SMTP_PORT must be a valid integer"):
                ConfigManager()

    def test_smtp_port_zero_raises(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"EMAIL_SMTP_PORT": "0"}, clear=False):
            with pytest.raises(ValueError, match="EMAIL_SMTP_PORT must be between 1 and 65535"):
                ConfigManager()

    def test_smtp_port_above_max_raises(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"EMAIL_SMTP_PORT": "99999"}, clear=False):
            with pytest.raises(ValueError, match="EMAIL_SMTP_PORT must be between 1 and 65535"):
                ConfigManager()

    def test_valid_smtp_port_is_stored_as_int(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"EMAIL_SMTP_PORT": "587"}, clear=False):
            cfg = ConfigManager()
            assert cfg.get_email_config()["smtp_port"] == 587
            assert isinstance(cfg.get_email_config()["smtp_port"], int)


class TestRequestTimeoutValidation:
    def test_non_numeric_request_timeout_raises(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"REQUEST_TIMEOUT": "fast"}, clear=False):
            with pytest.raises(ValueError, match="REQUEST_TIMEOUT must be a valid integer"):
                ConfigManager()

    def test_float_string_request_timeout_raises(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"REQUEST_TIMEOUT": "30.5"}, clear=False):
            with pytest.raises(ValueError, match="REQUEST_TIMEOUT must be a valid integer"):
                ConfigManager()

    def test_valid_request_timeout_is_stored_as_int(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"REQUEST_TIMEOUT": "60"}, clear=False):
            cfg = ConfigManager()
            assert cfg.get_scraper_config()["request_timeout"] == 60
            assert isinstance(cfg.get_scraper_config()["request_timeout"], int)


class TestMaxRetriesValidation:
    def test_non_numeric_max_retries_raises(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"MAX_RETRIES": "many"}, clear=False):
            with pytest.raises(ValueError, match="MAX_RETRIES must be a valid integer"):
                ConfigManager()

    def test_float_string_max_retries_raises(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"MAX_RETRIES": "3.5"}, clear=False):
            with pytest.raises(ValueError, match="MAX_RETRIES must be a valid integer"):
                ConfigManager()

    def test_valid_max_retries_is_stored_as_int(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"MAX_RETRIES": "5"}, clear=False):
            cfg = ConfigManager()
            assert cfg.get_scraper_config()["max_retries"] == 5
            assert isinstance(cfg.get_scraper_config()["max_retries"], int)


class TestRateLimitValidation:
    def test_non_numeric_rate_limit_raises(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"RATE_LIMIT": "high"}, clear=False):
            with pytest.raises(ValueError, match="RATE_LIMIT must be a valid number"):
                ConfigManager()

    def test_alphabetic_rate_limit_raises(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"RATE_LIMIT": "abc"}, clear=False):
            with pytest.raises(ValueError, match="RATE_LIMIT must be a valid number"):
                ConfigManager()

    def test_valid_int_rate_limit_is_stored_as_float(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"RATE_LIMIT": "10"}, clear=False):
            cfg = ConfigManager()
            assert cfg.get_scraper_config()["rate_limit"] == 10.0
            assert isinstance(cfg.get_scraper_config()["rate_limit"], float)

    def test_valid_float_rate_limit_is_stored(self):
        ConfigManager = _import_config_manager()
        with patch.dict("os.environ", {"RATE_LIMIT": "2.5"}, clear=False):
            cfg = ConfigManager()
            assert cfg.get_scraper_config()["rate_limit"] == 2.5
