"""Smoke tests for audit-show CLI command."""

import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from laughtrack.app.commands.audit_show import main
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SHOW_DATE = datetime(2026, 4, 1, 20, 0, 0, tzinfo=timezone.utc)

_BASE_SHOW_ROW = {
    "id": 42,
    "date": _SHOW_DATE,
    "room": "Main Stage",
    "name": "Tuesday Night Comedy",
    "club_id": 7,
    "club_name": "Test Comedy Club",
    "scraper": "test_scraper",
    "scraping_url": "https://example.com",
    "address": "123 Main St",
    "website": "https://example.com",
    "popularity": 50,
    "zip_code": "10001",
    "phone_number": "555-0000",
    "timezone": "America/New_York",
    "visible": True,
    "city": "New York",
    "state": "NY",
    "eventbrite_id": None,
    "ticketmaster_id": None,
    "seatengine_id": None,
    "status": "active",
    "rate_limit": 1.0,
    "max_retries": 3,
    "timeout": 30,
}


def _make_conn(show_row, lineup_names):
    """Return a mock db.get_connection() context manager."""
    cur = MagicMock()
    # fetchone for show query, then fetchall for lineup query
    cur.fetchone.return_value = show_row
    cur.fetchall.return_value = [(name,) for name in lineup_names]
    cur.description = [(col,) for col in show_row.keys()] if show_row else []

    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    @contextmanager
    def _ctx(*args, **kwargs):
        yield conn

    return _ctx


def _make_scraped_show(date=_SHOW_DATE, room="Main Stage", names=None):
    """Build a Show object with the given lineup names."""
    lineup = [Comedian(name=n) for n in (names or [])]
    return Show(
        name="Tuesday Night Comedy",
        club_id=7,
        date=date,
        show_page_url="https://example.com/show/42",
        lineup=lineup,
        room=room,
    )


def _make_scraper_result(shows, error=None):
    result = MagicMock()
    result.shows = shows
    result.error = error
    return result


def _patch_db_and_scraper(show_row, lineup_names, scraped_shows, scraper_error=None):
    """Return a context manager that patches both db and ScraperResolver."""
    @contextmanager
    def _combined():
        ctx = _make_conn(show_row, lineup_names)
        mock_scraper_cls = MagicMock()
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.scrape_with_result.return_value = _make_scraper_result(
            scraped_shows, scraper_error
        )
        mock_scraper_cls.return_value = mock_scraper_instance

        mock_resolver = MagicMock()
        mock_resolver.get.return_value = mock_scraper_cls

        with patch("laughtrack.app.commands.audit_show.db") as mock_db, \
             patch(
                "laughtrack.app.commands.audit_show.ScraperResolver",
                return_value=mock_resolver,
             ):
            mock_db.get_connection = ctx
            yield mock_db, mock_resolver

    return _combined()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuditShowDiffOutput:
    """Tests for the normal diff output path."""

    def test_db_only_names_shown(self, capsys):
        """Names in DB but not in live scrape are flagged for removal."""
        db_names = ["Alice", "Bob"]
        live_names = ["Alice"]
        scraped_show = _make_scraped_show(names=live_names)

        with _patch_db_and_scraper(_BASE_SHOW_ROW, db_names, [scraped_show]):
            main(["--show-id", "42"])

        out = capsys.readouterr().out
        assert "REMOVED" in out
        assert "Bob" in out

    def test_live_only_names_shown(self, capsys):
        """Names in live scrape but not in DB are flagged for addition."""
        db_names = ["Alice"]
        live_names = ["Alice", "Charlie"]
        scraped_show = _make_scraped_show(names=live_names)

        with _patch_db_and_scraper(_BASE_SHOW_ROW, db_names, [scraped_show]):
            main(["--show-id", "42"])

        out = capsys.readouterr().out
        assert "ADDED" in out
        assert "Charlie" in out

    def test_in_both_names_shown(self, capsys):
        """Names present in both DB and live scrape are listed in the 'in both' section."""
        names = ["Alice", "Bob"]
        scraped_show = _make_scraped_show(names=names)

        with _patch_db_and_scraper(_BASE_SHOW_ROW, names, [scraped_show]):
            main(["--show-id", "42"])

        out = capsys.readouterr().out
        assert "Alice" in out
        assert "Bob" in out

    def test_lineups_identical_prints_match_message(self, capsys):
        """When DB and live lineups are identical, a match message is printed."""
        names = ["Alice", "Bob"]
        scraped_show = _make_scraped_show(names=names)

        with _patch_db_and_scraper(_BASE_SHOW_ROW, names, [scraped_show]):
            main(["--show-id", "42"])

        out = capsys.readouterr().out
        assert "Lineups match" in out


class TestAuditShowErrorCases:
    """Tests for the error/exit paths."""

    def test_show_id_not_found_exits_1(self):
        """When the show is not found in the DB, sys.exit(1) is raised."""
        ctx = _make_conn(None, [])
        ctx_none = _make_conn_none()

        with patch("laughtrack.app.commands.audit_show.db") as mock_db:
            mock_db.get_connection = ctx_none
            with pytest.raises(SystemExit) as exc_info:
                main(["--show-id", "999"])

        assert exc_info.value.code == 1

    def test_club_missing_scraper_exits_1(self, capsys):
        """When the club has no scraper configured, sys.exit(1) is raised."""
        show_row = dict(_BASE_SHOW_ROW)
        show_row["scraper"] = None

        ctx = _make_conn(show_row, ["Alice"])
        with patch("laughtrack.app.commands.audit_show.db") as mock_db:
            mock_db.get_connection = ctx
            with pytest.raises(SystemExit) as exc_info:
                main(["--show-id", "42"])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "no scraper configured" in err

    def test_no_match_in_live_scrape_exits_1(self, capsys):
        """When no scraped show matches the target date/room, sys.exit(1) is raised."""
        # Scraped show has a different room
        scraped_show = _make_scraped_show(names=["Alice"], room="Different Room")

        with _patch_db_and_scraper(_BASE_SHOW_ROW, ["Alice"], [scraped_show]):
            with pytest.raises(SystemExit) as exc_info:
                main(["--show-id", "42"])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "No match found" in err


def _make_conn_none():
    """Return a mock db.get_connection() that returns None for fetchone."""
    cur = MagicMock()
    cur.fetchone.return_value = None
    cur.description = []

    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    @contextmanager
    def _ctx(*args, **kwargs):
        yield conn

    return _ctx
