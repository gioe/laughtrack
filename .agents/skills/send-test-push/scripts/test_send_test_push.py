from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from send_test_push import find_target, run


class CursorContext:
    def __init__(self, row):
        self.cursor = MagicMock()
        self.cursor.fetchone.return_value = row

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc_type, exc, traceback):
        return False


class Connection:
    def __init__(self, row):
        self.cursor_context = CursorContext(row)

    def cursor(self):
        return self.cursor_context


class ConnectionContext:
    def __init__(self, row):
        self.connection = Connection(row)

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_find_target_uses_parameterized_email_query():
    connection = Connection(("user-1", "User@Example.com", "token-1", "secret", None))

    target = find_target(connection, email="user@example.com", user_id=None)

    assert target is not None
    assert target.token_id == "token-1"
    query, params = connection.cursor_context.cursor.execute.call_args.args
    assert "lower(u.email) = lower(%s)" in query
    assert "ORDER BY last_registered_at DESC, created_at DESC" in query
    assert params == ("user@example.com",)


def test_run_exits_without_service_when_user_has_no_active_token(capsys):
    service_factory = MagicMock()

    exit_code = run(
        ["--user-id", "user-1"],
        connection_factory=lambda: ConnectionContext(("user-1", "user@example.com", None, None, None)),
        service_factory=service_factory,
    )

    assert exit_code == 0
    assert "No active iOS push token" in capsys.readouterr().out
    service_factory.assert_not_called()


def test_run_sends_through_apns_service_without_printing_raw_token(capsys):
    registered_at = datetime(2026, 7, 31, 21, 34, tzinfo=timezone.utc)
    service = MagicMock()
    service.send_test_notification.return_value = MagicMock(
        success=True,
        status_code=200,
        reason=None,
    )

    exit_code = run(
        ["--email", "user@example.com", "--title", "Title", "--body", "Body"],
        connection_factory=lambda: ConnectionContext(
            ("user-1", "user@example.com", "token-1", "raw-device-token", registered_at)
        ),
        service_factory=lambda: service,
    )

    assert exit_code == 0
    service.send_test_notification.assert_called_once_with(
        device_token="raw-device-token",
        title="Title",
        body="Body",
    )
    output = capsys.readouterr().out
    assert "token_id=token-1" in output
    assert "status_code=200" in output
    assert "raw-device-token" not in output


def test_run_reports_unknown_user_without_loading_service(capsys):
    service_factory = MagicMock()

    exit_code = run(
        ["--email", "missing@example.com"],
        connection_factory=lambda: ConnectionContext(None),
        service_factory=service_factory,
    )

    assert exit_code == 2
    assert "User not found" in capsys.readouterr().err
    service_factory.assert_not_called()


@pytest.mark.parametrize("status_code, expected", [(200, 0), (410, 1)])
def test_run_returns_delivery_status(status_code, expected):
    service = MagicMock()
    service.send_test_notification.return_value = MagicMock(
        success=status_code == 200,
        status_code=status_code,
        reason=None if status_code == 200 else "Unregistered",
    )

    exit_code = run(
        ["--user-id", "user-1"],
        connection_factory=lambda: ConnectionContext(
            ("user-1", "user@example.com", "token-1", "raw-device-token", None)
        ),
        service_factory=lambda: service,
    )

    assert exit_code == expected
