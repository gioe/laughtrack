"""
Unit tests for ConfigManager DATABASE_PORT startup validation.

Verifies that a non-numeric DATABASE_PORT raises a clear ValueError at
config load time rather than propagating a cryptic error from psycopg2.
"""

import importlib
import os
import sys
from unittest.mock import patch

import pytest


def _reset_config_manager():
    """Reset the ConfigManager singleton so each test gets a fresh load."""
    # Remove cached module so reimport re-executes module-level code
    for key in list(sys.modules.keys()):
        if "laughtrack.infrastructure.config.config_manager" in key:
            del sys.modules[key]


def _import_config_manager():
    """Import ConfigManager fresh (after singleton reset)."""
    _reset_config_manager()
    from laughtrack.infrastructure.config.config_manager import ConfigManager  # noqa: PLC0415

    # Reset singleton state so _load_config runs again
    ConfigManager._instance = None
    ConfigManager._loaded = False
    ConfigManager._config = {}
    return ConfigManager


class TestDatabasePortValidation:
    def test_valid_numeric_port_is_stored_as_int(self):
        ConfigManager = _import_config_manager()
        env = {
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "db",
            "DATABASE_USER": "user",
            "DATABASE_HOST": "localhost",
            "DATABASE_PASSWORD": "secret",
        }
        with patch.dict("os.environ", env, clear=False):
            cfg = ConfigManager()
            assert cfg.get_database_config()["port"] == 5432
            assert isinstance(cfg.get_database_config()["port"], int)

    def test_non_numeric_port_raises_value_error(self):
        ConfigManager = _import_config_manager()
        env = {"DATABASE_PORT": "not_a_number"}
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError, match="DATABASE_PORT must be a valid integer"):
                ConfigManager()

    def test_alphabetic_port_raises_value_error(self):
        ConfigManager = _import_config_manager()
        env = {"DATABASE_PORT": "abc"}
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError, match="DATABASE_PORT must be a valid integer"):
                ConfigManager()

    def test_missing_port_is_stored_as_none(self):
        ConfigManager = _import_config_manager()
        # Patch load_dotenv to prevent .env from re-injecting DATABASE_PORT,
        # then clear it from the environment entirely.
        with patch("laughtrack.infrastructure.config.config_manager.load_dotenv"):
            env_without_port = {k: v for k, v in os.environ.items() if k != "DATABASE_PORT"}
            with patch.dict("os.environ", env_without_port, clear=True):
                cfg = ConfigManager()
                assert cfg.get_database_config()["port"] is None

    def test_float_string_port_raises_value_error(self):
        ConfigManager = _import_config_manager()
        env = {"DATABASE_PORT": "54.32"}
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError, match="DATABASE_PORT must be a valid integer"):
                ConfigManager()

    def test_port_zero_raises_value_error(self):
        ConfigManager = _import_config_manager()
        env = {"DATABASE_PORT": "0"}
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError, match="DATABASE_PORT must be between 1 and 65535"):
                ConfigManager()

    def test_port_above_max_raises_value_error(self):
        ConfigManager = _import_config_manager()
        env = {"DATABASE_PORT": "99999"}
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError, match="DATABASE_PORT must be between 1 and 65535"):
                ConfigManager()

    def test_negative_port_raises_value_error(self):
        ConfigManager = _import_config_manager()
        env = {"DATABASE_PORT": "-1"}
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError, match="DATABASE_PORT must be between 1 and 65535"):
                ConfigManager()
