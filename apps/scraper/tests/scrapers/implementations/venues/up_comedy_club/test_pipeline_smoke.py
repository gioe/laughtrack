"""
Pipeline smoke test for UP Comedy Club scraper.

Covers:
  - collect_scraping_targets(): GraphQL call → filters for UP Comedy Club shows
    → returns entityResolver URLs
  - get_data(): entity resolver response → decodes base64 patronticketData
    → returns UPComedyClubPageData with one event per instance
  - UPComedyClubEvent.to_show(): timezone-aware datetime conversion
  - Error paths: GraphQL failure, missing patronticketData, no instances
"""

import base64
import importlib.util
import json
import urllib.parse
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.up_comedy_club import UPComedyClubEvent
from laughtrack.scrapers.implementations.venues.up_comedy_club.scraper import UPComedyClubScraper
from laughtrack.scrapers.implementations.venues.up_comedy_club.data import UPComedyClubPageData

SCRAPING_URL = "https://www.secondcity.com/shows/chicago/"


def _club(timezone: str = "America/Chicago") -> Club:
    return Club(
        id=999,
        name="UP Comedy Club",
        address="230 W North Ave",
        website="https://www.secondcity.com/shows/chicago/",
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="60610",
        phone_number="",
        visible=True,
        timezone=timezone,
    )


def _graphql_response(include_up_show: bool = True) -> Dict[str, Any]:
    """Fake GraphQL response listing Chicago shows."""
    nodes = [
        {
            "title": "The Best of The Second City: Chicago Style",
            "uri": "/shows/chicago/the-best-of-the-second-city-chicago-style-chi",
            "showAttributes": {
                "venue": [{"name": "UP Comedy Club - Chicago"}],
            },
        },
        {
            "title": "The Second City Mainstage 114th Revue",
            "uri": "/shows/chicago/the-second-city-mainstage-114th-revue-chi",
            "showAttributes": {
                "venue": [{"name": "Chicago Mainstage"}],
            },
        },
    ]
    if not include_up_show:
        nodes = [nodes[1]]
    return {"data": {"shows": {"nodes": nodes}}}


def _make_patron_ticket_data(instances: list) -> str:
    """Return a base64-encoded patronticketData string with the given instances."""
    payload = {
        "type": "Tickets",
        "name": "The Best of The Second City: Chicago Style",
        "id": "a0S1R00000CjhqUAB",
        "instances": instances,
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _make_instance(
    date_utc: str = "2026-05-29T00:00:00Z",
    ticket_url: str = "https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000009NIIP2A4",
    sold_out: int = 0,
    title: str = "The Best of The Second City: Chicago Style",
) -> Dict[str, Any]:
    return {
        "venueId": "a0T36000005QkwLEAS",
        "soldOut": sold_out,
        "seatingType": "General Admission",
        "purchaseUrl": ticket_url,
        "name": "Thursday, May 28, 2026, at 7:00 PM",
        "id": "a0FTP000009NIIP2A4",
        "formattedDates": {"ISO8601": date_utc},
        "eventName": title,
        "eventId": "a0S1R00000Cjhq8UAB",
        "detail": "",
        "custom": {},
        "contentFormat": "Standard",
        "allocations": [],
    }


def _entity_resolver_response(instances: list) -> Dict[str, Any]:
    """Fake entityResolver response with encoded patronticketData."""
    return {
        "patronticketData": {
            "patronticketData": _make_patron_ticket_data(instances),
        }
    }


# ---------------------------------------------------------------------------
# collect_scraping_targets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_up_comedy_club_urls(monkeypatch):
    """collect_scraping_targets() calls GraphQL and returns entityResolver URL for UP shows."""
    scraper = UPComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> Dict:
        return _graphql_response(include_up_show=True)

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) == 1, f"Expected 1 UP Comedy Club show URL, got: {urls}"
    assert "entityResolver" in urls[0], "Expected entityResolver URL"
    assert "the-best-of-the-second-city-chicago-style-chi" in urls[0]


@pytest.mark.asyncio
async def test_collect_scraping_targets_excludes_non_up_shows(monkeypatch):
    """Mainstage-only shows are excluded from scraping targets."""
    scraper = UPComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> Dict:
        return _graphql_response(include_up_show=False)

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()
    assert urls == [], f"Expected no URLs when no UP Comedy Club shows, got: {urls}"


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_empty_on_graphql_failure(monkeypatch):
    """collect_scraping_targets() returns [] when the GraphQL request fails."""
    scraper = UPComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> Optional[Dict]:
        return None

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()
    assert urls == [], "Expected [] when GraphQL returns None"


@pytest.mark.asyncio
async def test_collect_scraping_targets_includes_multi_venue_show(monkeypatch):
    """Shows whose venue list includes UP Comedy Club alongside other venues are included."""
    scraper = UPComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> Dict:
        return {
            "data": {
                "shows": {
                    "nodes": [
                        {
                            "title": "Best of The Second City",
                            "uri": "/shows/chicago/best-of-the-second-city-chi",
                            "showAttributes": {
                                "venue": [
                                    {"name": "Chicago Mainstage"},
                                    {"name": "UP Comedy Club - Chicago"},
                                ],
                            },
                        }
                    ]
                }
            }
        }

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) == 1, "Multi-venue show with UP Comedy Club must be included"
    assert "best-of-the-second-city-chi" in urls[0]


# ---------------------------------------------------------------------------
# get_data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() decodes patronticketData and returns one event per instance."""
    scraper = UPComedyClubScraper(_club())
    instances = [
        _make_instance("2026-05-29T00:00:00Z"),
        _make_instance("2026-05-30T01:00:00Z", ticket_url="https://secondcityus.my.salesforce-sites.com/ticket/#/instances/INST2"),
    ]

    async def fake_fetch_json(self, url: str, **kwargs) -> Dict:
        return _entity_resolver_response(instances)

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://www.secondcity.com/api/entityResolver?uri=%2Fshows%2Fchicago%2Ftest-show-chi&isPreview=false")

    assert isinstance(result, UPComedyClubPageData), "get_data() did not return UPComedyClubPageData"
    assert len(result.event_list) == 2, f"Expected 2 events, got {len(result.event_list)}"
    assert result.event_list[0].title == "The Best of The Second City: Chicago Style"
    assert "salesforce-sites.com" in result.event_list[0].ticket_url


@pytest.mark.asyncio
async def test_get_data_returns_none_when_all_instances_malformed(monkeypatch):
    """get_data() returns None when every instance is missing required fields."""
    scraper = UPComedyClubScraper(_club())
    malformed = [
        {"soldOut": 0, "formattedDates": {"ISO8601": ""}, "purchaseUrl": "", "eventName": ""},
        {"soldOut": 0, "formattedDates": {}, "purchaseUrl": "https://example.com", "eventName": ""},
    ]

    async def fake_fetch_json(self, url: str, **kwargs) -> Dict:
        return _entity_resolver_response(malformed)

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://www.secondcity.com/api/entityResolver?uri=%2Fshows%2Fchicago%2Ftest&isPreview=false")
    assert result is None, "Expected None when all instances are malformed"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_instances(monkeypatch):
    """get_data() returns None when patronticketData has an empty instances list."""
    scraper = UPComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> Dict:
        return _entity_resolver_response([])

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://www.secondcity.com/api/entityResolver?uri=%2Fshows%2Fchicago%2Ftest&isPreview=false")
    assert result is None, "Expected None when instances list is empty"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_patron_ticket_data(monkeypatch):
    """get_data() returns None when patronticketData is absent from the response."""
    scraper = UPComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> Dict:
        return {"title": "Some Show", "uri": "/shows/chicago/some-show"}

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://www.secondcity.com/api/entityResolver?uri=%2Fshows%2Fchicago%2Fsome-show&isPreview=false")
    assert result is None, "Expected None when patronticketData is absent"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_api_returns_none(monkeypatch):
    """get_data() returns None when the entity resolver request fails."""
    scraper = UPComedyClubScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> Optional[Dict]:
        return None

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://www.secondcity.com/api/entityResolver?uri=%2Fshows%2Fchicago%2Ftest&isPreview=false")
    assert result is None, "Expected None when API returns None"


# ---------------------------------------------------------------------------
# UPComedyClubEvent.to_show — timezone handling
# ---------------------------------------------------------------------------

def test_to_show_converts_utc_to_club_timezone():
    """to_show() correctly converts UTC datetime to the club timezone."""
    event = UPComedyClubEvent(
        title="The Best of The Second City: Chicago Style",
        date_utc="2026-05-29T00:00:00Z",   # midnight UTC = 7 PM CDT (UTC-5)
        ticket_url="https://secondcityus.my.salesforce-sites.com/ticket/#/instances/abc123",
        sold_out=False,
    )
    club = _club(timezone="America/Chicago")
    show = event.to_show(club)

    assert show is not None
    assert show.name == "The Best of The Second City: Chicago Style"
    # 2026-05-29 00:00 UTC in CDT (UTC-5) = 2026-05-28 19:00
    assert show.date.month == 5
    assert show.date.day == 28
    assert show.date.hour == 19


def test_to_show_falls_back_to_utc_when_timezone_is_none():
    """to_show() uses UTC when club.timezone is None."""
    event = UPComedyClubEvent(
        title="Best of The Second City",
        date_utc="2026-06-15T01:00:00Z",
        ticket_url="https://secondcityus.my.salesforce-sites.com/ticket/#/instances/xyz",
        sold_out=False,
    )
    club = _club(timezone=None)
    show = event.to_show(club)

    assert show is not None
    # UTC fallback: 2026-06-15T01:00:00 UTC
    assert show.date.hour == 1
    assert show.date.day == 15


def test_to_show_sold_out_propagated_to_ticket():
    """to_show() forwards sold_out=True to the ticket so sold-out shows are flagged correctly."""
    event = UPComedyClubEvent(
        title="The Best of The Second City: Chicago Style",
        date_utc="2026-05-29T00:00:00Z",
        ticket_url="https://secondcityus.my.salesforce-sites.com/ticket/#/instances/abc123",
        sold_out=True,
    )
    show = event.to_show(_club())
    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].sold_out is True


def test_to_show_not_sold_out_by_default():
    """to_show() correctly reflects sold_out=False for available performances."""
    event = UPComedyClubEvent(
        title="The Best of The Second City: Chicago Style",
        date_utc="2026-05-29T00:00:00Z",
        ticket_url="https://secondcityus.my.salesforce-sites.com/ticket/#/instances/abc123",
        sold_out=False,
    )
    show = event.to_show(_club())
    assert show is not None
    assert show.tickets[0].sold_out is False


def test_to_show_returns_none_for_missing_fields():
    """to_show() returns None when required fields are empty."""
    event = UPComedyClubEvent(title="", date_utc="2026-05-29T00:00:00Z", ticket_url="https://example.com", sold_out=False)
    assert event.to_show(_club()) is None

    event2 = UPComedyClubEvent(title="A Show", date_utc="", ticket_url="https://example.com", sold_out=False)
    assert event2.to_show(_club()) is None

    event3 = UPComedyClubEvent(title="A Show", date_utc="2026-05-29T00:00:00Z", ticket_url="", sold_out=False)
    assert event3.to_show(_club()) is None


def test_to_show_ticket_url_in_show():
    """to_show() sets the Salesforce instance URL as the show's ticket URL."""
    ticket_url = "https://secondcityus.my.salesforce-sites.com/ticket/#/instances/a0FTP000009NIIP2A4"
    event = UPComedyClubEvent(
        title="The Best of The Second City: Chicago Style",
        date_utc="2026-05-29T00:00:00Z",
        ticket_url=ticket_url,
        sold_out=False,
    )
    show = event.to_show(_club())
    assert show is not None
    assert show.show_page_url == ticket_url


# ---------------------------------------------------------------------------
# Past-instance filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_data_filters_past_instances(monkeypatch):
    """get_data() skips instances whose ISO8601 datetime is in the past."""
    scraper = UPComedyClubScraper(_club())
    instances = [
        _make_instance("2020-01-01T00:00:00Z"),  # past — must be skipped
        _make_instance("2026-05-29T00:00:00Z", ticket_url="https://secondcityus.my.salesforce-sites.com/ticket/#/instances/FUTURE"),  # future
    ]

    async def fake_fetch_json(self, url: str, **kwargs) -> Dict:
        return _entity_resolver_response(instances)

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://www.secondcity.com/api/entityResolver?uri=%2Fshows%2Fchicago%2Ftest&isPreview=false")
    assert result is not None, "Expected result with one future instance"
    assert len(result.event_list) == 1, f"Expected 1 event (past filtered), got {len(result.event_list)}"
    assert "FUTURE" in result.event_list[0].ticket_url


@pytest.mark.asyncio
async def test_get_data_returns_none_when_all_instances_are_past(monkeypatch):
    """get_data() returns None when every instance is in the past."""
    scraper = UPComedyClubScraper(_club())
    instances = [
        _make_instance("2020-01-01T00:00:00Z", ticket_url="https://secondcityus.my.salesforce-sites.com/ticket/#/instances/PAST1"),
        _make_instance("2021-06-01T12:00:00Z", ticket_url="https://secondcityus.my.salesforce-sites.com/ticket/#/instances/PAST2"),
    ]

    async def fake_fetch_json(self, url: str, **kwargs) -> Dict:
        return _entity_resolver_response(instances)

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data("https://www.secondcity.com/api/entityResolver?uri=%2Fshows%2Fchicago%2Ftest&isPreview=false")
    assert result is None, "Expected None when all instances are in the past"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_pipeline_graphql_to_events(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = UPComedyClubScraper(_club())
    instances = [_make_instance()]

    async def fake_fetch_json(self, url: str, **kwargs) -> Optional[Dict]:
        if "graphql" in url:
            return _graphql_response(include_up_show=True)
        return _entity_resolver_response(instances)

    monkeypatch.setattr(UPComedyClubScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()
    assert len(urls) == 1

    page_data = await scraper.get_data(urls[0])
    assert isinstance(page_data, UPComedyClubPageData)
    assert len(page_data.event_list) == 1
    assert "salesforce-sites.com" in page_data.event_list[0].ticket_url
    assert page_data.event_list[0].title == "The Best of The Second City: Chicago Style"
