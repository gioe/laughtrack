"""OrganizerVenueHandler — per-organizer Eventbrite venue history (TASK-2859).

Verifies the handler reads/writes the eventbrite_organizer_venues history and
answers the cross-organizer safety questions the dropped-venue reconciler needs.
"""
from unittest.mock import MagicMock

from laughtrack.core.entities.organizer_venue.handler import OrganizerVenueHandler
from sql.organizer_venue_queries import OrganizerVenueQueries


def _handler():
    h = OrganizerVenueHandler.__new__(OrganizerVenueHandler)
    h.execute_with_cursor = MagicMock()
    return h


def test_get_venue_club_ids_returns_club_ids():
    h = _handler()
    h.execute_with_cursor.return_value = [{"club_id": 101}, {"club_id": 202}]

    result = h.get_venue_club_ids(55)

    h.execute_with_cursor.assert_called_once_with(
        OrganizerVenueQueries.GET_VENUE_CLUB_IDS, (55,), return_results=True
    )
    assert result == [101, 202]


def test_get_venue_club_ids_empty_when_no_rows():
    h = _handler()
    h.execute_with_cursor.return_value = None
    assert h.get_venue_club_ids(55) == []


def test_forget_venue_issues_scoped_delete():
    h = _handler()
    h.forget_venue(55, 303)
    h.execute_with_cursor.assert_called_once_with(
        OrganizerVenueQueries.DELETE_VENUE, (55, 303)
    )


def test_covered_when_another_organizer_claims_the_venue():
    h = _handler()
    # First lookup (other organizer) returns a row → covered, second never runs.
    h.execute_with_cursor.return_value = [{"?column?": 1}]

    assert h.is_venue_covered_elsewhere(55, 303) is True
    h.execute_with_cursor.assert_called_once_with(
        OrganizerVenueQueries.COVERED_BY_OTHER_ORGANIZER, (303, 55), return_results=True
    )


def test_covered_when_direct_eventbrite_source_exists():
    h = _handler()
    # No other organizer, but the venue has its own enabled eventbrite source.
    h.execute_with_cursor.side_effect = [[], [{"?column?": 1}]]

    assert h.is_venue_covered_elsewhere(55, 303) is True
    assert h.execute_with_cursor.call_args_list[1].args[0] == (
        OrganizerVenueQueries.HAS_DIRECT_EVENTBRITE_SOURCE
    )
    assert h.execute_with_cursor.call_args_list[1].args[1] == (303,)


def test_not_covered_when_neither_sibling_source_exists():
    h = _handler()
    h.execute_with_cursor.side_effect = [[], []]
    assert h.is_venue_covered_elsewhere(55, 303) is False


def test_record_venues_noop_on_empty():
    h = _handler()
    h.transaction = MagicMock()
    h.record_venues(55, [])
    h.transaction.assert_not_called()


def test_coverage_query_excludes_same_organizer():
    """The other-organizer probe must exclude this organizer's own row, or every
    venue would look covered by itself."""
    sql = OrganizerVenueQueries.COVERED_BY_OTHER_ORGANIZER
    assert "club_id = %s" in sql
    assert "production_company_id <> %s" in sql


def test_direct_source_query_scoped_to_enabled_eventbrite():
    sql = OrganizerVenueQueries.HAS_DIRECT_EVENTBRITE_SOURCE
    assert "scraping_sources" in sql
    assert "club_id = %s" in sql
    assert "platform = 'eventbrite'" in sql
    assert "enabled = TRUE" in sql
