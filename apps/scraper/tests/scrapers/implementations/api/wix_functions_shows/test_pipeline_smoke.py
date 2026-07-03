"""Pipeline smoke tests for the generic Wix/Velo _functions/shows scraper."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.implementations.api.wix_functions_shows.extractor import (
    WixFunctionsShowsExtractor,
)
from laughtrack.scrapers.implementations.api.wix_functions_shows.scraper import (
    WixFunctionsShowsScraper,
)


FEED_URL = "https://uppereastsidecomedyclub.com/_functions/shows"


def _future_local(days=7) -> str:
    return (datetime.now() + timedelta(days=days)).replace(microsecond=0).isoformat()


def _past_utc(days=1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _raw_show(**overrides):
    raw = {
        "eid": "1992321227423",
        "title": "FUNNY PEOPLE Live | Stand-Up Comedy on the Upper East Side",
        "start_utc": "2099-07-04T00:00:00Z",
        "start_local": _future_local(),
        "end_local": "2099-07-03T21:30:00",
        "timezone": "America/New_York",
        "ticket_url": "https://www.eventbrite.com/e/funny-people-live-tickets-1992321227423",
        "price_from": 5,
        "lineup_text": "Featuring Raj Suresh (Don&#39;t Tell Comedy)",
    }
    raw.update(overrides)
    return raw


def _club() -> Club:
    club = Club(
        id=3566,
        name="Upper East Side Comedy Club",
        address="206 E 67th St, New York, NY 10065, USA",
        website="https://www.uppereastsidecomedyclub.com/",
        popularity=0,
        zip_code="10065",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="wix_functions_shows",
        source_url=FEED_URL,
        external_id=None,
        metadata={},
    )
    club.active_scraping_source = source
    club.scraping_sources = [source]
    return club


def test_extract_events_parses_shows_response():
    events = WixFunctionsShowsExtractor.extract_events(
        {"shows": [_raw_show()]},
        timezone_name="America/New_York",
    )

    assert len(events) == 1
    event = events[0]
    assert event.title == "FUNNY PEOPLE Live | Stand-Up Comedy on the Upper East Side"
    assert event.ticket_url == "https://www.eventbrite.com/e/funny-people-live-tickets-1992321227423"
    assert event.price_from == 5
    assert event.lineup_text == "Featuring Raj Suresh (Don't Tell Comedy)"


def test_extract_events_skips_past_and_invalid_rows():
    events = WixFunctionsShowsExtractor.extract_events(
        {
            "shows": [
                _raw_show(title="Past Show", start_local=None, start_utc=_past_utc()),
                _raw_show(title="", ticket_url="https://example.com/missing-title"),
                _raw_show(title="Future Show"),
            ]
        },
        timezone_name="America/New_York",
    )

    assert [event.title for event in events] == ["Future Show"]


def test_extract_events_localizes_naive_start_to_club_timezone():
    events = WixFunctionsShowsExtractor.extract_events(
        {"shows": [_raw_show(start_local="2026-07-10T20:00:00")]},
        timezone_name="America/New_York",
    )

    assert len(events) == 1
    assert events[0].start == datetime(2026, 7, 10, 20, 0, tzinfo=ZoneInfo("America/New_York"))


def test_event_to_show_uses_eventbrite_ticket_url_and_price():
    event = WixFunctionsShowsExtractor.extract_events({"shows": [_raw_show()]}, "America/New_York")[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "FUNNY PEOPLE Live | Stand-Up Comedy on the Upper East Side"
    assert show.show_page_url == "https://www.eventbrite.com/e/funny-people-live-tickets-1992321227423"
    assert show.tickets[0].purchase_url == show.show_page_url
    assert show.tickets[0].price == 5
    assert show.description == "Featuring Raj Suresh (Don't Tell Comedy)"


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_feed_url():
    scraper = WixFunctionsShowsScraper(_club())

    assert await scraper.collect_scraping_targets() == [FEED_URL]


@pytest.mark.asyncio
async def test_get_data_fetches_endpoint_and_returns_page_data(monkeypatch):
    scraper = WixFunctionsShowsScraper(_club())

    async def fake_fetch_json(url: str, **kwargs):
        return {"shows": [_raw_show(), _raw_show(title="Past Show", start_local=None, start_utc=_past_utc())]}

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(FEED_URL)

    assert isinstance(result, EventListContainer)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "FUNNY PEOPLE Live | Stand-Up Comedy on the Upper East Side"
