"""Pipeline smoke tests for the generic FullCalendar JSON feed scraper."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

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
