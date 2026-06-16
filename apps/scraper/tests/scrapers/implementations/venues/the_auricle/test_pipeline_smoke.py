"""
Pipeline smoke tests for TheAuricleScraper and TheAuricleEvent.

Exercises get_data() against the mocked SociableKit/accentapi JSON feed (trimmed
real fixture) and unit-tests the extractor's comedy filtering, date parsing, and
the TheAuricleEvent.to_show() transformation path.
"""

import json
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.the_auricle import TheAuricleEvent
from laughtrack.scrapers.implementations.venues.the_auricle.scraper import TheAuricleScraper
from laughtrack.scrapers.implementations.venues.the_auricle.data import TheAuriclePageData
from laughtrack.scrapers.implementations.venues.the_auricle.extractor import TheAuricleEventExtractor

_FEED_URL = "https://data.accentapi.com/feed/55840.json"
_FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "accentapi_feed.json").read_text())


def _club() -> Club:
    c = Club(
        id=999, name="The Auricle - Venue & Bar", address="201 Cleveland Ave NW",
        website="https://www.theauricle.net", popularity=0, zip_code="44702",
        phone_number="", visible=True, timezone="America/New_York",
    )
    c.active_scraping_source = ScrapingSource(
        id=1, club_id=c.id, platform="custom", scraper_key="the_auricle",
        source_url=_FEED_URL, external_id=None,
    )
    c.scraping_sources = [c.active_scraping_source]
    c.scraping_url = _FEED_URL
    return c


# --------------------------------------------------------------------------- #
# Registry + targets
# --------------------------------------------------------------------------- #


def test_scraper_key_in_registry():
    from laughtrack.app.registry import SCRAPERS

    assert SCRAPERS.get("the_auricle") is TheAuricleScraper


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_feed_url():
    targets = await TheAuricleScraper(_club()).collect_scraping_targets()
    assert targets == [_FEED_URL]


# --------------------------------------------------------------------------- #
# get_data()
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_data_returns_only_comedy_events(monkeypatch):
    """get_data() keeps the Comedy Open Mic and drops music/variety events."""
    async def fake_fetch_json(self, url, *a, **k):
        return _FIXTURE

    monkeypatch.setattr(TheAuricleScraper, "fetch_json", fake_fetch_json)
    result = await TheAuricleScraper(_club()).get_data(_FEED_URL)

    assert isinstance(result, TheAuriclePageData)
    names = [e.name for e in result.event_list]
    assert names == ["Comedy Open Mic"]
    assert not any("Goth Dammit" in n or "Vinyl" in n for n in names)


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_feed(monkeypatch):
    async def fake_fetch_json(self, url, *a, **k):
        return {"events": []}

    monkeypatch.setattr(TheAuricleScraper, "fetch_json", fake_fetch_json)
    assert await TheAuricleScraper(_club()).get_data(_FEED_URL) is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_falsy_payload(monkeypatch):
    async def fake_fetch_json(self, url, *a, **k):
        return None

    monkeypatch.setattr(TheAuricleScraper, "fetch_json", fake_fetch_json)
    assert await TheAuricleScraper(_club()).get_data(_FEED_URL) is None


# --------------------------------------------------------------------------- #
# Extractor unit tests
# --------------------------------------------------------------------------- #


def test_extract_filters_non_comedy():
    events = TheAuricleEventExtractor.extract_shows(_FIXTURE)
    assert {e.name for e in events} == {"Comedy Open Mic"}


def test_extract_parses_local_datetime_and_url():
    mic = TheAuricleEventExtractor.extract_shows(_FIXTURE)[0]
    assert mic.dt_str == "2026-06-29 20:00:00"  # from start_date_raw + "8:00 pm"
    assert mic.url.startswith("https://www.facebook.com/events/")


def test_extract_open_mic_without_comedy_term_is_excluded():
    """A bare 'Open Mic' (no comedy term) must not be treated as comedy."""
    payload = {"events": [
        {"name": "Open Mic Night", "start_date_raw": "2026-07-01", "start_time": "8:00 pm"},
    ]}
    assert TheAuricleEventExtractor.extract_shows(payload) == []


def test_extract_handles_non_dict_payload():
    assert TheAuricleEventExtractor.extract_shows([]) == []
    assert TheAuricleEventExtractor.extract_shows(None) == []


# --------------------------------------------------------------------------- #
# to_show()
# --------------------------------------------------------------------------- #


def test_to_show_builds_localized_show_with_fallback_ticket():
    event = TheAuricleEvent(
        name="Comedy Open Mic", dt_str="2026-06-29 20:00:00",
        url="https://www.facebook.com/events/123", price=None,
    )
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Comedy Open Mic"
    assert show.date.month == 6 and show.date.day == 29 and show.date.hour == 20
    assert show.date.utcoffset() is not None  # localized to America/New_York
    assert len(show.tickets) == 1
    assert show.tickets[0].price is None
    assert show.tickets[0].purchase_url == "https://www.facebook.com/events/123"


def test_to_show_parses_price_when_present():
    event = TheAuricleEvent(
        name="Comedy Night", dt_str="2026-07-04 20:00:00",
        url="https://example.com/tix", price=10.0,
    )
    show = event.to_show(_club())
    assert show.tickets[0].price == 10.0


def test_to_show_returns_none_on_bad_date():
    event = TheAuricleEvent(name="X", dt_str="nope", url="https://x", price=None)
    assert event.to_show(_club()) is None
