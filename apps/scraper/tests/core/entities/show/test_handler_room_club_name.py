"""Room values that duplicate the club name are blanked at ingestion (TASK-2803).

Several scrapers (ticketmaster/live_nation, tixr PIXL) copy the venue name into
the room field, so shows.room repeats the club name instead of naming a room.
The handler suppresses those values before in-batch dedup and the upsert.
"""
from datetime import datetime
from unittest.mock import MagicMock

from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.core.entities.show.model import Show
from sql.show_queries import ShowQueries

_DATE = datetime(2026, 6, 1, 20, 0, 0)


def _handler(club_rows):
    """Handler whose execute_with_cursor routes by query identity.

    Returns ``club_rows`` for the club-name lookup and [] for every other
    query (cross-batch dedup, PatronTicket/SeatEngine reconciliation).
    """
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
                "date": _DATE,
                "room": "",
                "operation_type": "inserted",
            }
        ]
    )
    h.ticket_handler.insert_tickets.return_value = None
    h.tag_handler.process_show_tags.return_value = None
    h.update_show_lineups = MagicMock(return_value=(0, 0))

    def fake_exec(query, params=None, return_results=False):
        if query is ShowQueries.GET_CLUB_NAMES_BY_IDS:
            return list(club_rows)
        return []

    h.execute_with_cursor = MagicMock(side_effect=fake_exec)
    return h


def _show(club_id=1, room="", name="Some Show", url="https://example.com/show", date=_DATE):
    return Show(
        name=name,
        club_id=club_id,
        date=date,
        show_page_url=url,
        room=room,
    )


def _club_name_calls(h):
    return [
        c for c in h.execute_with_cursor.call_args_list
        if c.args and c.args[0] is ShowQueries.GET_CLUB_NAMES_BY_IDS
    ]


def _inserted_rooms(h):
    return [item[6] for item in h.execute_batch_operation.call_args.args[1]]


def test_room_equal_to_club_name_is_blanked():
    h = _handler([{"id": 1, "name": "Punch Line Philly"}])

    h._process_single_batch([_show(room="Punch Line Philly")])

    assert _inserted_rooms(h) == [""]


def test_room_matching_club_name_case_and_whitespace_insensitively_is_blanked():
    h = _handler([{"id": 1, "name": "Punch Line Philly"}])

    h._process_single_batch([_show(room="  PUNCH LINE PHILLY ")])

    assert _inserted_rooms(h) == [""]


def test_distinct_room_is_preserved():
    h = _handler([{"id": 1, "name": "Punch Line Philly"}])

    h._process_single_batch([_show(room="The Annex")])

    assert _inserted_rooms(h) == ["The Annex"]


def test_club_lookup_skipped_when_no_show_has_a_room():
    h = _handler([{"id": 1, "name": "Punch Line Philly"}])

    h._process_single_batch([_show(room=""), _show(room=None, name="Other Show")])

    assert _club_name_calls(h) == []


def test_multi_club_batch_compares_each_show_to_its_own_club():
    h = _handler([
        {"id": 1, "name": "Punch Line Philly"},
        {"id": 2, "name": "Punch Line SF"},
    ])

    h._process_single_batch([
        _show(club_id=1, room="Punch Line Philly"),
        _show(club_id=2, room="Punch Line Philly", name="Other Show"),
    ])

    # Club 1's room duplicates its own club name; club 2's room names a
    # different club, so it is treated as a real (if odd) room value.
    assert _inserted_rooms(h) == ["", "Punch Line Philly"]


def test_unknown_club_id_leaves_room_untouched():
    h = _handler([])

    h._process_single_batch([_show(club_id=99, room="Punch Line Philly")])

    assert _inserted_rooms(h) == ["Punch Line Philly"]


def test_suppressed_duplicates_collapse_in_batch_dedup():
    """Two rows differing only by venue-name-room collapse to one after suppression."""
    h = _handler([{"id": 1, "name": "Punch Line Philly"}])

    h._process_single_batch([
        _show(room="Punch Line Philly"),
        _show(room=""),
    ])

    assert _inserted_rooms(h) == [""]
