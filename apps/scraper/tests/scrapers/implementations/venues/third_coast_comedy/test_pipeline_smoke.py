"""
Pipeline smoke tests for VivenuScraper and VivenuEvent.

Exercises get_data() against mocked Vivenu seller page HTML containing
__NEXT_DATA__ JSON, and unit-tests the VivenuEvent.to_show() transformation path.
"""

import json

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.vivenu import VivenuEvent
from laughtrack.scrapers.implementations.venues.third_coast_comedy.scraper import VivenuScraper
from laughtrack.scrapers.implementations.venues.third_coast_comedy.data import VivenuPageData
from laughtrack.scrapers.implementations.venues.third_coast_comedy.extractor import VivenuExtractor

_TICKET_BASE = "https://tickets.thirdcoastcomedy.club"

# Future timestamp: 2026-04-01T02:00:00.000Z
_FUTURE_START = "2026-04-01T02:00:00.000Z"
# Past timestamp: 2020-01-01T00:00:00.000Z
_PAST_START = "2020-01-01T00:00:00.000Z"


def _club() -> Club:
    return Club(
        id=200,
        name="Third Coast Comedy Club",
        address="1310 Clinton Street, Suite 121",
        website="https://www.thirdcoastcomedy.club",
        scraping_url="https://tickets.thirdcoastcomedy.club/",
        popularity=0,
        zip_code="37203",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _raw_event(
    event_id: str = "abc123",
    name: str = "Comedy Night",
    start: str = _FUTURE_START,
    event_url: str = "comedy-night-abc123",
    tz: str = "America/Chicago",
) -> dict:
    return {
        "_id": event_id,
        "url": event_url,
        "name": name,
        "start": start,
        "end": "2026-04-01T04:00:00.000Z",
        "sellerId": "66a3fea4b429c081d0c729df",
        "timezone": tz,
        "saleStatus": "onSale",
        "eventType": "SINGLE",
        "childEvents": [],
    }


def _make_html(events: list) -> str:
    """Wrap a list of raw event dicts in a minimal Vivenu __NEXT_DATA__ HTML page."""
    next_data = {
        "props": {
            "pageProps": {
                "sellerPage": {
                    "events": events,
                }
            }
        }
    }
    return (
        '<html><head>'
        f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script>'
        '</head><body></body></html>'
    )


# ---------------------------------------------------------------------------
# VivenuExtractor tests
# ---------------------------------------------------------------------------


def test_extract_events_returns_upcoming_events():
    """extract_events() returns upcoming events from __NEXT_DATA__ HTML."""
    html = _make_html([
        _raw_event(event_id="1", name="Show A"),
        _raw_event(event_id="2", name="Show B"),
    ])
    events = VivenuExtractor.extract_events(html, _TICKET_BASE)

    assert len(events) == 2
    names = {e.name for e in events}
    assert "Show A" in names
    assert "Show B" in names


def test_extract_events_skips_past_events():
    """extract_events() skips events whose start time is in the past."""
    html = _make_html([
        _raw_event(event_id="1", name="Past Show", start=_PAST_START),
        _raw_event(event_id="2", name="Future Show", start=_FUTURE_START),
    ])
    events = VivenuExtractor.extract_events(html, _TICKET_BASE)

    assert len(events) == 1
    assert events[0].name == "Future Show"


def test_extract_events_skips_events_with_no_name():
    """extract_events() skips events with an empty name."""
    html = _make_html([
        {**_raw_event(event_id="1"), "name": ""},
        _raw_event(event_id="2", name="Has Name"),
    ])
    events = VivenuExtractor.extract_events(html, _TICKET_BASE)

    assert len(events) == 1
    assert events[0].name == "Has Name"


def test_extract_events_skips_events_with_no_id():
    """extract_events() skips events with a missing _id."""
    no_id = {**_raw_event(event_id="1"), "_id": ""}
    html = _make_html([no_id, _raw_event(event_id="2", name="Has ID")])
    events = VivenuExtractor.extract_events(html, _TICKET_BASE)

    assert len(events) == 1
    assert events[0].name == "Has ID"


def test_extract_events_returns_empty_for_no_next_data():
    """extract_events() returns empty list when __NEXT_DATA__ is absent."""
    events = VivenuExtractor.extract_events("<html></html>", _TICKET_BASE)
    assert events == []


def test_extract_events_returns_empty_for_empty_events_list():
    """extract_events() returns empty list when sellerPage.events is empty."""
    html = _make_html([])
    events = VivenuExtractor.extract_events(html, _TICKET_BASE)
    assert events == []


def test_extract_events_sets_ticket_base_url():
    """extract_events() stores ticket_base_url on each extracted event."""
    html = _make_html([_raw_event(event_id="1", event_url="comedy-night-abc123")])
    events = VivenuExtractor.extract_events(html, _TICKET_BASE)

    assert len(events) == 1
    assert events[0].ticket_base_url == _TICKET_BASE


# ---------------------------------------------------------------------------
# VivenuEvent.to_show() tests
# ---------------------------------------------------------------------------


def _make_event(
    event_id: str = "abc123",
    name: str = "Comedy Night",
    start_utc: str = _FUTURE_START,
    event_url: str = "comedy-night-abc123",
    tz: str = "America/Chicago",
    ticket_base_url: str = _TICKET_BASE,
) -> VivenuEvent:
    return VivenuEvent(
        event_id=event_id,
        name=name,
        start_utc=start_utc,
        event_url=event_url,
        tz=tz,
        ticket_base_url=ticket_base_url,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the correct name."""
    event = _make_event(name="The Third Coast Comedy Show")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "The Third Coast Comedy Show"


def test_to_show_parses_utc_timestamp_in_chicago_timezone():
    """to_show() correctly converts a UTC ISO timestamp to Chicago local time.

    2026-04-01T02:00:00.000Z = 2026-03-31T21:00:00 CDT (UTC-5)
    """
    event = _make_event(start_utc="2026-04-01T02:00:00.000Z", tz="America/Chicago")
    show = event.to_show(_club())

    assert show is not None
    assert show.date.year == 2026
    assert show.date.month == 3
    assert show.date.day == 31
    assert show.date.hour == 21
    assert show.date.minute == 0


def test_to_show_builds_correct_ticket_url():
    """to_show() builds ticket URL from ticket_base_url and event slug."""
    event = _make_event(event_url="comedy-night-abc123")
    show = event.to_show(_club())

    assert show is not None
    assert show.show_page_url == f"{_TICKET_BASE}/event/comedy-night-abc123"
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == f"{_TICKET_BASE}/event/comedy-night-abc123"


def test_to_show_returns_none_for_invalid_timezone():
    """to_show() returns None when the timezone string is invalid."""
    event = _make_event(tz="Not/A/Timezone")
    show = event.to_show(_club())

    assert show is None


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_scraping_url():
    """collect_scraping_targets() returns exactly the club's scraping_url."""
    scraper = VivenuScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 1
    assert targets[0] == "https://tickets.thirdcoastcomedy.club/"


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() fetches the seller page and returns VivenuPageData with events."""
    scraper = VivenuScraper(_club())
    html = _make_html([
        _raw_event(event_id="1", name="Show A"),
        _raw_event(event_id="2", name="Show B"),
    ])

    async def fake_fetch_html_bare(self, url: str):
        return html

    monkeypatch.setattr(VivenuScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data("https://tickets.thirdcoastcomedy.club/")

    assert isinstance(result, VivenuPageData)
    assert len(result.event_list) == 2
    names = {e.name for e in result.event_list}
    assert "Show A" in names
    assert "Show B" in names


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_events(monkeypatch):
    """get_data() returns None when no upcoming events are found."""
    scraper = VivenuScraper(_club())
    html = _make_html([_raw_event(event_id="1", start=_PAST_START)])

    async def fake_fetch_html_bare(self, url: str):
        return html

    monkeypatch.setattr(VivenuScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data("https://tickets.thirdcoastcomedy.club/")
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_null_response(monkeypatch):
    """get_data() returns None when fetch_html_bare returns empty string."""
    scraper = VivenuScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        return ""

    monkeypatch.setattr(VivenuScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: __import__("asyncio").sleep(0))

    result = await scraper.get_data("https://tickets.thirdcoastcomedy.club/")
    assert result is None


# ---------------------------------------------------------------------------
# Full pipeline smoke test
# ---------------------------------------------------------------------------


def test_transformation_pipeline_produces_shows():
    """Full pipeline: VivenuPageData → transformation_pipeline → Show objects.

    Guards against silent failures in VivenuEventTransformer.can_transform() —
    if generic parameter type matching fails, transform() returns 0 Shows with
    no error. The to_show() unit tests cover conversion logic but do not exercise
    the pipeline dispatch path.
    """
    scraper = VivenuScraper(_club())
    page_data = VivenuPageData(event_list=[_make_event(name="Comedy Night")])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows — "
        "check VivenuEventTransformer and Club timezone"
    )
    assert shows[0].name == "Comedy Night"
