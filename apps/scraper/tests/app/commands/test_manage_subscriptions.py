"""Tests for manage_subscriptions CLI."""

import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, call, patch

import pytest

from laughtrack.app.commands.manage_subscriptions import (
    build_parser,
    cmd_add,
    cmd_list,
    main,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(fetchall=None, fetchone=None):
    """Return a mock connection context manager whose cursor returns given rows."""
    cur = MagicMock()
    cur.fetchall.return_value = fetchall if fetchall is not None else []
    cur.fetchone.return_value = fetchone

    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    @contextmanager
    def _ctx(*args, **kwargs):
        yield conn

    return _ctx, cur


# ---------------------------------------------------------------------------
# cmd_list
# ---------------------------------------------------------------------------

class TestCmdList:
    def test_prints_all_subscribed_message_when_no_rows(self, capsys):
        ctx, _ = _make_conn(fetchall=[])
        with patch("laughtrack.app.commands.manage_subscriptions.db") as mock_db:
            mock_db.get_connection = ctx
            cmd_list()

        out = capsys.readouterr().out
        assert "All clubs have an active email subscription." in out

    def test_prints_table_when_clubs_missing_subscription(self, capsys):
        ctx, _ = _make_conn(fetchall=[(1, "Comedy Cellar"), (2, "Gotham Comedy Club")])
        with patch("laughtrack.app.commands.manage_subscriptions.db") as mock_db:
            mock_db.get_connection = ctx
            cmd_list()

        out = capsys.readouterr().out
        assert "Comedy Cellar" in out
        assert "Gotham Comedy Club" in out
        assert "ID" in out


# ---------------------------------------------------------------------------
# cmd_add
# ---------------------------------------------------------------------------

class TestCmdAdd:
    def test_upserts_row_and_prints_confirmation(self, capsys):
        ctx, cur = _make_conn(fetchone=("Comedy Cellar",))
        with patch("laughtrack.app.commands.manage_subscriptions.db") as mock_db:
            mock_db.get_connection = ctx
            cmd_add(1, "comedycellar.com")

        out = capsys.readouterr().out
        assert "Subscription saved" in out
        assert "comedycellar.com" in out
        # Ensure both SELECT and INSERT were executed
        assert cur.execute.call_count == 2

    def test_invalid_club_id_exits_with_code_1(self, capsys):
        ctx, _ = _make_conn(fetchone=None)
        with patch("laughtrack.app.commands.manage_subscriptions.db") as mock_db:
            mock_db.get_connection = ctx
            with pytest.raises(SystemExit) as exc:
                cmd_add(999, "example.com")
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "999" in err

    def test_invalid_sender_domain_exits_before_db_call(self, capsys):
        with patch("laughtrack.app.commands.manage_subscriptions.db") as mock_db:
            with pytest.raises(SystemExit) as exc:
                cmd_add(1, "nodot")
        assert exc.value.code == 1
        mock_db.get_connection.assert_not_called()

    def test_empty_sender_domain_exits(self, capsys):
        with patch("laughtrack.app.commands.manage_subscriptions.db"):
            with pytest.raises(SystemExit) as exc:
                cmd_add(1, "")
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_list_subcommand_parsed(self):
        parser = build_parser()
        args = parser.parse_args(["list"])
        assert args.subcommand == "list"

    def test_add_subcommand_parsed(self):
        parser = build_parser()
        args = parser.parse_args(["add", "42", "example.com"])
        assert args.subcommand == "add"
        assert args.club_id == 42
        assert args.sender_domain == "example.com"

    def test_missing_subcommand_exits(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_add_requires_two_positional_args(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["add", "42"])

    def test_club_id_must_be_int(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["add", "notanint", "example.com"])


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_dispatches_list(self):
        with patch("laughtrack.app.commands.manage_subscriptions.cmd_list") as mock_list:
            main(["list"])
        mock_list.assert_called_once()

    def test_main_dispatches_add(self):
        with patch("laughtrack.app.commands.manage_subscriptions.cmd_add") as mock_add:
            main(["add", "7", "foo.com"])
        mock_add.assert_called_once_with(7, "foo.com")
