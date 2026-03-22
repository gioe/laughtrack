"""
Unit tests for create_connection() retry logic.

Verifies that transient OperationalErrors (e.g. Neon auto-suspend wakeup) are
retried with backoff, and that non-retryable errors are raised immediately.
"""

from unittest.mock import MagicMock, call, patch

import psycopg2
import pytest

from laughtrack.infrastructure.database.connection import (
    _CONNECT_RETRY_DELAYS,
    create_connection,
)

_VALID_DB_CONFIG = {
    "name": "testdb",
    "user": "user",
    "host": "host",
    "password": "pw",
    "port": 5432,
}


def _patch_config(config=_VALID_DB_CONFIG):
    return patch(
        "laughtrack.infrastructure.database.connection.ConfigManager.get_database_configuration",
        return_value=config,
    )


def _patch_sleep():
    return patch("laughtrack.infrastructure.database.connection.time.sleep")


class TestCreateConnectionRetry:
    def test_succeeds_on_first_attempt(self):
        mock_conn = MagicMock()
        with _patch_config(), _patch_sleep() as mock_sleep, patch("psycopg2.connect", return_value=mock_conn):
            conn = create_connection()

        assert conn is mock_conn
        mock_sleep.assert_not_called()

    def test_retries_on_operational_error_then_succeeds(self):
        mock_conn = MagicMock()
        side_effects = [psycopg2.OperationalError("server closed"), mock_conn]

        with _patch_config(), _patch_sleep() as mock_sleep, patch("psycopg2.connect", side_effect=side_effects):
            conn = create_connection()

        assert conn is mock_conn
        mock_sleep.assert_called_once_with(_CONNECT_RETRY_DELAYS[0])

    def test_retries_all_delays_then_raises(self):
        err = psycopg2.OperationalError("connection refused")
        attempts = len(_CONNECT_RETRY_DELAYS) + 1  # 1 initial + N retries

        with _patch_config(), _patch_sleep() as mock_sleep, patch(
            "psycopg2.connect", side_effect=[err] * attempts
        ):
            with pytest.raises(psycopg2.OperationalError):
                create_connection()

        assert mock_sleep.call_args_list == [call(d) for d in _CONNECT_RETRY_DELAYS]

    def test_non_operational_error_not_retried(self):
        """ProgrammingError and other non-transient errors should propagate immediately."""
        err = psycopg2.ProgrammingError("bad SQL")

        with _patch_config(), _patch_sleep() as mock_sleep, patch("psycopg2.connect", side_effect=err):
            with pytest.raises(psycopg2.ProgrammingError):
                create_connection()

        mock_sleep.assert_not_called()

    def test_incomplete_config_raises_value_error_without_retry(self):
        incomplete = {"name": "db", "user": "u", "host": "h"}  # missing password, port

        with _patch_config(incomplete), _patch_sleep() as mock_sleep:
            with pytest.raises(ValueError, match="incomplete"):
                create_connection()

        mock_sleep.assert_not_called()

    def test_non_operational_psycopg2_error_not_retried(self):
        """InterfaceError and other non-OperationalError psycopg2.Error subclasses propagate immediately."""
        err = psycopg2.InterfaceError("connection already closed")

        with _patch_config(), _patch_sleep() as mock_sleep, patch("psycopg2.connect", side_effect=err):
            with pytest.raises(psycopg2.InterfaceError):
                create_connection()

        mock_sleep.assert_not_called()

    def test_autocommit_set_on_connection(self):
        mock_conn = MagicMock()
        with _patch_config(), _patch_sleep(), patch("psycopg2.connect", return_value=mock_conn):
            create_connection(autocommit=True)

        assert mock_conn.autocommit is True

    def test_autocommit_false_not_set(self):
        mock_conn = MagicMock()
        mock_conn.autocommit = False
        with _patch_config(), _patch_sleep(), patch("psycopg2.connect", return_value=mock_conn):
            create_connection(autocommit=False)

        assert mock_conn.autocommit is False
