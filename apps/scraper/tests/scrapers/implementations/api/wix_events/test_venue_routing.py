"""Wix source routing uses reviewed full addresses, preserving source and rooms."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.wix_events.scraper import WixEventsScraper
from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

AUDIT = Path(__file__).resolve().parents[5] / "docs/audits/2026-09-28-organizer-venues/ac-pag/ac-wix-source.json"
EVENTS = json.loads(AUDIT.read_text())["events"]


def venue(ident):
    return Club(
        id=ident,
        name=f"Venue {ident}",
        address="Verified address",
        website="https://physical.example",
        popularity=0,
        zip_code="08401",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def signature(location):
    address = location["fullAddress"]
    street = address["streetAddress"]
    return dict(
        name=location["name"],
        country=address["country"],
        state=address["subdivision"],
        city=address["city"],
        street_number=street["number"],
        street_name=street["name"],
        street_apt=street.get("apt", ""),
        postal_code=address["postalCode"][:5],
    )


def source():
    club = venue(412)
    routes = {}
    for event in EVENTS:
        loc = event["location"]
        name = loc["name"]
        ident = 9001 if name == "Hi Point Pub" else 9002 if name == "The Cove Restaurant" else 412
        routes[name] = {"club_id": ident, "location": signature(loc)}
    club.active_scraping_source = ScrapingSource(
        id=291,
        club_id=412,
        platform="wix_events",
        scraper_key="wix_events",
        wix_event_id="comp-lpdlygbr",
        source_url="https://www.acjokes.com",
        metadata={
            "wix_venue_routes": {
                "source_id": 291,
                "component_id": "comp-lpdlygbr",
                "producer_id": 73,
                "routes": list(routes.values()),
            }
        },
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


async def pipeline(monkeypatch, events, club=None):
    monkeypatch.setattr(ClubHandler, "get_physical_clubs_by_ids", lambda self, ids: [venue(i) for i in ids])
    scraper = WixEventsScraper(club or source())
    scraper.fetch_json = AsyncMock(return_value={"events": events, "hasMore": False})
    page = await scraper.get_data("https://www.acjokes.com/events?limit=50&offset=0")
    return scraper, scraper.transform_data(page, "https://www.acjokes.com")


@pytest.mark.asyncio
async def test_pinned_44_events_route_four_offsite_preserving_40_resorts_rooms(monkeypatch):
    scraper, shows = await pipeline(monkeypatch, deepcopy(EVENTS))
    assert len(shows) == 44
    assert sum(s.club_id == 412 for s in shows) == 40
    assert sum(s.club_id == 9001 for s in shows) == 3
    assert sum(s.club_id == 9002 for s in shows) == 1
    assert {s.room for s in shows if s.club_id == 412} == {
        "Resorts Casino - Starlight Ballroom",
        "Resorts Casino - Directors Room",
    }
    for raw, show in zip(EVENTS, shows):
        assert show.room == raw["location"]["name"]
        assert show.show_page_url == f"https://www.acjokes.com/event-details/{raw['slug']}"
        assert show.tickets[0].purchase_url == show.show_page_url
        assert show.production_company_id == show.scraped_by_organizer_id == 73
        assert show.last_scraped_by == "wix_events"


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["name_only", "city", "suite", "tbd", "conflict", "source", "component", "disabled"])
async def test_incomplete_or_conflicting_location_is_held(monkeypatch, change):
    raw = deepcopy(next(e for e in EVENTS if e["location"]["name"] == "Hi Point Pub"))
    club = source()
    if change == "name_only":
        raw["location"] = {"name": "Hi Point Pub"}
    elif change == "city":
        raw["location"]["fullAddress"]["city"] = "Atlantic City"
    elif change == "suite":
        raw["location"]["fullAddress"]["streetAddress"]["apt"] = "Suite 308"
    elif change == "tbd":
        raw["location"]["tbd"] = True
    elif change == "conflict":
        raw["location"]["address"] = "Different street and city"
    elif change == "source":
        club.source_metadata["wix_venue_routes"]["source_id"] = 999
    elif change == "component":
        club.source_metadata["wix_venue_routes"]["component_id"] = "other"
    else:
        club.active_scraping_source.enabled = False
    _, shows = await pipeline(monkeypatch, [raw], club)
    assert shows == []


@pytest.mark.asyncio
async def test_unconfigured_wix_retains_legacy_behavior(monkeypatch):
    club = source()
    club.active_scraping_source.metadata = {}
    _, shows = await pipeline(monkeypatch, deepcopy(EVENTS), club)
    assert len(shows) == 44 and {s.club_id for s in shows} == {412}
    assert all(s.production_company_id is None for s in shows)


@pytest.mark.asyncio
async def test_partial_routing_and_pagination_cannot_reconcile(monkeypatch):
    scraper, shows = await pipeline(monkeypatch, deepcopy(EVENTS[:1]))
    scraper.fetch_json = AsyncMock(side_effect=[{"events": deepcopy(EVENTS[:1]), "hasMore": True}, None])
    page = await scraper.get_data("https://www.acjokes.com/events?limit=1&offset=0")
    assert page and len(page.event_list) == 1
    # get_data executes inside scrape() in production. Keep its incomplete
    # marker during this synchronous wrapper test without using nested loops.
    errors = list(scraper.venue_router.errors)

    def scrape():
        scraper.venue_router.errors.extend(errors)
        return shows

    monkeypatch.setattr(scraper, "scrape", scrape)
    result = scraper.scrape_with_result()
    result.fetches_ok = 1
    assert result.error and not ScrapingResultProcessor._is_clean_for_reconciliation(result)


@pytest.mark.asyncio
async def test_normalized_address_preserves_date_price_and_availability(monkeypatch):
    from datetime import datetime

    raw = deepcopy(next(e for e in EVENTS if e["location"]["name"] == "Hi Point Pub"))
    raw["location"]["fullAddress"]["city"] = "  ABSECON "
    raw["location"]["fullAddress"]["postalCode"] = "08201-1234"
    raw["registration"] = {"ticketing": {"lowestTicketPrice": {"amount": "25.50"}, "soldOut": True}}
    _, shows = await pipeline(monkeypatch, [raw])
    assert len(shows) == 1
    show = shows[0]
    assert (
        show.date.timestamp()
        == datetime.fromisoformat(raw["scheduling"]["config"]["startDate"].replace("Z", "+00:00")).timestamp()
    )
    assert show.tickets[0].price == 25.5 and show.tickets[0].sold_out
    assert not show.source_performance_id


@pytest.mark.asyncio
async def test_unknown_sibling_and_malformed_record_mark_run_incomplete(monkeypatch):
    unknown = deepcopy(EVENTS[0])
    unknown["location"]["fullAddress"]["streetAddress"]["name"] = "Unreviewed Street"
    scraper, shows = await pipeline(monkeypatch, [deepcopy(EVENTS[0]), unknown, None])
    assert len(shows) == 1 and len(scraper.venue_router.errors) == 2
    errors = list(scraper.venue_router.errors)

    def scrape():
        scraper.venue_router.errors.extend(errors)
        return shows

    monkeypatch.setattr(scraper, "scrape", scrape)
    result = scraper.scrape_with_result()
    result.fetches_ok = 1
    assert result.error and not ScrapingResultProcessor._is_clean_for_reconciliation(result)


@pytest.mark.asyncio
async def test_duplicate_reviewed_signature_is_held(monkeypatch):
    club = source()
    routes = club.source_metadata["wix_venue_routes"]["routes"]
    routes.append(deepcopy(routes[0]))
    routes[-1]["club_id"] = 1234
    scraper, shows = await pipeline(monkeypatch, deepcopy(EVENTS[:1]), club)
    assert not shows and scraper.venue_router.errors


@pytest.mark.asyncio
async def test_existing_room_identity_survives_standard_show_handler(monkeypatch):
    from unittest.mock import MagicMock

    from laughtrack.core.entities.show.handler import ShowHandler

    raw = [
        next(e for e in EVENTS if e["location"]["name"] == name)
        for name in ("Resorts Casino - Starlight Ballroom", "Hi Point Pub", "The Cove Restaurant")
    ]
    _, shows = await pipeline(monkeypatch, deepcopy(raw))
    stored_rooms = ["", "Hi Point Pub", "The Cove Restaurant"]
    rows = [
        dict(id=index, club_id=s.club_id, date=s.date, name=s.name, room=room)
        for index, (s, room) in enumerate(zip(shows, stored_rooms), 1)
    ]
    handler = ShowHandler.__new__(ShowHandler)
    handler.execute_with_cursor = MagicMock(
        side_effect=[[dict(id=9001, name="Hi Point Pub"), dict(id=9002, name="The Cove Restaurant")], rows]
    )
    assert handler._suppress_room_matching_club_name(shows) == 2
    assert handler._collapse_cross_batch_duplicates(shows) == 3
    assert [s.room for s in shows] == stored_rooms


# This fixture uses a rollback-only PostgreSQL TEMP table with no scraping_sources
# table; it exercises the real physical query rather than a destination mock.
from tests.core.entities.club.test_physical_destination_lookup import database as physical_database_fixture

database = physical_database_fixture


@pytest.mark.asyncio
async def test_real_source_less_destination_query(database):
    club = source()
    club.source_metadata["wix_venue_routes"]["routes"] = [
        r for r in club.source_metadata["wix_venue_routes"]["routes"] if r["club_id"] == 9001
    ]
    scraper = WixEventsScraper(club)
    raw = deepcopy(next(e for e in EVENTS if e["location"]["name"] == "Hi Point Pub"))
    scraper.fetch_json = AsyncMock(return_value={"events": [raw], "hasMore": False})
    page = await scraper.get_data("https://www.acjokes.com/events?limit=50&offset=0")
    shows = scraper.transform_data(page, "https://www.acjokes.com")
    assert len(shows) == 1 and shows[0].club_id == 9001
    assert not scraper.venue_router.destinations[9001].scraping_sources
    assert not scraper.venue_router.errors
