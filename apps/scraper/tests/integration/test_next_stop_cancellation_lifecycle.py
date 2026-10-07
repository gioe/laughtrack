"""Real PostgreSQL cancellation lifecycle; no production connections or HTTP.

Set TEST_DATABASE_URL to a local PostgreSQL database. Each test creates an
isolated schema and rolls it back. Persistence, cancellation matching/guards,
result processing and stale SQL are real; only connection acquisition is scoped
to the fixture. Public visibility checks execute the web query's declared flag
contract, not an HTTP/browser end-to-end test.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import parse_dsn
from psycopg2.extras import RealDictCursor
import pytest

SCRAPER = Path(__file__).parents[2]
URL = "https://www.nextstopcomedy.com/events/venue-reviewed-event"
ADDRESS = "1 Main St, Boston, MA 02116, US"
CHILDREN = (
    "tickets",
    "lineup_items",
    "tagged_shows",
    "saved_shows",
    "sent_notifications",
    "discovery_show_feature_snapshots",
    "ticket_purchase_click_events",
)


@pytest.fixture
def lifecycle(monkeypatch, request):
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL enables isolated local PostgreSQL lifecycle verification")
    host = parse_dsn(dsn).get("host", "")
    if host not in {"", "localhost", "127.0.0.1", "::1"} and not host.startswith("/"):
        pytest.fail("Cancellation integration tests require a local PostgreSQL server")

    from laughtrack.core.entities.club.model import Club
    from laughtrack.core.entities.show.handler import ShowHandler
    from laughtrack.core.entities.show.model import Show
    from laughtrack.core.entities.show.service import ShowService
    from laughtrack.scrapers.implementations.next_stop_comedy.scraper import NextStopComedyScraper
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    conn = psycopg2.connect(dsn)
    schema = "cancellation_lifecycle_" + uuid4().hex
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("CREATE SCHEMA {}; SET LOCAL search_path TO {}; SET LOCAL TIME ZONE 'UTC'").format(
                sql.Identifier(schema), sql.Identifier(schema)
            )
        )
        cur.execute("""
        CREATE TABLE clubs(id int PRIMARY KEY,name text,address text,zip_code text);
        CREATE TABLE shows(id serial PRIMARY KEY,name text,show_page_url text,description text,date timestamptz,club_id int REFERENCES clubs,
          last_scraped_date timestamptz,room text,production_company_id int,last_scraped_by text,scraped_by_organizer_id int,
          show_type text,source_performance_id text,is_cancelled bool NOT NULL DEFAULT false);
        CREATE UNIQUE INDEX show_legacy ON shows(club_id,date,room) WHERE source_performance_id IS NULL;
        CREATE UNIQUE INDEX show_native ON shows(club_id,source_performance_id) WHERE source_performance_id IS NOT NULL;
        CREATE TABLE tickets(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,type text,price numeric,purchase_url text,sold_out bool);
        CREATE TABLE lineup_items(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,comedian_id text,role text);
        CREATE TABLE tagged_shows(show_id int REFERENCES shows ON DELETE CASCADE,tag_id int,PRIMARY KEY(show_id,tag_id));
        CREATE TABLE saved_shows(show_id int REFERENCES shows ON DELETE CASCADE,profile_id text,created_at timestamptz,PRIMARY KEY(show_id,profile_id));
        CREATE TABLE sent_notifications(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,user_id text,payload jsonb);
        CREATE TABLE discovery_show_feature_snapshots(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,evidence jsonb);
        CREATE TABLE ticket_purchase_click_events(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE SET NULL,club_id int,payload jsonb);
        """)
        cur.execute("INSERT INTO clubs VALUES(1,'Venue',%s,'02116')", (ADDRESS,))

    handler = ShowHandler()
    source_id = getattr(request, "param", None)
    show = Show(
        name="Venue",
        club_id=1,
        date=datetime.now(timezone.utc) + timedelta(days=30),
        show_page_url=URL,
        production_company_id=35,
        scraped_by_organizer_id=35,
        last_scraped_by="next_stop_comedy",
        show_type="standup",
        source_performance_id=source_id,
    )
    persisted = handler._persist_show_partitions([show], conn=conn)
    show.id = persisted[0]["id"]
    with conn.cursor() as cur:
        cur.execute("UPDATE shows SET last_scraped_date=NOW()-INTERVAL '1 day' WHERE id=%s", (show.id,))
        cur.execute("INSERT INTO tickets VALUES(10,%s,'General Admission',27,%s,false)", (show.id, URL))
        cur.execute("INSERT INTO lineup_items VALUES(20,%s,'real-comedian','host')", (show.id,))
        cur.execute("INSERT INTO tagged_shows VALUES(%s,30)", (show.id,))
        cur.execute("INSERT INTO saved_shows VALUES(%s,'test-profile',NOW())", (show.id,))
        cur.execute(
            "INSERT INTO sent_notifications VALUES(40,%s,'test-user','{\"delivered\":true}')", (show.id,)
        )
        cur.execute("INSERT INTO discovery_show_feature_snapshots VALUES(50,%s,'{\"score\":3}')", (show.id,))
        cur.execute(
            'INSERT INTO ticket_purchase_click_events VALUES(60,%s,1,\'{"session":"fixture"}\')', (show.id,)
        )

    def query(query, params=None, return_results=False, **kwargs):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall() if return_results else None

    real_apply = handler.apply_cancellations
    monkeypatch.setattr(handler, "execute_with_cursor", query)
    monkeypatch.setattr(handler, "apply_cancellations", lambda intents: real_apply(intents, conn=conn))
    processor = ScrapingResultProcessor.__new__(ScrapingResultProcessor)
    processor.show_service = ShowService.__new__(ShowService)
    processor.show_service.show_handler = handler
    proxy = Club(
        id=0,
        name="Next Stop Comedy",
        address="",
        website="https://www.nextstopcomedy.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=False,
        is_synthetic=True,
        production_company_id=35,
    )
    scraper = NextStopComedyScraper(proxy)
    scraper._stored_events = query(
        """SELECT s.*,c.name AS venue_name,c.address AS venue_address,c.zip_code AS venue_zip
        FROM shows s JOIN clubs c ON c.id=s.club_id""",
        return_results=True,
    )
    try:
        yield conn, show, handler, processor, scraper
    finally:
        conn.rollback()
        conn.close()


def snapshot(conn):
    result = {}
    with conn.cursor() as cur:
        for table in ("shows", *CHILDREN):
            cur.execute(sql.SQL("SELECT to_jsonb(t) FROM {} t").format(sql.Identifier(table)))
            result[table] = sorted(
                (row[0] for row in cur.fetchall()), key=lambda row: json.dumps(row, sort_keys=True)
            )
    return result


def detail(show, status="https://schema.org/EventCancelled", url=URL, date=None):
    node = {
        "@type": "ComedyEvent",
        "name": "Venue",
        "url": url,
        "startDate": (date or show.date).isoformat(),
        "eventStatus": status,
        "location": {
            "name": "Venue",
            "address": {
                "streetAddress": "1 Main St",
                "addressLocality": "Boston",
                "addressRegion": "MA",
                "postalCode": "02116",
                "addressCountry": "US",
            },
        },
    }
    if status is None:
        node.pop("eventStatus")
    return f'<link rel="canonical" href="{url}"><main><h1>Venue</h1></main><script type="application/ld+json">{json.dumps(node)}</script>'


def intents(scraper, show, html=None):
    from laughtrack.scrapers.implementations.next_stop_comedy.extractor import (
        extract_cancelled_events,
        extract_json_ld_events,
    )

    html = detail(show) if html is None else html
    return scraper._match_cancellations(extract_cancelled_events(html, URL), extract_json_ld_events(html))


def club_result(cancellations):
    from laughtrack.core.models.results import ClubScrapingResult

    return ClubScrapingResult(
        club_name="Venue",
        club_id=1,
        shows=[],
        execution_time=0,
        scraper_key="next_stop_comedy",
        production_company_id=35,
        fetches_ok=1,
        fetches_failed=0,
        items_before_filter=0,
        cancellations=cancellations,
    )


def public_ids(conn):
    # Bind this SQL-level proof to the actual web mapper/Prisma flag contract.
    contract = (SCRAPER.parent / "web/lib/data/show/showSelect.ts").read_text()
    assert re.search(r"NON_CANCELLED_SHOW_WHERE\s*=\s*\{\s*isCancelled:\s*false\s*\}", contract)
    detail_query = (SCRAPER.parent / "web/lib/data/show/detail/findShowById.ts").read_text()
    assert "where: { id, isCancelled: false }" in detail_query
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM shows WHERE is_cancelled=false")
        return [row[0] for row in cur.fetchall()]


@pytest.mark.parametrize(
    "lifecycle", [None, "next_stop_comedy:4632c328-eafb-4707-9295-eaca57ce3cb3"], indirect=True
)
def test_scheduled_cancelled_repeat_cleanup_and_ordinary_upsert(lifecycle):
    from sql.show_queries import ShowQueries

    conn, show, handler, processor, scraper = lifecycle
    before = snapshot(conn)
    assert public_ids(conn) == [show.id]
    cancellations = intents(scraper, show)
    assert len(cancellations) == 1
    result = processor.insert_club_result(club_result(cancellations))
    assert not result.errors and not result.db_errors
    after = snapshot(conn)
    # A flag written after cleanup would lose this deliberately stale row and
    # its children. Exact equality proves ordering as well as payload retention.
    assert after["shows"] == [dict(before["shows"][0], is_cancelled=True)]
    assert all(after[table] == before[table] for table in CHILDREN)
    assert public_ids(conn) == []
    processor.insert_club_result(club_result(cancellations))
    assert snapshot(conn) == after

    cutoff = datetime.now(timezone.utc) + timedelta(seconds=1)
    with conn.cursor() as cur:
        for count_sql, delete_sql, owner in [
            (ShowQueries.COUNT_STALE_FUTURE_SHOWS, ShowQueries.DELETE_STALE_FUTURE_SHOWS, "next_stop_comedy"),
            (
                ShowQueries.COUNT_STALE_FUTURE_SHOWS_BY_ORGANIZER,
                ShowQueries.DELETE_STALE_FUTURE_SHOWS_BY_ORGANIZER,
                35,
            ),
        ]:
            cur.execute(count_sql, (1, owner, cutoff))
            assert cur.fetchone()[0] == 0
            cur.execute(delete_sql, (1, owner, cutoff))
            assert cur.fetchall() == []
    ordinary = handler._persist_show_partitions([show], conn=conn)
    assert ordinary[0]["id"] == show.id
    upserted = snapshot(conn)
    assert upserted["shows"][0]["is_cancelled"] is True
    assert all(upserted[table] == before[table] for table in CHILDREN)
    assert public_ids(conn) == []  # Reactivation requires a separate reviewed action.


@pytest.mark.parametrize(
    "control", ["scheduled", "missing_status", "rescheduled", "redirect", "fetch_failure", "ambiguous"]
)
def test_non_authoritative_controls_do_not_cancel_or_delete(lifecycle, control):
    conn, show, handler, _, scraper = lifecycle
    html = detail(show)
    if control == "scheduled":
        html = detail(show, status="https://schema.org/EventScheduled")
    if control == "missing_status":
        html = detail(show, status=None)
    if control == "rescheduled":
        html = detail(show, date=show.date + timedelta(days=1))
    if control == "redirect":
        html = detail(show, url=URL + "-redirect")
    if control == "fetch_failure":
        html = ""
    if control == "ambiguous":
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO shows(name,show_page_url,date,club_id,room,production_company_id,last_scraped_by,last_scraped_date) SELECT name,show_page_url,date,club_id,'second-room',production_company_id,last_scraped_by,last_scraped_date FROM shows"
            )
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT s.*,c.name AS venue_name,c.address AS venue_address,c.zip_code AS venue_zip FROM shows s JOIN clubs c ON c.id=s.club_id"
            )
            scraper._stored_events = cur.fetchall()
    before = snapshot(conn)
    cancellations = intents(scraper, show, html)
    assert cancellations == []
    assert handler.apply_cancellations(cancellations) == []
    assert snapshot(conn) == before
    assert public_ids(conn)


@pytest.mark.parametrize("drift", ["name", "native_identity", "venue_address"])
def test_changed_identity_between_match_and_write_blocks_cleanup(lifecycle, drift):
    conn, show, _, processor, scraper = lifecycle
    cancellations = intents(scraper, show)
    assert len(cancellations) == 1
    with conn.cursor() as cur:
        if drift == "name":
            cur.execute("UPDATE shows SET name='Different event'")
        elif drift == "native_identity":
            cur.execute("UPDATE shows SET source_performance_id='next_stop_comedy:different'")
        else:
            cur.execute("UPDATE clubs SET address='Different venue address'")
    before = snapshot(conn)
    result = processor.insert_club_result(club_result(cancellations))
    assert result.errors or result.db_errors or result.validation_errors
    assert snapshot(conn) == before
    assert public_ids(conn) == [show.id]
