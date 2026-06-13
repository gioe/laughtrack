"""ShowHandler.delete_stale_future_shows — stale-future-show reconciliation (TASK-2847).

Verifies the handler issues the DELETE_STALE_FUTURE_SHOWS query with the
(club_id, scraper_key, cutoff) params and returns the deleted rows for logging.
The SQL itself scopes to future + last_scraped_by + last_scraped_date < cutoff.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from laughtrack.core.entities.show.handler import ShowHandler
from sql.show_queries import ShowQueries


def _handler():
    h = ShowHandler.__new__(ShowHandler)
    h.execute_with_cursor = MagicMock()
    return h


def test_issues_delete_query_with_scoped_params():
    h = _handler()
    deleted_rows = [
        {"id": 1532633, "name": "Standup Comedy", "date": datetime(2026, 7, 24), "room": ""},
    ]
    h.execute_with_cursor.return_value = deleted_rows
    cutoff = datetime(2026, 6, 13, 9, 0, 0, tzinfo=timezone.utc)

    result = h.delete_stale_future_shows(2301, "eventbrite", cutoff)

    h.execute_with_cursor.assert_called_once_with(
        ShowQueries.DELETE_STALE_FUTURE_SHOWS,
        (2301, "eventbrite", cutoff),
        return_results=True,
    )
    assert result == deleted_rows


def test_returns_empty_list_when_nothing_stale():
    h = _handler()
    h.execute_with_cursor.return_value = None  # cursor.fetchall() can be falsy

    result = h.delete_stale_future_shows(1, "json_ld", datetime.now(timezone.utc))

    assert result == []


def test_query_is_scoped_to_future_and_scraper_and_cutoff():
    """Guard the SQL predicate so a refactor can't silently widen the delete."""
    sql = ShowQueries.DELETE_STALE_FUTURE_SHOWS
    assert "DELETE FROM shows" in sql
    assert "club_id = %s" in sql
    assert "last_scraped_by = %s" in sql
    assert "date > NOW()" in sql
    assert "last_scraped_date < %s" in sql
    assert "RETURNING" in sql
