"""Pipeline smoke tests for the Flop House JSON scraper."""

from datetime import datetime, timedelta, timezone

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.implementations.api.flop_house_json.extractor import (
    FlopHouseJsonExtractor,
)
from laughtrack.scrapers.implementations.api.flop_house_json.scraper import (
    FlopHouseJsonScraper,
)


BASE_URL = "https://www.flophousecomedy.com"


def _future_ms(days: int = 7) -> int:
    return int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp() * 1000)


def _past_ms(days: int = 7) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)


def _venues():
    return [
        {
            "id": "williamsburg",
            "name": "Williamsburg",
            "address": "362 Grand Street, Brooklyn, NY 11211",
            "timezone": "America/New_York",
        }
    ]


def _event_groups(start_ms: int | None = None):
    start = start_ms if start_ms is not None else _future_ms()
    return [
        {
            "show": {
                "id": "show-1",
                "title": "If Found Please Call",
                "description": "A stand-up comedy showcase.",
            },
            "events": [
                {
                    "id": "event-1",
                    "venueId": "williamsburg",
                    "showId": "show-1",
                    "startTime": start,
                    "endTime": start + 5400000,
                    "eventbriteId": "1992439062872",
                }
            ],
        }
    ]


def _club() -> Club:
    club = Club(
        id=99,
        name="Flop House Comedy Club",
        address="362 Grand Street, Brooklyn, NY 11211, USA",
        website=BASE_URL,
        popularity=0,
        zip_code="11211",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="flop_house_json",
        source_url=BASE_URL,
        external_id=None,
        metadata={},
    )
    club.active_scraping_source = source
    club.scraping_sources = [source]
    return club


def test_extract_events_combines_show_event_and_venue_fields():
    events = FlopHouseJsonExtractor.extract_events(
        _event_groups(),
        venues_by_id={"williamsburg": _venues()[0]},
    )

    assert len(events) == 1
    event = events[0]
    assert event.title == "If Found Please Call"
    assert event.description == "A stand-up comedy showcase."
    assert event.venue_name == "Williamsburg"
    assert event.show_page_url == "https://www.eventbrite.com/e/tickets-1992439062872"


def test_extract_events_skips_past_or_malformed_events():
    events = FlopHouseJsonExtractor.extract_events(
        [
            *_event_groups(start_ms=_past_ms()),
            {"show": {"title": "Missing Eventbrite"}, "events": [{"startTime": _future_ms()}]},
            *_event_groups(start_ms=_future_ms()),
        ],
        venues_by_id={"williamsburg": _venues()[0]},
    )

    assert [event.title for event in events] == ["If Found Please Call"]


def test_event_to_show_uses_eventbrite_ticket_url_and_room():
    event = FlopHouseJsonExtractor.extract_events(
        _event_groups(),
        venues_by_id={"williamsburg": _venues()[0]},
    )[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "If Found Please Call"
    assert show.show_page_url == event.show_page_url
    assert show.tickets[0].purchase_url == event.show_page_url
    assert show.room == "Williamsburg"


@pytest.mark.asyncio
async def test_collect_scraping_targets_fetches_venue_event_urls(monkeypatch):
    scraper = FlopHouseJsonScraper(_club())

    async def fake_fetch_json(url: str, **kwargs):
        assert url == f"{BASE_URL}/venues.json"
        return _venues()

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    assert await scraper.collect_scraping_targets() == [f"{BASE_URL}/venues/williamsburg_events.json"]


@pytest.mark.asyncio
async def test_get_data_fetches_event_groups(monkeypatch):
    scraper = FlopHouseJsonScraper(_club())
    scraper.venues_by_id = {"williamsburg": _venues()[0]}

    async def fake_fetch_json(url: str, **kwargs):
        return _event_groups()

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(f"{BASE_URL}/venues/williamsburg_events.json")

    assert isinstance(result, EventListContainer)
    assert len(result.event_list) == 1
