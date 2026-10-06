"""Captured producer inventory retains every native occurrence and venue join."""

import json
from pathlib import Path

from laughtrack.core.clients.punchup.inventory import extract_inventory

ROOT = Path(__file__).resolve().parents[5]
PROJECTION = json.loads(
    (ROOT / "docs/audits/2026-09-28-organizer-venues/lets-shoppe/public-source-projection.json").read_text()
)["comedy_shoppe"]
PAGE = "4969662d-af53-4d87-b151-9f94c8f89d4c"


def html(events=None, locations=None):
    events = PROJECTION["events"] if events is None else events
    locations = PROJECTION["venues"] if locations is None else locations
    queries = [
        {"queryKey": ["venue-page", "comedyshoppe"], "state": {"data": {"id": PAGE, "locations": locations}}},
        {
            "queryKey": ["venuePageCarousel", PAGE, "public"],
            "state": {
                "data": {
                    "items": [{"type": "show", "show": e} for e in events[:20]] + [{"type": "image", "show": events[0]}]
                }
            },
        },
        {"queryKey": ["venueShows", PAGE], "state": {"data": events}},
    ]
    return (
        "<script>self.__next_f.push([1,"
        + json.dumps("a:" + json.dumps({"queries": queries}, separators=(",", ":")))
        + "])</script>"
    )


def test_captured_24_are_not_truncated_to_first_20():
    assert len(extract_inventory(html(), PAGE, "comedyshoppe").events) == 24


from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
import time_machine

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.the_comedy_shoppe.punchup import ComedyShoppeScraper
from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor


def club(ident):
    v = (
        PROJECTION["venues"][ident - 9001]
        if 9001 <= ident < 9001 + len(PROJECTION["venues"])
        else dict(name="Producer", address="Producer address", postal_code="10001", city="New York", state="NY")
    )
    return Club(
        id=ident,
        name=v["name"],
        address=v["address"],
        city=v["city"],
        state=v["state"],
        website="https://physical.example",
        popularity=0,
        zip_code=v["postal_code"],
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def source():
    c = club(327)
    routes = {
        v["id"]: dict(v, club_id=9001 + i, country_code="US", timezone="America/New_York")
        for i, v in enumerate(PROJECTION["venues"])
    }
    c.active_scraping_source = ScrapingSource(
        id=617,
        club_id=327,
        platform="punchup",
        scraper_key="the_comedy_shoppe",
        source_url="https://www.jjcomedy.com/socials",
        metadata={
            "punchup_venue_routes": dict(
                source_id=617, page_id=PAGE, slug="comedyshoppe", producer_id=91, routes=routes
            )
        },
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


async def pipeline(monkeypatch, events=None, mutate=None, api=None):
    c = source()
    raw = deepcopy(events if events is not None else PROJECTION["events"])
    locs = [dict(v, country_code="US") for v in deepcopy(PROJECTION["venues"])]
    if mutate:
        mutate(raw, locs, c)
    monkeypatch.setattr(ClubHandler, "get_physical_clubs_by_ids", lambda self, ids: [club(i) for i in ids])
    scraper = ComedyShoppeScraper(c)
    scraper.fetch_html = AsyncMock(return_value=html(raw, locs))
    scraper.fetch_json = AsyncMock(side_effect=api if api is not None else [raw[:20], raw[20:]])
    data = await scraper.get_data(c.scraping_url)
    return scraper, scraper.transform_data(data, c.scraping_url)


@pytest.mark.asyncio
@time_machine.travel("2026-09-28T00:00:00Z", tick=False)
async def test_captured_routing_preserves_24_dates_tickets_and_physical_venues(monkeypatch):
    scraper, shows = await pipeline(monkeypatch)
    assert len(shows) == 24 and not scraper.errors
    config = scraper.club.source_metadata["punchup_venue_routes"]
    for raw, show in zip(PROJECTION["events"], shows):
        assert show.club_id == config["routes"][raw["venue_id"]]["club_id"] != 327
        assert show.date.strftime("%Y-%m-%dT%H:%M:%S") == raw["datetime"]
        assert show.show_page_url == raw["ticket_link"]
        assert show.tickets[0].purchase_url == raw["ticket_link"]
        assert show.production_company_id == show.scraped_by_organizer_id == 91
        assert show.last_scraped_by == "the_comedy_shoppe" and not show.source_performance_id


@pytest.mark.asyncio
@time_machine.travel("2026-10-05T00:00:00Z", tick=False)
async def test_current_projection_keeps_current_dates(monkeypatch):
    current = json.loads(Path(__file__).with_name("current_projection.json").read_text())
    scraper, shows = await pipeline(monkeypatch, current["events"])
    expected = [e for e in current["events"] if e["datetime"] > "2026-10-05"]
    assert len(shows) == len(expected) and not scraper.errors
    assert {s.date.strftime("%Y-%m-%dT%H:%M:%S") for s in shows} == {e["datetime"] for e in expected}


@pytest.mark.asyncio
@time_machine.travel("2026-09-28T00:00:00Z", tick=False)
@pytest.mark.parametrize("field", ["venue_id", "venue", "location"])
async def test_conflicting_event_location_is_held(monkeypatch, field):
    def mutate(raw, locs, c):
        raw[0][field] = "wrong"

    scraper, shows = await pipeline(monkeypatch, mutate=mutate)
    assert len(shows) == 23 and scraper.errors


@pytest.mark.asyncio
@time_machine.travel("2026-09-28T00:00:00Z", tick=False)
async def test_missing_destination_or_changed_address_never_falls_back(monkeypatch):
    def mutate(raw, locs, c):
        locs[0]["address"] = "Wrong street"

    scraper, shows = await pipeline(monkeypatch, mutate=mutate)
    assert scraper.errors and all(s.club_id != 327 for s in shows)
    errors = list(scraper.errors)

    def scrape():
        scraper.errors.extend(errors)
        return shows

    monkeypatch.setattr(scraper, "scrape", scrape)
    result = scraper.scrape_with_result()
    result.fetches_ok = 1
    assert result.error and not ScrapingResultProcessor._is_clean_for_reconciliation(result)


@pytest.mark.asyncio
async def test_incomplete_pagination_does_not_accept_first_twenty(monkeypatch):
    scraper, shows = await pipeline(monkeypatch, api=[PROJECTION["events"][:20], None])
    assert not shows and scraper.errors


def test_unrelated_page_and_conflicting_occurrence():
    from laughtrack.core.clients.punchup.inventory import merge_events

    events = deepcopy(PROJECTION["events"])
    changed = dict(events[0], datetime="2027-01-01T20:00:00")
    merged, errors = merge_events(events + [changed])
    assert len(merged) == 23 and errors
    with pytest.raises(ValueError):
        extract_inventory(html(), "wrong-page", "comedyshoppe")


@pytest.mark.asyncio
@time_machine.travel("2026-09-28T00:00:00Z", tick=False)
async def test_api_only_events_are_retained(monkeypatch):
    raw = deepcopy(PROJECTION["events"])
    extra = [dict(raw[0], id=f"api-only-{i}", datetime=f"2027-01-0{i+1}T20:00:00") for i in range(3)]
    scraper, shows = await pipeline(monkeypatch, api=[raw[:20], raw[20:] + extra])
    assert len(shows) == 27 and not scraper.errors


@pytest.mark.asyncio
@time_machine.travel("2026-09-28T00:00:00Z", tick=False)
async def test_past_show_is_excluded_without_rollover(monkeypatch):
    def mutate(raw, locs, c):
        raw[0]["datetime"] = "2025-09-28T19:30:00"

    scraper, shows = await pipeline(monkeypatch, mutate=mutate)
    assert len(shows) == 23 and not scraper.errors


from tests.core.entities.club.test_physical_destination_lookup import database as physical_fixture
from tests.core.entities.show.test_source_performance_identity import database as identity_fixture
from tests.core.entities.show.test_source_performance_identity import handler_for

physical_database = physical_fixture
identity_database = identity_fixture


@pytest.mark.asyncio
@time_machine.travel("2026-09-28T00:00:00Z", tick=False)
async def test_actual_source_less_lookup_and_hidden_destination(physical_database):
    with physical_database.cursor() as cur:
        cur.execute("ALTER TABLE clubs ADD COLUMN city text, ADD COLUMN state text")
        v = PROJECTION["venues"][0]
        cur.execute(
            "UPDATE clubs SET timezone='America/New_York',name=%s,address=%s,zip_code=%s,city=%s,state=%s WHERE id=9001",
            (v["name"], v["address"], v["postal_code"], v["city"], v["state"]),
        )
    c = source()
    route = next(iter(c.source_metadata["punchup_venue_routes"]["routes"].items()))
    c.source_metadata["punchup_venue_routes"]["routes"] = {route[0]: route[1]}
    raw = [e for e in PROJECTION["events"] if e["venue_id"] == route[0]]
    scraper = ComedyShoppeScraper(c)
    scraper.fetch_html = AsyncMock(return_value=html(raw, [dict(v, country_code="US") for v in PROJECTION["venues"]]))
    scraper.fetch_json = AsyncMock(return_value=raw)
    page = await scraper.get_data(c.scraping_url)
    assert len(page.event_list) == len(raw) and not scraper.errors
    assert all(e.show.club_id == 9001 for e in page.event_list)
    route[1]["club_id"] = 9002
    page = await scraper.get_data(c.scraping_url)
    assert not page.event_list and scraper.errors


@pytest.mark.asyncio
@time_machine.travel("2026-09-28T00:00:00Z", tick=False)
async def test_repeat_postgresql_upsert_preserves_ids_and_references(monkeypatch, identity_database):
    _, shows = await pipeline(monkeypatch)
    handler = handler_for(identity_database)
    result = handler.insert_shows(shows, scraper_key="the_comedy_shoppe")
    assert result.inserts == 24
    ids = [s.id for s in shows]
    with identity_database.cursor() as cur:
        cur.execute("INSERT INTO saved_shows VALUES ('shoppe-user',%s)", (ids[0],))
        cur.execute("INSERT INTO ticket_purchase_click_events VALUES (900,%s)", (ids[0],))
    _, repeat = await pipeline(monkeypatch)
    result = handler.insert_shows(repeat, scraper_key="the_comedy_shoppe")
    assert result.updates == 24 and [s.id for s in repeat] == ids
    with identity_database.cursor() as cur:
        cur.execute("SELECT show_id FROM saved_shows WHERE profile_id='shoppe-user'")
        assert cur.fetchone()[0] == ids[0]
        cur.execute("SELECT show_id FROM ticket_purchase_click_events WHERE id=900")
        assert cur.fetchone()[0] == ids[0]


@pytest.mark.asyncio
@time_machine.travel("2026-10-05T00:00:00Z", tick=False)
async def test_reviewed_music_exclusion_keeps_paginated_comedy_and_source_scope(monkeypatch):
    raw = json.loads(Path(__file__).with_name("current_projection.json").read_text())["events"]
    api = json.loads(Path(__file__).with_name("api_projection.json").read_text())

    def configure(events, locations, c):
        c.source_metadata["exclude_title_patterns"] = [r"^\s*The Day Players at Wonders Theatre\s*$"]

    scraper, shows = await pipeline(monkeypatch, raw, mutate=configure, api=[api[:20], api[20:]])
    assert len(shows) == 25 and not scraper.errors
    assert any("Gabriel" in s.name and s.date.hour == 21 for s in shows)
    _, unfiltered = await pipeline(monkeypatch, raw, api=[api[:20], api[20:]])
    assert len(unfiltered) == 27


@pytest.mark.asyncio
@time_machine.travel("2026-10-05T00:00:00Z", tick=False)
@pytest.mark.parametrize("kind", ["past", "excluded"])
async def test_all_filtered_is_not_an_empty_calendar(monkeypatch, kind):
    from types import SimpleNamespace

    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
    )

    raw = [deepcopy(PROJECTION["events"][0])]

    def mutate(events, locs, c):
        if kind == "past":
            events[0]["datetime"] = "2025-01-01T20:00:00"
        else:
            c.source_metadata["exclude_title_patterns"] = [".*"]

    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        _, shows = await pipeline(monkeypatch, raw, mutate=mutate, api=[[]])
    finally:
        reset_diagnostics(token)
    result = SimpleNamespace(
        error=None,
        bot_block_detected=False,
        fetches_failed=0,
        fetches_ok=1,
        shows=shows,
        items_before_filter=diagnostics.items_before_filter,
    )
    assert not shows and diagnostics.items_before_filter == 1
    assert not ScrapingResultProcessor._is_clean_for_reconciliation(result)


@pytest.mark.asyncio
@time_machine.travel("2026-09-28T00:00:00Z", tick=False)
async def test_changed_database_destination_is_held(monkeypatch):
    scraper, _ = await pipeline(monkeypatch)

    def destinations(self, ids):
        result = [club(i) for i in ids]
        for c in result:
            c.address = "A different street"
        return result

    monkeypatch.setattr(ClubHandler, "get_physical_clubs_by_ids", destinations)
    scraper.fetch_json = AsyncMock(side_effect=[PROJECTION["events"][:20], PROJECTION["events"][20:]])
    page = await scraper.get_data(scraper.club.scraping_url)
    assert not page.event_list and scraper.errors


def test_registry_discovers_new_key():
    from laughtrack.app.registry import discover_scrapers

    assert discover_scrapers()["the_comedy_shoppe"] is ComedyShoppeScraper


@pytest.mark.asyncio
@time_machine.travel("2026-09-28T00:00:00Z", tick=False)
async def test_explicit_other_page_membership_is_held(monkeypatch):
    def mutate(events, locs, c):
        events[0]["venue_pages"] = [dict(id="another-page", is_live=True, show_visibility_status="visible")]

    scraper, shows = await pipeline(monkeypatch, mutate=mutate)
    assert len(shows) == 23 and scraper.errors
