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


def test_record_venues_noop_on_empty():
    h = _handler()
    h.transaction = MagicMock()
    h.record_venues(55, [])
    h.transaction.assert_not_called()


def test_coverage_probes_removed_in_task_2861():
    """The TASK-2859 conservative-skip coverage probes were superseded by per-show
    organizer attribution (TASK-2861); they must no longer exist on the handler or
    the queries class."""
    assert not hasattr(OrganizerVenueHandler, "is_venue_covered_elsewhere")
    assert not hasattr(OrganizerVenueQueries, "COVERED_BY_OTHER_ORGANIZER")
    assert not hasattr(OrganizerVenueQueries, "HAS_DIRECT_EVENTBRITE_SOURCE")
