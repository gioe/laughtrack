"""Real PostgreSQL upserts preserve native performances and their relationships."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import pytest

from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from sql.show_queries import ShowQueries


@pytest.fixture
def database():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL required for native identity PostgreSQL regression")
    connection = psycopg2.connect(dsn)
    schema = "identity_" + uuid4().hex
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{schema}"')
        cursor.execute(f'SET search_path TO "{schema}"')
        cursor.execute("""
            CREATE TABLE shows (
                id serial PRIMARY KEY, name text, show_page_url text, description text,
                date timestamptz NOT NULL, club_id int NOT NULL, last_scraped_date timestamptz,
                room text, is_cancelled boolean NOT NULL DEFAULT false, production_company_id int, last_scraped_by text,
                scraped_by_organizer_id int, show_type text
            );
            CREATE UNIQUE INDEX shows_club_id_date_room_key ON shows(club_id,date,room);
            CREATE TABLE tickets(id serial PRIMARY KEY, show_id int REFERENCES shows ON DELETE CASCADE,
                purchase_url text, UNIQUE(show_id,purchase_url));
            CREATE TABLE saved_shows(profile_id text, show_id int REFERENCES shows ON DELETE CASCADE);
            CREATE TABLE ticket_purchase_click_events(id int PRIMARY KEY,
                show_id int REFERENCES shows ON DELETE SET NULL);
        """)
        # The migration must upgrade an existing physical-key table, not merely a fresh schema.
        cursor.execute("INSERT INTO shows(id,name,club_id,date,room) VALUES (100,'Legacy',9,'2026-10-01T20:00Z','')")
        cursor.execute("INSERT INTO saved_shows VALUES ('legacy-user',100)")
        connection.commit()
        migration = (
            Path(__file__).resolve().parents[5]
            / "web/prisma/migrations/20260930193000_show_source_performance_identity/migration.sql"
        )
        cursor.execute(migration.read_text())
    try:
        yield connection
    finally:
        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA "{schema}" CASCADE')
        connection.commit()
        connection.close()


def handler_for(connection):
    handler = ShowHandler.__new__(ShowHandler)
    handler._suppress_room_matching_club_name = MagicMock()
    handler._collapse_cross_batch_duplicates = MagicMock()
    handler._reconcile_patronticket_instances = MagicMock()
    handler._reconcile_seatengine_classic_show_urls = MagicMock()
    handler.tag_handler = MagicMock()
    handler.update_show_lineups = MagicMock(return_value=(0, 0))

    def batch(query, items, template, **kwargs):
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            return execute_values(cursor, query, items, template=template, fetch=True)

    def tickets(shows):
        with connection.cursor() as cursor:
            for show in shows:
                for ticket in show.tickets:
                    cursor.execute(
                        "INSERT INTO tickets(show_id,purchase_url) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                        (show.id, ticket.purchase_url),
                    )

    handler.execute_batch_operation = batch
    handler.ticket_handler = SimpleNamespace(insert_tickets=tickets)
    return handler


def performance(number, date=None):
    return Show(
        name=f"Performance {number}",
        club_id=183,
        date=date
        or (datetime.now(timezone.utc) + timedelta(days=10)).replace(hour=20, minute=0, second=0, microsecond=0),
        room="",
        show_page_url="https://annoyance.thundertix.com/events/100",
        source_performance_id=f"thundertix:annoyance:100:{number}",
        tickets=[
            Ticket(
                price=10,
                purchase_url=f"https://annoyance.thundertix.com/orders/new?event_id=100&performance_id={number}",
            )
        ],
    )


@pytest.mark.parametrize("batch_size", [1, 100])
def test_distinct_simultaneous_performances_survive_refresh(database, batch_size):
    handler = handler_for(database)
    first, second = performance(1), performance(2)
    result = handler.insert_shows([first, second], batch_size=batch_size, scraper_key="thundertix")
    assert result.validation_errors == result.db_errors == result.errors == 0
    assert result.inserts == 2
    assert first.id != second.id
    original_ids = (first.id, second.id)
    with database.cursor() as cursor:
        cursor.execute("INSERT INTO saved_shows VALUES ('a',%s),('b',%s)", original_ids)
        cursor.execute("INSERT INTO ticket_purchase_click_events VALUES (1,%s),(2,%s)", original_ids)

    repeat = [performance(1), performance(2)]
    result = handler.insert_shows(repeat, batch_size=batch_size, scraper_key="thundertix")
    assert result.updates == 2
    assert tuple(show.id for show in repeat) == original_ids

    singleton = performance(2)
    singleton.name = "Updated second performance"
    assert handler.insert_shows([singleton], scraper_key="thundertix").updates == 1
    assert singleton.id == second.id
    moved = performance(2, second.date + timedelta(hours=1))
    moved.room = "Small Theater"
    assert handler.insert_shows([moved], scraper_key="thundertix").updates == 1
    assert moved.id == second.id

    with database.cursor() as cursor:
        cursor.execute("SELECT id,name,room FROM shows WHERE club_id=183 ORDER BY id")
        assert cursor.fetchall() == [(first.id, "Performance 1", ""), (second.id, "Performance 2", "Small Theater")]
        cursor.execute("SELECT show_id,purchase_url FROM tickets ORDER BY show_id")
        assert cursor.fetchall() == [
            (first.id, first.tickets[0].purchase_url),
            (second.id, second.tickets[0].purchase_url),
        ]
        cursor.execute("SELECT show_id FROM saved_shows WHERE profile_id <> 'legacy-user' ORDER BY show_id")
        assert cursor.fetchall() == [(first.id,), (second.id,)]
        cursor.execute("SELECT show_id FROM ticket_purchase_click_events ORDER BY id")
        assert cursor.fetchall() == [(first.id,), (second.id,)]
        cursor.execute("SELECT show_id FROM saved_shows WHERE profile_id='legacy-user'")
        assert cursor.fetchone() == (100,)


def test_legacy_slot_upsert_and_identified_row_do_not_overwrite_each_other(database):
    handler = handler_for(database)
    identified = performance(1)
    handler.insert_shows([identified], scraper_key="thundertix")
    legacy = performance(2)
    legacy.source_performance_id = None
    handler.insert_shows([legacy], scraper_key="legacy")
    assert legacy.id != identified.id
    refreshed = performance(3)
    refreshed.source_performance_id = None
    assert handler.insert_shows([refreshed], scraper_key="legacy").updates == 1
    assert refreshed.id == legacy.id
    with database.cursor() as cursor:
        cursor.execute("SELECT name FROM shows WHERE id=%s", (identified.id,))
        assert cursor.fetchone() == ("Performance 1",)


def test_stale_reconciliation_keeps_each_refreshed_identity(database):
    handler = handler_for(database)
    shows = [performance(1), performance(2), performance(3)]
    handler.insert_shows(shows, scraper_key="thundertix")
    cutoff = datetime.now(timezone.utc)
    with database.cursor() as cursor:
        cursor.execute("UPDATE shows SET last_scraped_date=%s WHERE club_id=183", (cutoff - timedelta(days=1),))
    refreshed = [performance(1), performance(2)]
    assert handler.insert_shows(refreshed, scraper_key="thundertix").updates == 2
    with database.cursor() as cursor:
        cursor.execute(ShowQueries.COUNT_STALE_FUTURE_SHOWS, (183, "thundertix", cutoff))
        assert cursor.fetchone() == (1,)
        cursor.execute(ShowQueries.DELETE_STALE_FUTURE_SHOWS, (183, "thundertix", cutoff))
        assert [row[0] for row in cursor.fetchall()] == [shows[2].id]
        cursor.execute("SELECT id FROM shows WHERE club_id=183 ORDER BY id")
        assert cursor.fetchall() == [(shows[0].id,), (shows[1].id,)]
