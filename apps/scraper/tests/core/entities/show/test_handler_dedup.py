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
    """TASK-3489: incoming room='' must NOT be rewritten to a legacy NULL room.

    Postgres treats NULL as distinct in the (club_id, date, room) unique index,
    so writing NULL makes the upsert's ON CONFLICT miss and INSERT a fresh
    NULL-room row on every scrape — the per-run duplicate accretion this task
    fixes. The canonical room collapses to '' (never NULL) so repeated scrapes
    converge on a single row; the legacy NULL rows are swept by the
    collapse_duplicate_shows_stable_identity backfill.
    """
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
    assert inserted_items[0][6] == ""


def test_incoming_empty_room_not_rewritten_to_null_with_many_legacy_null_rows():
    """The accretion repro: many existing NULL-room rows for one showtime.

    Mirrors Bricktown Comedy club 90 / Steve Hofstetter /shows/319290, where 75
    NULL-room rows piled up because each scrape rewrote the incoming '' to NULL
    and the upsert could never converge. The collapse must keep the incoming
    room '' so the upsert reconciles instead of inserting yet another NULL row.
    """
    h = _handler()
    null_rows = [
        {
            "id": 1000 + i,
            "club_id": 1,
            "date": datetime(2026, 6, 1, 20, 0, 0),
            "room": None,
            "name": "Same Show",
        }
        for i in range(5)
    ]
    h.execute_with_cursor = MagicMock(return_value=null_rows)

    h._process_single_batch([_show(room="")])

    inserted_items = h.execute_batch_operation.call_args.args[1]
    assert len(inserted_items) == 1
    assert inserted_items[0][6] == ""


def test_incoming_empty_room_collapses_onto_existing_venue_name_room_row():
    """TASK-2806: the Ticketmaster client no longer emits the TM venue name as
    room, so incoming shows arrive with room='' while pre-fix rows may still
    hold a venue-name room that differs from clubs.name ('Punch Line San
    Francisco' vs 'Punch Line SF' - the TASK-2803 suppression only blanks
    exact club-name matches). Cross-batch collapse must rewrite the incoming
    empty room to the existing row's room so the upsert updates that row
    instead of inserting a duplicate listing.
    """
    h = _handler()
    h.execute_with_cursor = MagicMock(
        return_value=[
            {
                "id": 10,
                "club_id": 1,
                "date": datetime(2026, 6, 1, 20, 0, 0),
                "room": "Punch Line San Francisco",
                "name": "Same Show",
            }
        ]
    )
    # The upsert hits the existing row's (club_id, date, room) key, so the
    # returned row carries the venue-name room.
    h.execute_batch_operation = MagicMock(
        return_value=[
            {
                "id": 10,
                "club_id": 1,
                "date": datetime(2026, 6, 1, 20, 0, 0),
                "room": "Punch Line San Francisco",
                "operation_type": "updated",
            }
        ]
    )

    result = h._process_single_batch([_show(room="")])

    inserted_items = h.execute_batch_operation.call_args.args[1]
    assert len(inserted_items) == 1
    assert inserted_items[0][6] == "Punch Line San Francisco"
    assert result.updates == 1


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


def test_cross_batch_collapse_preserves_rooms_without_matching_existing_rows():
    """An unrelated DB match must not blank rooms on new shows in the same batch."""
    h = _handler()
    h.execute_with_cursor = MagicMock(
        return_value=[
            {
                "id": 10,
                "club_id": 1,
                "date": datetime(2026, 6, 1, 20, 0, 0),
                "room": "",
                "name": "Existing Show",
            }
        ]
    )
    shows = [
        _show(name="Existing Show", room=""),
        _show(name="New Main Room Show", room="Main Room"),
        _show(name="New Upstairs Show", room="Upstairs"),
    ]

    collapsed = h._collapse_cross_batch_duplicates(shows)

    assert collapsed == 0
    assert [show.room for show in shows] == ["", "Main Room", "Upstairs"]


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


def test_patronticket_reschedule_moves_highest_id_among_duplicate_rows():
    """With pre-existing duplicate rows for one instance, move only the newest (highest id)."""
    later_date = datetime(2026, 7, 11, 21, 0, 0)  # a second reschedule, matches neither row
    existing = [
        {"id": 481928, "club_id": 1, "date": _OLD_DATE, "room": "", "show_page_url": _PT_URL},
        {"id": 535489, "club_id": 1, "date": _NEW_DATE, "room": "", "show_page_url": _PT_URL},
    ]
    h = _pt_handler(existing)  # GET orders by id, so the list arrives id-ascending

    h._process_single_batch([_show(date=later_date, url=_PT_URL)])

    update_calls = _update_calls(h)
    assert len(update_calls) == 1
    # Exactly one move, targeting the highest-id (most recent) row.
    assert update_calls[0].args[1] == (later_date, 535489, later_date)


def test_patronticket_no_move_when_no_room_compatible_row_exists():
    """A room mismatch between the existing row and the incoming show blocks the move.

    Moving a different-room row would land it off the upsert's (club_id, date, room)
    conflict key, so reconciliation skips it rather than risk a duplicate.
    """
    existing = {
        "id": 481928,
        "club_id": 1,
        "date": _OLD_DATE,
        "room": "Main Stage",
        "show_page_url": _PT_URL,
    }
    h = _pt_handler([existing])

    h._process_single_batch([_show(date=_NEW_DATE, room="", url=_PT_URL)])

    assert _update_calls(h) == []


# --- SeatEngine Classic stable show URL reconciliation (TASK-2694) ----------

_SEATENGINE_CLASSIC_URL = "https://newbrunswick.stressfactory.com/shows/374462"


def test_seatengine_classic_reschedule_moves_existing_row_in_place():
    """A SeatEngine Classic start-time correction moves the stable /shows/id row."""
    h = _handler()

    def fake_exec(query, params=None, return_results=False):
        query_text = str(query)
        if "show_page_url LIKE '%%/shows/%%'" in query_text:
            return [
                {
                    "id": 2125402,
                    "club_id": 1,
                    "date": _OLD_DATE,
                    "room": "",
                    "show_page_url": _SEATENGINE_CLASSIC_URL,
                }
            ]
        return []

    h.execute_with_cursor = MagicMock(side_effect=fake_exec)

    incoming = _show(
        name="Corey B",
        date=_NEW_DATE,
        url=_SEATENGINE_CLASSIC_URL,
    )
    incoming.last_scraped_by = "seatengine_classic"
    h._process_single_batch([incoming])

    update_calls = _update_calls(h)
    assert len(update_calls) == 1
    assert update_calls[0].args[1] == (_NEW_DATE, 2125402, _NEW_DATE)


def test_seatengine_classic_reconciles_across_domain_rebrand():
    """TASK-3489: a venue domain rebrand keeps the same stable /shows/<id>.

    Fort Lauderdale Improv migrated daniaimprov.com -> www.improvftl.com and the
    parsed start time drifted across runs. Both hosts expose /shows/313789, so
    the reconciler must match on the host-agnostic (club_id, /shows/<id>) and
    move the existing daniaimprov row in place rather than inserting a second
    improvftl row — one performance, one row.
    """
    h = _handler()
    old_domain_url = "https://www.daniaimprov.com/shows/313789"
    new_domain_url = "https://www.improvftl.com/shows/313789"

    def fake_exec(query, params=None, return_results=False):
        if "show_page_url LIKE '%%/shows/%%'" in str(query):
            return [
                {
                    "id": 279633,
                    "club_id": 1,
                    "date": _OLD_DATE,
                    "room": "",
                    "show_page_url": old_domain_url,
                    "last_scraped_by": "seatengine_classic",
                }
            ]
        return []

    h.execute_with_cursor = MagicMock(side_effect=fake_exec)

    incoming = _show(name="Rick Glassman", date=_NEW_DATE, url=new_domain_url)
    incoming.last_scraped_by = "seatengine_classic"
    h._process_single_batch([incoming])

    update_calls = _update_calls(h)
    assert len(update_calls) == 1
    # The pre-existing daniaimprov row (id 279633) is moved to the drifted date,
    # so the improvftl upsert reconciles onto it instead of inserting a dup.
    assert update_calls[0].args[1] == (_NEW_DATE, 279633, _NEW_DATE)
