"""Pipeline smoke tests for the generic FullCalendar JSON feed scraper."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
import time_machine

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.implementations.api.fullcalendar_json.extractor import (
    FullCalendarJsonExtractor,
)
from laughtrack.scrapers.implementations.api.fullcalendar_json.scraper import (
    FullCalendarJsonScraper,
)


BASE_DOMAIN = "https://www.seshcomedy.com"
FEED_URL = f"{BASE_DOMAIN}/feed.php"


def _future_iso(days=7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _past_iso(days=1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _raw_event(**overrides):
    raw = {
        "title": "7/3 Friday Night SESH Showcase - 8:30 PM",
        "start": _future_iso(),
        "url": "event-detail.php?id=I6JEWESIB4EOYVG75NZN7UXY",
        "extendedProps": {
            "desc": "<p>Hosted by Sesh Comedy.</p>",
            "location": "55 Chrystie - SESH Comedy",
            "soldOut": False,
        },
    }
    raw.update(overrides)
    return raw


def _club() -> Club:
    club = Club(
        id=99,
        name="Sesh Comedy",
        address="55 Chrystie St, New York, NY 10002, USA",
        website=BASE_DOMAIN,
        popularity=0,
        zip_code="10002",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="fullcalendar_json",
        source_url=FEED_URL,
        external_id=None,
        metadata={},
    )
    club.active_scraping_source = source
    club.scraping_sources = [source]
    return club


def test_extract_events_parses_fullcalendar_feed_items():
    events = FullCalendarJsonExtractor.extract_events([_raw_event()], BASE_DOMAIN)

    assert len(events) == 1
    event = events[0]
    assert event.title == "7/3 Friday Night SESH Showcase - 8:30 PM"
    assert event.show_page_url == f"{BASE_DOMAIN}/event-detail.php?id=I6JEWESIB4EOYVG75NZN7UXY"
    assert event.description == "Hosted by Sesh Comedy."
    assert event.location == "55 Chrystie - SESH Comedy"


def test_extract_events_skips_past_and_sold_out_events():
    events = FullCalendarJsonExtractor.extract_events(
        [
            _raw_event(title="Past Show", start=_past_iso()),
            _raw_event(title="Sold Out Show", extendedProps={"soldOut": True}),
            _raw_event(title="Future Show"),
        ],
        BASE_DOMAIN,
    )

    assert [event.title for event in events] == ["Future Show"]


def test_extract_events_applies_title_filters():
    include = [__import__("re").compile("showcase", __import__("re").IGNORECASE)]
    exclude = [__import__("re").compile("class", __import__("re").IGNORECASE)]

    events = FullCalendarJsonExtractor.extract_events(
        [
            _raw_event(title="Friday Showcase"),
            _raw_event(title="Comedy Class"),
            _raw_event(title="Open Mic"),
        ],
        BASE_DOMAIN,
        include_title_res=include,
        exclude_title_res=exclude,
    )

    assert [event.title for event in events] == ["Friday Showcase"]


@time_machine.travel("2026-07-06T12:00:00Z", tick=False)
def test_extract_events_localizes_naive_start_to_club_timezone():
    events = FullCalendarJsonExtractor.extract_events(
        [_raw_event(start="2026-07-10T20:30:00")],
        BASE_DOMAIN,
        timezone_name="America/New_York",
    )

    assert len(events) == 1
    assert events[0].start == datetime(2026, 7, 10, 20, 30, tzinfo=ZoneInfo("America/New_York"))


def test_event_to_show_uses_feed_title_date_and_detail_url():
    event = FullCalendarJsonExtractor.extract_events([_raw_event()], BASE_DOMAIN)[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "7/3 Friday Night SESH Showcase - 8:30 PM"
    assert show.show_page_url == f"{BASE_DOMAIN}/event-detail.php?id=I6JEWESIB4EOYVG75NZN7UXY"
    assert show.tickets[0].purchase_url == show.show_page_url
    assert show.description == "Hosted by Sesh Comedy."


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_feed_url():
    scraper = FullCalendarJsonScraper(_club())

    assert await scraper.collect_scraping_targets() == [FEED_URL]


@pytest.mark.asyncio
async def test_get_data_fetches_feed_and_returns_page_data(monkeypatch):
    scraper = FullCalendarJsonScraper(_club())

    async def fake_fetch_json(url: str, **kwargs):
        return [_raw_event(), _raw_event(title="Past Show", start=_past_iso())]

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(FEED_URL)

    assert isinstance(result, EventListContainer)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "7/3 Friday Night SESH Showcase - 8:30 PM"


@pytest.fixture(params=["memory", "postgres"])
def persistence(request, monkeypatch):
    """Run real handler orchestration with memory SQL semantics or PostgreSQL."""
    import os
    from contextlib import contextmanager
    from laughtrack.core.entities.show.handler import ShowHandler
    from sql.show_queries import ShowQueries

    handler = ShowHandler()
    rows = []
    conn = None
    if request.param == "postgres":
        if not os.environ.get("TEST_DATABASE_URL"):
            pytest.skip("TEST_DATABASE_URL enables the additional real SQL regression")
        import psycopg2
        from psycopg2.extras import RealDictCursor, execute_values

        conn = psycopg2.connect(os.environ["TEST_DATABASE_URL"], cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SET LOCAL TIME ZONE 'UTC';
                CREATE TEMP TABLE clubs(id integer PRIMARY KEY, name text);
                INSERT INTO clubs VALUES (99, 'Sesh Comedy');
                CREATE TEMP TABLE shows(
                    id serial PRIMARY KEY, name text, show_page_url text,
                    description text, date timestamptz, club_id integer,
                    last_scraped_date timestamptz, room text,
                    production_company_id integer, last_scraped_by text,
                    scraped_by_organizer_id integer, show_type text,
                    UNIQUE(club_id,date,room)
                );
                CREATE TEMP TABLE saved_show(id serial PRIMARY KEY, show_id integer REFERENCES shows(id));
            """)

    @contextmanager
    def transaction():
        import copy

        before = copy.deepcopy(rows)
        if conn:
            with conn.cursor() as cur:
                cur.execute("SAVEPOINT persistence_test")
        try:
            yield conn
        except Exception:
            if conn:
                with conn.cursor() as cur:
                    cur.execute("ROLLBACK TO SAVEPOINT persistence_test")
            else:
                rows[:] = before
            raise
        finally:
            if conn:
                with conn.cursor() as cur:
                    cur.execute("RELEASE SAVEPOINT persistence_test")

    def execute(query, params=None, return_results=False, **kwargs):
        if conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall() if return_results else None
        if "pg_advisory_xact_lock" in query:
            return []
        if query == ShowQueries.GET_CLUB_NAMES_BY_IDS:
            return [{"id": 99, "name": "Sesh Comedy"}]
        if query.lstrip().startswith("SELECT"):
            return [dict(row) for row in rows]
        if "UPDATE shows" in query:
            room, row_id, club_id, date, url, old_room, destination_room = params
            target = next((r for r in rows if r["id"] == row_id), None)
            if target and not any(
                r["club_id"] == club_id and r["date"] == date and r["room"] == room and r["id"] != row_id for r in rows
            ):
                target["room"] = room
                return [{"id": row_id}]
            return []
        raise AssertionError(query)

    def batch(query, items, template=None, return_results=False, **kwargs):
        if conn:
            with conn.cursor() as cur:
                execute_values(cur, query, items, template=template)
                return cur.fetchall()
        results = []
        columns = [
            "name",
            "show_page_url",
            "description",
            "date",
            "club_id",
            "last_scraped_date",
            "room",
            "production_company_id",
            "last_scraped_by",
            "scraped_by_organizer_id",
            "show_type",
        ]
        for item in items:
            incoming = dict(zip(columns, item))
            existing = next(
                (
                    r
                    for r in rows
                    if (r["club_id"], r["date"], r["room"]) == (incoming["club_id"], incoming["date"], incoming["room"])
                ),
                None,
            )
            operation = "updated" if existing else "inserted"
            if existing is None:
                existing = {"id": len(rows) + 1}
                rows.append(existing)
            existing.update(incoming)
            results.append(dict(existing, operation_type=operation))
        return results

    def snapshot():
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM shows ORDER BY id")
                return [dict(r) for r in cur.fetchall()]
        return [dict(r) for r in rows]

    monkeypatch.setattr(handler, "transaction", transaction)
    monkeypatch.setattr(handler, "execute_with_cursor", execute)
    monkeypatch.setattr(handler, "execute_batch_operation", batch)
    monkeypatch.setattr(handler, "_update_shows_and_related", lambda batch, results: (batch, 0, 0))
    monkeypatch.setattr(handler, "_summarize_and_log", lambda batch, size: (0, 0, []))
    try:
        yield handler, snapshot, conn
    finally:
        if conn:
            conn.rollback()
            conn.close()


def _persisted_event(room, *, event_id="ONE", days=7, url=None, title="SESH Showcase"):
    event = FullCalendarJsonExtractor.extract_events(
        [
            _raw_event(
                title=title,
                start=_future_iso(days),
                url=url or f"event-detail.php?id={event_id}",
                extendedProps={"location": room},
            )
        ],
        BASE_DOMAIN,
    )[0]
    show = event.to_show(_club(), enhanced=False)
    show.last_scraped_by = "fullcalendar_json"
    return show


@time_machine.travel("2026-09-24T12:00:00Z", tick=False)
def test_event_location_change_reconciles(persistence):
    handler, snapshot, conn = persistence
    handler._process_single_batch([_persisted_event("Old location")])
    old_id = snapshot()[0]["id"]
    if conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO saved_show(show_id) VALUES (%s)", (old_id,))
    handler._process_single_batch([_persisted_event("New location", title="Renamed Showcase")])
    handler._process_single_batch([_persisted_event("New location", title="Renamed Showcase")])
    actual = snapshot()
    assert len(actual) == 1
    assert actual[0]["id"] == old_id
    assert actual[0]["room"] == "New location"
    assert actual[0]["name"] == "Renamed Showcase"
    if conn:
        with conn.cursor() as cur:
            cur.execute("SELECT show_id FROM saved_show")
            assert cur.fetchone()["show_id"] == old_id


@time_machine.travel("2026-09-24T12:00:00Z", tick=False)
def test_distinct_performances_survive_reconciliation(persistence):
    handler, snapshot, _ = persistence
    handler._process_single_batch([_persisted_event("Room A", event_id="ONE")])
    handler._process_single_batch([_persisted_event("", event_id="TWO")])
    handler._process_single_batch([_persisted_event("Room A", event_id="ONE", days=8)])
    assert len(snapshot()) == 3
    assert {r["show_page_url"] for r in snapshot()} == {
        f"{BASE_DOMAIN}/event-detail.php?id=ONE",
        f"{BASE_DOMAIN}/event-detail.php?id=TWO",
    }


@time_machine.travel("2026-09-24T12:00:00Z", tick=False)
def test_series_url_does_not_establish_performance_identity(persistence):
    handler, snapshot, _ = persistence
    handler._process_single_batch([_persisted_event("Room A", url="series.php?id=weekly")])
    handler._process_single_batch([_persisted_event("Room B", url="series.php?id=weekly")])
    assert len(snapshot()) == 2


@time_machine.travel("2026-09-24T12:00:00Z", tick=False)
def test_location_move_does_not_overwrite_other_event(persistence):
    handler, snapshot, _ = persistence
    handler._process_single_batch(
        [_persisted_event("Room A", event_id="ONE"), _persisted_event("Room B", event_id="TWO")]
    )
    before = [(r["id"], r["show_page_url"], r["room"]) for r in snapshot()]
    handler._process_single_batch([_persisted_event("Room B", event_id="ONE")])
    assert [(r["id"], r["show_page_url"], r["room"]) for r in snapshot()] == before


@time_machine.travel("2026-09-24T12:00:00Z", tick=False)
def test_room_move_rolls_back_when_upsert_fails(persistence, monkeypatch):
    handler, snapshot, _ = persistence
    handler._process_single_batch([_persisted_event("Room A")])
    before = snapshot()

    def fail(*args, **kwargs):
        raise ValueError("injected persistence failure")

    monkeypatch.setattr(handler, "execute_batch_operation", fail)
    with pytest.raises(ValueError, match="injected persistence failure"):
        handler._process_single_batch([_persisted_event("Room B")])
    assert snapshot() == before


@time_machine.travel("2026-09-24T12:00:00Z", tick=False)
def test_simultaneous_shared_identity_is_not_moved(persistence):
    handler, snapshot, _ = persistence
    handler._process_single_batch([_persisted_event("Room A"), _persisted_event("Room B")])
    original = {r["id"]: r["room"] for r in snapshot()}
    result = handler._process_single_batch([_persisted_event("Room C")])
    assert result.validation_errors == 1  # Blocks downstream stale cleanup.
    assert all(r["room"] == original[r["id"]] for r in snapshot() if r["id"] in original)


@time_machine.travel("2026-09-24T12:00:00Z", tick=False)
def test_homepage_url_does_not_move_existing_show(persistence):
    handler, snapshot, _ = persistence
    handler._process_single_batch([_persisted_event("Room A", url=BASE_DOMAIN)])
    handler._process_single_batch([_persisted_event("Room B", url=BASE_DOMAIN)])
    assert len(snapshot()) == 2


@time_machine.travel("2026-09-24T12:00:00Z", tick=False)
def test_different_ids_targeting_same_room_are_rejected_before_dedup(persistence):
    handler, snapshot, _ = persistence
    handler._process_single_batch(
        [_persisted_event("Room A", event_id="ONE"), _persisted_event("Room B", event_id="TWO")]
    )
    before = snapshot()
    result = handler._process_single_batch(
        [_persisted_event("Room C", event_id="ONE"), _persisted_event("Room C", event_id="TWO")]
    )
    assert result.validation_errors == 2
    assert snapshot() == before


@time_machine.travel("2026-09-24T12:00:00Z", tick=False)
def test_shared_identity_ambiguity_survives_batch_boundary(persistence):
    handler, snapshot, _ = persistence
    result = handler.insert_shows([_persisted_event("Room A"), _persisted_event("Room B")], batch_size=1)
    assert result.validation_errors == 2
    assert {row["room"] for row in snapshot()} == {"Room A", "Room B"}


@time_machine.travel("2026-09-24T12:00:00Z", tick=False)
def test_destination_conflict_survives_batch_boundary(persistence):
    handler, snapshot, _ = persistence
    result = handler.insert_shows(
        [_persisted_event("Room A", event_id="ONE"), _persisted_event("Room A", event_id="TWO")], batch_size=1
    )
    assert result.validation_errors == 2
    assert snapshot() == []
