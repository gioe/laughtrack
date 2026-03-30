"""
Pipeline smoke test for Bushwick Comedy Club scraper.

Exercises collect_scraping_targets() (Wix auth + URL generation) → get_data()
(Wix events API) by mocking fetch_json for both token and events endpoints.
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
from laughtrack.core.entities.event.bushwick import BushwickEvent
from laughtrack.scrapers.implementations.venues.bushwick.scraper import BushwickComedyClubScraper
from laughtrack.scrapers.implementations.venues.bushwick.data import BushwickEventData
from laughtrack.scrapers.implementations.venues.bushwick.extractor import BushwickEventExtractor


DOMAIN = "https://www.bushwickcomedyclub.com"
SCRAPING_URL = "https://www.bushwickcomedyclub.com"


def _club() -> Club:
    return Club(
        id=99,
        name="Bushwick Comedy Club",
        address="",
        website=DOMAIN,
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _token_response() -> Dict[str, Any]:
    """Wix access-token API response with app intId=24.

    The top-level key ("comedy_events") is arbitrary — WixAccessTokenResponse
    looks up the token by intId, not by key name.
    """
    return {
        "apps": {
            "comedy_events": {"intId": 24, "instance": "fake-token-abc123"}
        }
    }


def _fake_bushwick_event() -> BushwickEvent:
    return BushwickEvent(
        id="bwk-evt-1",
        title="Bushwick Comedy Night",
        description="A great night of comedy",
        scheduling={"startDate": "2026-04-15T20:00:00.000Z", "endDate": "2026-04-15T22:00:00.000Z"},
        location={"address": "Bushwick, Brooklyn, NY"},
        registration_form={},
        created_date="2026-01-01T00:00:00.000Z",
        updated_date="2026-01-01T00:00:00.000Z",
        status="PUBLISHED",
    )


def test_to_show_populates_ticket_url_from_slug():
    """to_show() constructs show_page_url and ticket URL from eventSlug + club.scraping_url."""
    from laughtrack.core.entities.event.bushwick import BushwickEvent

    event = BushwickEvent(
        id="bwk-slug-1",
        title="Slug Test Night",
        description="",
        scheduling={"config": {"startDate": "2026-05-10T00:00:00.000Z"}},
        location={},
        registration_form={"eventSlug": "slug-test-night"},
        created_date="",
        updated_date="",
        status="PUBLISHED",
    )
    club = _club()
    show = event.to_show(club)
    assert show is not None
    expected_url = "https://www.bushwickcomedyclub.com/events/slug-test-night"
    assert show.show_page_url == expected_url, (
        f"show_page_url should be {expected_url!r}, got {show.show_page_url!r}"
    )
    assert len(show.tickets) > 0, "to_show() should produce a ticket when eventSlug is set"
    assert show.tickets[0].purchase_url == expected_url


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_wix_api_url(monkeypatch):
    """collect_scraping_targets() authenticates and returns a Wix events API URL."""
    scraper = BushwickComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, headers: Dict = None) -> Dict:
        return _token_response()

    monkeypatch.setattr(BushwickComedyClubScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, (
        "collect_scraping_targets() returned 0 URLs — "
        "check _ensure_authenticated() and Wix API URL construction"
    )
    assert any("paginated-events" in u for u in urls), (
        f"Expected Wix paginated-events API URL, got: {urls}"
    )


@pytest.mark.asyncio
async def test_get_data_returns_events_from_wix_api(monkeypatch):
    """get_data() returns BushwickEventData when Wix API response contains events."""
    scraper = BushwickComedyClubScraper(_club())
    scraper.access_token = "fake-token-abc123"  # Skip auth flow

    fake_event = _fake_bushwick_event()

    async def fake_fetch_json(self, url: str, headers: Dict = None) -> Dict:
        return {"events": [], "hasMore": False, "total": 0}  # raw Wix JSON; extractor is mocked below

    monkeypatch.setattr(BushwickComedyClubScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(BushwickEventExtractor, "extract_events", staticmethod(lambda r: [fake_event]))

    result = await scraper.get_data(
        f"{DOMAIN}/_api/wix-one-events-server/web/paginated-events/viewer?limit=50&offset=0"
    )

    assert isinstance(result, BushwickEventData), "get_data() did not return BushwickEventData"
    assert len(result.event_list) > 0, "get_data() returned 0 events"
    assert result.event_list[0].title == "Bushwick Comedy Night"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = BushwickComedyClubScraper(_club())
    fake_event = _fake_bushwick_event()

    async def fake_fetch_json(self, url: str, headers: Dict = None) -> Dict:
        if "access-tokens" in url:
            return _token_response()
        return {"events": [], "hasMore": False, "total": 1}

    monkeypatch.setattr(BushwickComedyClubScraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(BushwickEventExtractor, "extract_events", staticmethod(lambda r: [fake_event]))

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls:
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
