from datetime import datetime
from unittest.mock import MagicMock

from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.core.entities.show.model import Show
from sql.show_queries import ShowQueries


def _handler():
    h = ShowHandler.__new__(ShowHandler)
    h.ticket_handler = MagicMock()
    h.tag_handler = MagicMock()
    h.lineup_handler = MagicMock()
    h.comedian_handler = MagicMock()
    h.execute_batch_operation = MagicMock(
        return_value=[
            {
                "id": 10,
                "club_id": 1,
                "date": datetime(2026, 6, 1, 20, 0, 0),
                "room": "",
                "operation_type": "updated",
            }
        ]
    )
    h.ticket_handler.insert_tickets.return_value = None
    h.tag_handler.process_show_tags.return_value = None
    h.update_show_lineups = MagicMock(return_value=(0, 0))
    return h


def _show(name="Same Show", room="", url="https://example.com/show", date=datetime(2026, 6, 1, 20, 0, 0)):
    return Show(
        name=name,
        club_id=1,
        date=date,
        show_page_url=url,
        room=room,
    )


def test_insert_shows_dedups_cross_batch():
    h = _handler()
    h.execute_with_cursor = MagicMock(
        return_value=[
            {
                "id": 10,
                "club_id": 1,
                "date": datetime(2026, 6, 1, 20, 0, 0),
                "room": "",
                "name": "Same Show",
            }
        ]
    )

    result = h._process_single_batch([_show(room="Main Room")])

    inserted_items = h.execute_batch_operation.call_args.args[1]
    assert len(inserted_items) == 1
    assert inserted_items[0][6] == ""
    assert result.updates == 1


def test_insert_shows_dedups_cross_batch_when_existing_room_is_null():
    h = _handler()
    h.execute_with_cursor = MagicMock(
        return_value=[
            {
                "id": 10,
                "club_id": 1,
                "date": datetime(2026, 6, 1, 20, 0, 0),
                "room": None,
                "name": "Same Show",
            }
        ]
    )

    h._process_single_batch([_show(room="")])

    inserted_items = h.execute_batch_operation.call_args.args[1]
    assert len(inserted_items) == 1
    assert inserted_items[0][6] is None


def test_insert_shows_preserves_distinct_rooms():
    h = _handler()
    h.execute_with_cursor = MagicMock(
        return_value=[
            {
                "id": 10,
                "club_id": 1,
                "date": datetime(2026, 6, 1, 20, 0, 0),
                "room": "Main Room",
                "name": "Same Show",
            }
        ]
    )

    h._process_single_batch([_show(room="Side Room")])

    inserted_items = h.execute_batch_operation.call_args.args[1]
    assert len(inserted_items) == 1
    assert inserted_items[0][6] == "Side Room"


# --- PatronTicket instance-id reconciliation (TASK-2494) -------------------

_PT_URL = "https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000004XeKY2A0"
_OLD_DATE = datetime(2026, 7, 11, 20, 0, 0)   # original start time
_NEW_DATE = datetime(2026, 7, 11, 20, 30, 0)  # rescheduled 30 min later


def _pt_handler(existing_rows):
    """Handler whose execute_with_cursor routes by query identity.

    Returns ``existing_rows`` for the PatronTicket lookup and records every call so
    tests can assert whether the in-place date move (UPDATE_SHOW_DATE_BY_ID) fired.
    """
    h = _handler()

    def fake_exec(query, params=None, return_results=False):
        if query is ShowQueries.GET_PATRONTICKET_SHOWS_BY_CLUB:
            return list(existing_rows)
        return []

    h.execute_with_cursor = MagicMock(side_effect=fake_exec)
    return h


def _update_calls(h):
    return [
        c for c in h.execute_with_cursor.call_args_list
        if c.args and c.args[0] is ShowQueries.UPDATE_SHOW_DATE_BY_ID
    ]


def test_patronticket_reschedule_moves_existing_row_in_place():
    """A start-time change for one instance id moves the existing row, so one row remains."""
    existing = {
        "id": 481928,
        "club_id": 1,
        "date": _OLD_DATE,
        "room": "",
        "show_page_url": _PT_URL,
    }
    h = _pt_handler([existing])

    h._process_single_batch([_show(date=_NEW_DATE, url=_PT_URL)])

    update_calls = _update_calls(h)
    assert len(update_calls) == 1
    # Guarded UPDATE params are (new_date, existing_id, new_date): the existing row
    # is moved to the rescheduled date in place rather than a duplicate being inserted.
    assert update_calls[0].args[1] == (_NEW_DATE, 481928, _NEW_DATE)


def test_patronticket_no_move_when_existing_row_already_at_incoming_date():
    """Re-scraping an unchanged instance does not issue a redundant date move."""
    existing = {
        "id": 481928,
        "club_id": 1,
        "date": _NEW_DATE,
        "room": "",
        "show_page_url": _PT_URL,
    }
    h = _pt_handler([existing])

    h._process_single_batch([_show(date=_NEW_DATE, url=_PT_URL)])

    assert _update_calls(h) == []


def test_non_patronticket_show_never_reconciles_by_instance_id():
    """Shows without a #/instances/ fragment skip instance reconciliation entirely."""
    h = _pt_handler([])

    h._process_single_batch([_show(url="https://example.com/show")])

    # No PatronTicket lookup and no date move for non-instance URLs.
    pt_lookups = [
        c for c in h.execute_with_cursor.call_args_list
        if c.args and c.args[0] is ShowQueries.GET_PATRONTICKET_SHOWS_BY_CLUB
    ]
    assert pt_lookups == []
    assert _update_calls(h) == []
