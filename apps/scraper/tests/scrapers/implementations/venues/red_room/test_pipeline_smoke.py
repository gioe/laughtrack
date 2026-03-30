"""
Pipeline smoke test for RED ROOM Comedy Club scraper.

Exercises collect_scraping_targets() (Wix auth + URL generation) → get_data()
(Wix events API) by mocking fetch_json for both the token and events endpoints.
Also covers RedRoomEvent.to_show() and the compId / no-categoryId invariants.
"""

import importlib.util
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.red_room import RedRoomEvent
from laughtrack.scrapers.implementations.venues.red_room.scraper import RedRoomComedyClubScraper
from laughtrack.scrapers.implementations.venues.red_room.data import RedRoomPageData
from laughtrack.scrapers.implementations.venues.red_room.extractor import RedRoomEventExtractor


DOMAIN = "https://www.redroomcomedyclub.com"
SCRAPING_URL = "https://www.redroomcomedyclub.com"


def _club(timezone: str = "America/Chicago") -> Club:
    return Club(
        id=200,
        name="RED ROOM Comedy Club",
        address="7442 N. Western Ave",
        website=DOMAIN,
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="60645",
        phone_number="",
        visible=True,
        timezone=timezone,
    )


def _token_response() -> Dict[str, Any]:
    """Wix access-token API response with app intId=24."""
    return {
        "apps": {
            "red_room_events": {"intId": 24, "instance": "fake-token-xyz789"}
        }
    }


def _fake_red_room_event() -> RedRoomEvent:
    return RedRoomEvent(
        id="rr-evt-1",
        title="RED ROOM Comedy Night",
        description="A great night of comedy in Chicago",
        scheduling={
            "config": {"startDate": "2026-04-20T20:00:00.000Z"},
        },
        location={"address": "7442 N. Western Ave, Chicago, IL"},
        registration_form={},
        created_date="2026-01-01T00:00:00.000Z",
        updated_date="2026-01-01T00:00:00.000Z",
        status="PUBLISHED",
    )


# ---------------------------------------------------------------------------
# collect_scraping_targets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_wix_api_url(monkeypatch):
    """collect_scraping_targets() authenticates and returns a Wix events API URL."""
    scraper = RedRoomComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, headers: Dict = None) -> Dict:
        return _token_response()

    monkeypatch.setattr(RedRoomComedyClubScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"
    assert any("paginated-events" in u for u in urls), (
        f"Expected Wix paginated-events URL, got: {urls}"
    )


@pytest.mark.asyncio
async def test_collect_scraping_targets_includes_comp_id(monkeypatch):
    """The generated URL must include compId=comp-j9ny0yyr and no categoryId."""
    scraper = RedRoomComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, headers: Dict = None) -> Dict:
        return _token_response()

    monkeypatch.setattr(RedRoomComedyClubScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) == 1
    url = urls[0]
    assert "compId=comp-j9ny0yyr" in url, f"Expected compId=comp-j9ny0yyr in URL, got: {url}"
    assert "categoryId" not in url, f"categoryId must not appear in URL for RED ROOM: {url}"


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_empty_when_auth_fails(monkeypatch):
    """collect_scraping_targets() returns [] when authentication fails."""
    scraper = RedRoomComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, headers: Dict = None) -> Dict:
        return {"apps": {}}  # No intId=24 app

    monkeypatch.setattr(RedRoomComedyClubScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()
    assert urls == [], f"Expected [] on auth failure, got: {urls}"


# ---------------------------------------------------------------------------
# get_data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_data_returns_events_from_wix_api(monkeypatch):
    """get_data() returns RedRoomPageData when the Wix API response contains events."""
    scraper = RedRoomComedyClubScraper(_club())
    scraper.access_token = "fake-token-xyz789"

    fake_event = _fake_red_room_event()

    async def fake_fetch_json(self, url: str, headers: Dict = None) -> Dict:
        return {"events": [], "hasMore": False, "total": 0}

    monkeypatch.setattr(RedRoomComedyClubScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(
        RedRoomEventExtractor, "extract_events", staticmethod(lambda r: [fake_event])
    )

    result = await scraper.get_data(
        f"{DOMAIN}/_api/wix-one-events-server/web/paginated-events/viewer?compId=comp-j9ny0yyr"
    )

    assert isinstance(result, RedRoomPageData), "get_data() did not return RedRoomPageData"
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "RED ROOM Comedy Night"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_api_returns_empty(monkeypatch):
    """get_data() returns None when the API returns no events."""
    scraper = RedRoomComedyClubScraper(_club())
    scraper.access_token = "fake-token-xyz789"

    async def fake_fetch_json(self, url: str, headers: Dict = None) -> Dict:
        return {"events": [], "hasMore": False, "total": 0}

    monkeypatch.setattr(RedRoomComedyClubScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(
        RedRoomEventExtractor, "extract_events", staticmethod(lambda r: [])
    )

    result = await scraper.get_data(
        f"{DOMAIN}/_api/wix-one-events-server/web/paginated-events/viewer?compId=comp-j9ny0yyr"
    )
    assert result is None, "get_data() should return None when no events are extracted"


# ---------------------------------------------------------------------------
# RedRoomEvent.to_show — timezone handling
# ---------------------------------------------------------------------------

def test_to_show_no_slug_returns_show_without_ticket():
    """to_show() with no eventSlug produces a Show with empty show_page_url and no tickets."""
    event = RedRoomEvent(
        id="rr-no-slug",
        title="No Slug Show",
        description="",
        scheduling={"config": {"startDate": "2026-05-10T00:00:00.000Z"}},
        location={},
        registration_form={},
        created_date="",
        updated_date="",
        status="PUBLISHED",
    )
    club = _club()
    show = event.to_show(club)
    assert show is not None
    assert show.show_page_url == ""
    assert show.tickets == []


def test_to_show_uses_club_timezone():
    """to_show() uses club.timezone (America/Chicago) for the event start time."""
    event = RedRoomEvent(
        id="rr-1",
        title="Friday Night Comedy",
        description="",
        scheduling={"config": {"startDate": "2026-05-01T01:00:00.000Z"}},
        location={},
        registration_form={},
        created_date="",
        updated_date="",
        status="PUBLISHED",
    )
    club = _club(timezone="America/Chicago")
    show = event.to_show(club)
    assert show is not None
    # 2026-05-01T01:00:00 UTC = 2026-04-30T20:00:00 CDT (UTC-5)
    assert show.date.hour == 20
    assert show.date.month == 4
    assert show.date.day == 30


def test_to_show_populates_ticket_url_from_slug():
    """to_show() constructs show_page_url and ticket URL from eventSlug + club.scraping_url."""
    event = RedRoomEvent(
        id="rr-3",
        title="Slug Test Show",
        description="",
        scheduling={"config": {"startDate": "2026-05-10T00:00:00.000Z"}},
        location={},
        registration_form={"eventSlug": "slug-test-show"},
        created_date="",
        updated_date="",
        status="PUBLISHED",
    )
    club = _club()
    show = event.to_show(club)
    assert show is not None
    expected_url = "https://www.redroomcomedyclub.com/events/slug-test-show"
    assert show.show_page_url == expected_url, (
        f"show_page_url should be {expected_url!r}, got {show.show_page_url!r}"
    )
    assert len(show.tickets) > 0, "to_show() should produce a ticket when eventSlug is set"
    assert show.tickets[0].purchase_url == expected_url


def test_to_show_falls_back_to_utc_when_timezone_missing():
    """to_show() falls back to UTC when club.timezone is None or empty."""
    event = RedRoomEvent(
        id="rr-2",
        title="Late Night Show",
        description="",
        scheduling={"config": {"startDate": "2026-06-15T02:00:00.000Z"}},
        location={},
        registration_form={},
        created_date="",
        updated_date="",
        status="PUBLISHED",
    )
    club = _club(timezone=None)
    show = event.to_show(club)
    assert show is not None
    # UTC fallback: 2026-06-15T02:00:00 UTC
    assert show.date.hour == 2
    assert show.date.month == 6


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_data_follows_has_more_pagination(monkeypatch):
    """get_data() follows hasMore pagination and accumulates events across all pages."""
    scraper = RedRoomComedyClubScraper(_club())
    scraper.access_token = "fake-token-xyz789"

    call_count = {"n": 0}

    async def fake_fetch_json(self, url: str, headers: Dict = None) -> Dict:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {"events": [], "hasMore": True, "total": 2}
        return {"events": [], "hasMore": False, "total": 2}

    page_events = [
        [RedRoomEvent(id="rr-p1", title="Page 1 Show", description="", scheduling={"config": {"startDate": "2026-04-20T20:00:00.000Z"}}, location={}, registration_form={}, created_date="", updated_date="", status="PUBLISHED")],
        [RedRoomEvent(id="rr-p2", title="Page 2 Show", description="", scheduling={"config": {"startDate": "2026-04-21T20:00:00.000Z"}}, location={}, registration_form={}, created_date="", updated_date="", status="PUBLISHED")],
    ]
    extract_call = {"n": 0}

    def fake_extract(r):
        idx = extract_call["n"]
        extract_call["n"] += 1
        return page_events[idx] if idx < len(page_events) else []

    monkeypatch.setattr(RedRoomComedyClubScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(RedRoomEventExtractor, "extract_events", staticmethod(fake_extract))

    result = await scraper.get_data(
        f"{DOMAIN}/_api/wix-one-events-server/web/paginated-events/viewer?compId=comp-j9ny0yyr&limit=50&offset=0"
    )

    assert result is not None
    assert len(result.event_list) == 2, (
        f"Expected 2 events (one per page), got {len(result.event_list)}"
    )
    assert call_count["n"] == 2, f"Expected 2 fetch_json calls, got {call_count['n']}"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = RedRoomComedyClubScraper(_club())
    fake_event = _fake_red_room_event()

    async def fake_fetch_json(self, url: str, headers: Dict = None) -> Dict:
        if "access-tokens" in url:
            return _token_response()
        return {"events": [], "hasMore": False, "total": 1}

    monkeypatch.setattr(RedRoomComedyClubScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(
        RedRoomEventExtractor, "extract_events", staticmethod(lambda r: [fake_event])
    )

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
    assert all_events[0].title == "RED ROOM Comedy Night"
