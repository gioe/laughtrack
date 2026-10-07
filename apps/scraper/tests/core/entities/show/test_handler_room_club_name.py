"""Room values that duplicate the club name are blanked at ingestion (TASK-2803).

Several scrapers (ticketmaster/live_nation, tixr PIXL) copy the venue name into
the room field, so shows.room repeats the club name instead of naming a room.
The handler suppresses those values before in-batch dedup and the upsert.
"""
from datetime import datetime
from unittest.mock import MagicMock

import pytest
import time_machine

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


def test_reviewed_wix_room_survives_title_change_before_physical_upsert():
    """Title corrections must not change a reviewed Wix performance's room key."""
    h = _handler([{"id": 1, "name": "The Royce Social Hall"}])
    show = _show(room="The Royce Social Hall", name="Comedy | 8:30PM")
    show.last_scraped_by = "wix_events"
    show.production_company_id = show.scraped_by_organizer_id = 46
    # Existing title is 8PM, so the title-based reconciliation returns no match.
    h._process_single_batch([show])
    assert _inserted_rooms(h) == ["The Royce Social Hall"]


def test_unreviewed_wix_room_still_suppressed():
    h = _handler([{"id": 1, "name": "The Royce Social Hall"}])
    show = _show(room="The Royce Social Hall")
    show.last_scraped_by = "wix_events"
    h._process_single_batch([show])
    assert _inserted_rooms(h) == [""]


@pytest.mark.parametrize("producer,organizer", [(46, 47), (46, None), (None, 46), (0, 0), (-1, -1), (True, True), (46, "46"), ("46", "46")])
def test_invalid_wix_provenance_cannot_preserve_venue_name_room(producer, organizer):
    h = _handler([{"id": 1, "name": "The Royce Social Hall"}])
    show = _show(room="The Royce Social Hall")
    show.last_scraped_by = "wix_events"
    show.production_company_id = producer
    show.scraped_by_organizer_id = organizer
    h._process_single_batch([show])
    assert _inserted_rooms(h) == [""]


def test_other_scraper_with_producer_provenance_still_suppresses_room():
    h = _handler([{"id": 1, "name": "The Royce Social Hall"}])
    show = _show(room="The Royce Social Hall")
    show.last_scraped_by = "seatengine"
    show.production_company_id = show.scraped_by_organizer_id = 46
    h._process_single_batch([show])
    assert _inserted_rooms(h) == [""]


@time_machine.travel("2036-10-07T12:00:00Z", tick=False)
def test_reviewed_wix_title_refresh_updates_original_postgres_row_and_references():
    """Exercise the real physical-key upsert after room suppression and title lookup."""
    import os
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values

    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL required for physical-key PostgreSQL regression")
    connection = psycopg2.connect(dsn)
    try:
        with connection.cursor() as cur:
            cur.execute("""
                CREATE TEMP TABLE clubs(id int PRIMARY KEY,name text);
                CREATE TEMP TABLE shows(id serial PRIMARY KEY,name text,show_page_url text,description text,
                    date timestamptz,club_id int,last_scraped_date timestamptz,room text,
                    production_company_id int,last_scraped_by text,scraped_by_organizer_id int,
                    show_type text,source_performance_id text);
                CREATE UNIQUE INDEX ON shows(club_id,date,room) WHERE source_performance_id IS NULL;
                CREATE TEMP TABLE saved_shows(show_id int REFERENCES shows ON DELETE CASCADE,profile_id text);
                CREATE TEMP TABLE ticket_purchase_click_events(id int,show_id int REFERENCES shows ON DELETE SET NULL);
                INSERT INTO clubs VALUES(1,'The Royce Social Hall');
                INSERT INTO shows(id,name,club_id,date,room,show_page_url) VALUES
                    (7898492,'Comedy | 8PM',1,'2036-10-17T00:30:00Z','The Royce Social Hall','https://example.com/show');
                INSERT INTO saved_shows VALUES(7898492,'saved-profile');
                INSERT INTO ticket_purchase_click_events VALUES(1,7898492);
            """)
        h = _handler([])

        def execute(query, params=None, return_results=False):
            with connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall() if return_results else None

        def batch(query, items, template, **kwargs):
            with connection.cursor(cursor_factory=RealDictCursor) as cur:
                return execute_values(cur, query, items, template=template, fetch=True)

        h.execute_with_cursor = execute
        h.execute_batch_operation = batch
        for _ in range(2):
            show = _show(room="The Royce Social Hall", name="Comedy | 8:30PM",
                         date=datetime.fromisoformat("2036-10-17T00:30:00+00:00"))
            show.last_scraped_by = "wix_events"
            show.production_company_id = show.scraped_by_organizer_id = 46
            result = h._process_single_batch([show])
            assert result.updates == 1 and result.inserts == 0
            assert show.id == 7898492
        with connection.cursor() as cur:
            cur.execute("SELECT id,name,room FROM shows")
            assert cur.fetchall() == [(7898492,"Comedy | 8:30PM","The Royce Social Hall")]
            cur.execute("SELECT show_id FROM saved_shows")
            assert cur.fetchall() == [(7898492,)]
            cur.execute("SELECT show_id FROM ticket_purchase_click_events")
            assert cur.fetchall() == [(7898492,)]
    finally:
        connection.rollback()
        connection.close()
