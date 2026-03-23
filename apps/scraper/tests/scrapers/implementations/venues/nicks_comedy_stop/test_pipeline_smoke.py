"""
Pipeline smoke test for NicksComedyStopScraper.

Exercises collect_scraping_targets() -> get_data() against mocked Wix API
responses matching the actual Nick's Comedy Stop paginated-events structure.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.nicks_comedy_stop.scraper import (
    NicksComedyStopScraper,
)
from laughtrack.scrapers.implementations.venues.nicks_comedy_stop.data import NicksPageData


EVENTS_URL = (
    "https://www.nickscomedystop.com/_api/wix-one-events-server/web/paginated-events/viewer"
)


def _club() -> Club:
    return Club(
        id=143,
        name="Nick's Comedy Stop",
        address="100 Warrenton St, Boston, MA",
        website="https://www.nickscomedystop.com",
        scraping_url="https://www.nickscomedystop.com",
        popularity=0,
        zip_code="02116",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _token_response() -> dict:
    """Minimal Wix access-tokens API response with intId=24."""
    return {
        "apps": {
            "wix-events": {
                "intId": 24,
                "instance": "test-access-token",
            }
        }
    }


def _raw_event(id_="evt-001", title="Friday Night Comedy", slug="friday-night-comedy") -> dict:
    return {
        "id": id_,
        "title": title,
        "description": "A great show",
        "slug": slug,
        "scheduling": {
            "config": {
                "startDate": "2026-03-28T01:00:00.000Z",
                "timeZoneId": "America/New_York",
            }
        },
        "registration": {
            "ticketing": {
                "lowestTicketPrice": {"amount": "20.00"}
            }
        },
    }


def _events_response(events: list) -> dict:
    return {"events": events}


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_single_url(monkeypatch):
    """collect_scraping_targets() returns the Wix paginated-events API URL after auth."""
    scraper = NicksComedyStopScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        if "access-tokens" in url:
            return _token_response()
        return {}

    monkeypatch.setattr(NicksComedyStopScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()

    assert len(urls) == 1
    assert "paginated-events" in urls[0]
    assert "nickscomedystop.com" in urls[0]
    assert "compId=comp-m4t1prev" in urls[0]


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_empty_on_auth_failure(monkeypatch):
    """collect_scraping_targets() returns [] when the token endpoint returns no intId=24."""
    scraper = NicksComedyStopScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        if "access-tokens" in url:
            return {"apps": {"other": {"intId": 99, "instance": "wrong"}}}
        return {}

    monkeypatch.setattr(NicksComedyStopScraper, "fetch_json", fake_fetch_json)

    urls = await scraper.collect_scraping_targets()
    assert urls == []


@pytest.mark.asyncio
async def test_get_data_returns_events_from_json_fixture(monkeypatch):
    """get_data() parses the Wix events JSON and returns NicksPageData with events."""
    scraper = NicksComedyStopScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _events_response([
            _raw_event(id_="1", title="Friday Show"),
            _raw_event(id_="2", title="Saturday Show"),
        ])

    monkeypatch.setattr(NicksComedyStopScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(EVENTS_URL)

    assert isinstance(result, NicksPageData), "get_data() did not return NicksPageData"
    assert len(result.event_list) == 2, (
        f"Expected 2 events, got {len(result.event_list)} — "
        "check NicksEventExtractor against Wix API response fixture"
    )
    titles = {e.title for e in result.event_list}
    assert "Friday Show" in titles
    assert "Saturday Show" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_response(monkeypatch):
    """get_data() returns None when the API returns an empty dict."""
    scraper = NicksComedyStopScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {}

    monkeypatch.setattr(NicksComedyStopScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(EVENTS_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    """get_data() returns None when the API response has an empty events list."""
    scraper = NicksComedyStopScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _events_response([])

    monkeypatch.setattr(NicksComedyStopScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(EVENTS_URL)
    assert result is None


@pytest.mark.asyncio
async def test_can_transform_not_defined_on_scraper():
    """NicksComedyStopScraper must not define can_transform() — transformation is handled by the pipeline."""
    assert "can_transform" not in NicksComedyStopScraper.__dict__, (
        "can_transform() must not be defined on NicksComedyStopScraper"
    )
