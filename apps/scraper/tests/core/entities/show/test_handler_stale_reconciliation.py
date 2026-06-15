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


def test_count_uses_same_predicate_as_delete():
    """The cap count must share the delete's predicate or the cap guards nothing."""
    count_sql = ShowQueries.COUNT_STALE_FUTURE_SHOWS
    assert "SELECT COUNT(*)" in count_sql
    for clause in ("club_id = %s", "last_scraped_by = %s", "date > NOW()", "last_scraped_date < %s"):
        assert clause in count_sql


def test_count_stale_future_shows_returns_int():
    h = _handler()
    h.execute_with_cursor.return_value = [{"stale_count": 3}]
    cutoff = datetime(2026, 6, 13, 9, 0, 0, tzinfo=timezone.utc)

    n = h.count_stale_future_shows(2301, "eventbrite", cutoff)

    h.execute_with_cursor.assert_called_once_with(
        ShowQueries.COUNT_STALE_FUTURE_SHOWS,
        (2301, "eventbrite", cutoff),
        return_results=True,
    )
    assert n == 3


def test_count_stale_future_shows_handles_empty_result():
    h = _handler()
    h.execute_with_cursor.return_value = None
    assert h.count_stale_future_shows(1, "json_ld", datetime.now(timezone.utc)) == 0


# --- TASK-2861: organizer-attributed reconcile variants ---


def test_delete_by_organizer_issues_query_with_organizer_scoped_params():
    h = _handler()
    deleted_rows = [{"id": 9, "name": "Dropped", "date": datetime(2026, 8, 1), "room": ""}]
    h.execute_with_cursor.return_value = deleted_rows
    cutoff = datetime(2026, 6, 13, 9, 0, 0, tzinfo=timezone.utc)

    result = h.delete_stale_future_shows_by_organizer(2301, 55, cutoff)

    h.execute_with_cursor.assert_called_once_with(
        ShowQueries.DELETE_STALE_FUTURE_SHOWS_BY_ORGANIZER,
        (2301, 55, cutoff),
        return_results=True,
    )
    assert result == deleted_rows


def test_count_by_organizer_returns_int():
    h = _handler()
    h.execute_with_cursor.return_value = [{"stale_count": 4}]
    cutoff = datetime(2026, 6, 13, 9, 0, 0, tzinfo=timezone.utc)

    n = h.count_stale_future_shows_by_organizer(2301, 55, cutoff)

    h.execute_with_cursor.assert_called_once_with(
        ShowQueries.COUNT_STALE_FUTURE_SHOWS_BY_ORGANIZER,
        (2301, 55, cutoff),
        return_results=True,
    )
    assert n == 4


def test_by_organizer_query_scopes_to_organizer_not_scraper_key():
    """The organizer-attributed reconcile must scope by scraped_by_organizer_id,
    not last_scraped_by, or a sibling Eventbrite source's shows could be deleted."""
    for sql in (
        ShowQueries.DELETE_STALE_FUTURE_SHOWS_BY_ORGANIZER,
        ShowQueries.COUNT_STALE_FUTURE_SHOWS_BY_ORGANIZER,
    ):
        assert "scraped_by_organizer_id = %s" in sql
        assert "last_scraped_by" not in sql
        assert "club_id = %s" in sql
        assert "date > NOW()" in sql
        assert "last_scraped_date < %s" in sql


def test_batch_insert_stamps_and_overwrites_scraped_by_organizer_id():
    """The upsert must INSERT scraped_by_organizer_id and OVERWRITE it on conflict
    (EXCLUDED, not COALESCE) so the last producer's attribution always wins."""
    insert_cols = ShowQueries.BATCH_INSERT_SHOWS.split("VALUES", maxsplit=1)[0]
    assert "scraped_by_organizer_id" in insert_cols

    conflict_update = ShowQueries.BATCH_INSERT_SHOWS.split("DO UPDATE SET", maxsplit=1)[1].split(
        "RETURNING", maxsplit=1
    )[0]
    assert "scraped_by_organizer_id = EXCLUDED.scraped_by_organizer_id" in conflict_update
