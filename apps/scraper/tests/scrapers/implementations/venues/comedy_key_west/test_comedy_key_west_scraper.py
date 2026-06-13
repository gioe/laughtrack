"""
Unit tests for ComedyKeyWestScraper.get_data() async method.

These tests verify the four key paths in get_data():
 1. Empty HTML from fetch_html_bare → returns None
 2. Non-empty HTML with no shows found → returns None with a warning
 3. Successful extraction → returns ComedyKeyWestPageData with expected shows
 4. Exception raised by fetch_html_bare → returns None

Also verifies that the scraper is registered under the "comedy_key_west" key.
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.comedy_key_west.scraper import ComedyKeyWestScraper
from laughtrack.scrapers.implementations.venues.comedy_key_west.data import ComedyKeyWestPageData


def _club() -> Club:
    _c = Club(id=98, name='Comedy Key West', address='', website='https://comedykeywest.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='comedykeywest.com/shows', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _build_show_html() -> str:
    """Return minimal HTML that PunchupExtractor will parse into one show."""
    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "some-venue-uuid"],
                "state": {
                    "data": {
                        "mode": "custom",
                        "items": [
                            {
                                "type": "show",
                                "id": "item-uuid-1",
                                "order": 1,
                                "show": {
                                    "id": "show-uuid-1",
                                    "title": "Key West Comedy Night",
                                    "datetime": "2026-04-15T20:00:00",
                                    "ticket_link": "https://event.tixologi.com/event/42/tickets",
                                    "tixologi_event_id": "42",
                                    "is_sold_out": False,
                                    "metadata_text": None,
                                    "show_comedians": [],
                                },
                            }
                        ],
                    },
                    "status": "success",
                },
            }
        ]
    }
    json_str = json.dumps(payload)
    return f"<html><body><script>{json_str}</script></body></html>"


def _build_no_shows_html() -> str:
    """Return HTML with an empty carousel items list — extractor returns []."""
    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "some-venue-uuid"],
                "state": {
                    "data": {"mode": "custom", "items": []},
                    "status": "success",
                },
            }
        ]
    }
    json_str = json.dumps(payload)
    return f"<html><body><script>{json_str}</script></body></html>"


# ---------------------------------------------------------------------------
# Registry key
# ---------------------------------------------------------------------------


def test_scraper_key_in_registry():
    from laughtrack.app.registry import SCRAPERS

    assert SCRAPERS.get("comedy_key_west") is ComedyKeyWestScraper


# ---------------------------------------------------------------------------
# ComedyKeyWestScraper.get_data — four paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_empty_html_returns_none(monkeypatch):
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        return ""

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data("comedykeywest.com/shows")
    assert result is None


@pytest.mark.asyncio
async def test_get_data_no_shows_returns_none(monkeypatch):
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        return _build_no_shows_html()

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data("comedykeywest.com/shows")
    assert result is None


def _stub_tixologi(monkeypatch):
    """Bypass Tixologi enrichment in tests that don't exercise pricing."""

    async def identity(self, shows):
        return shows

    monkeypatch.setattr(ComedyKeyWestScraper, "_enrich_tixologi_tickets", identity)


@pytest.mark.asyncio
async def test_get_data_successful_extraction_returns_page_data(monkeypatch):
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        return _build_show_html()

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html_bare", fake_fetch_html_bare)
    _stub_tixologi(monkeypatch)

    result = await scraper.get_data("comedykeywest.com/shows")
    assert isinstance(result, ComedyKeyWestPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Key West Comedy Night"


@pytest.mark.asyncio
async def test_get_data_fetch_exception_returns_none(monkeypatch):
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        raise RuntimeError("network error")

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data("comedykeywest.com/shows")
    assert result is None


# ---------------------------------------------------------------------------
# Tixologi ticket-type enrichment (TASK-2851) — mirrors creek_and_cave
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_enriches_tixologi_ticket_types(monkeypatch):
    """Shows carry Tixologi initial_price tickets via the creek_and_cave pattern."""
    from laughtrack.scrapers.implementations.venues.comedy_key_west.data import (
        ComedyKeyWestShow,
    )

    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        return _build_show_html()

    async def fake_fetch_event_ticket_types(event_id: str):
        assert event_id == "42"
        return [{"name": "General Admission", "initial_price": 30, "sold_out": False}]

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(
        scraper.tixologi_client,
        "fetch_event_ticket_types",
        fake_fetch_event_ticket_types,
    )

    result = await scraper.get_data("comedykeywest.com/shows")

    assert isinstance(result, ComedyKeyWestPageData)
    enriched = result.event_list[0]
    # dataclasses.replace must preserve the venue subclass for transformer dispatch.
    assert isinstance(enriched, ComedyKeyWestShow)
    show = enriched.to_show(_club())
    assert show is not None
    assert show.tickets[0].price == 30.0
    assert show.tickets[0].type == "General Admission"


@pytest.mark.asyncio
async def test_get_data_enrichment_failure_keeps_show_with_fallback_ticket(monkeypatch):
    """A Tixologi outage degrades one show to the priceless fallback, not a dropped page."""
    scraper = ComedyKeyWestScraper(_club())

    async def fake_fetch_html_bare(self, url: str):
        return _build_show_html()

    async def raising_fetch_event_ticket_types(event_id: str):
        raise RuntimeError("tixologi down")

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(
        scraper.tixologi_client,
        "fetch_event_ticket_types",
        raising_fetch_event_ticket_types,
    )

    result = await scraper.get_data("comedykeywest.com/shows")

    assert isinstance(result, ComedyKeyWestPageData)
    show = result.event_list[0].to_show(_club())
    assert show is not None
    assert show.tickets[0].price is None


@pytest.mark.asyncio
async def test_get_data_enrichment_skips_shows_without_tixologi_event_id(monkeypatch):
    """Shows without a resolvable tixologi_event_id never trigger a client call."""
    import json as _json

    scraper = ComedyKeyWestScraper(_club())
    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "some-venue-uuid"],
                "state": {
                    "data": {
                        "mode": "custom",
                        "items": [
                            {
                                "type": "show",
                                "id": "item-uuid-1",
                                "order": 1,
                                "show": {
                                    "id": "show-uuid-1",
                                    "title": "Walk-In Night",
                                    "datetime": "2026-04-15T20:00:00",
                                    "ticket_link": "https://www.eventbrite.com/e/walk-in-12345",
                                    "tixologi_event_id": None,
                                    "is_sold_out": False,
                                    "metadata_text": None,
                                    "show_comedians": [],
                                },
                            }
                        ],
                    },
                    "status": "success",
                },
            }
        ]
    }
    html = f"<html><body><script>{_json.dumps(payload)}</script></body></html>"

    async def fake_fetch_html_bare(self, url: str):
        return html

    # Record calls rather than raising: the enrichment guard catches Exception
    # (including AssertionError), so an exploding mock could be swallowed and
    # the test would pass even if the client WERE called.
    client_calls: list = []

    async def recording_fetch_event_ticket_types(event_id: str):
        client_calls.append(event_id)
        return []

    monkeypatch.setattr(ComedyKeyWestScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(
        scraper.tixologi_client,
        "fetch_event_ticket_types",
        recording_fetch_event_ticket_types,
    )

    result = await scraper.get_data("comedykeywest.com/shows")

    assert isinstance(result, ComedyKeyWestPageData)
    assert client_calls == [], "client must not be called for shows without an event id"
    show = result.event_list[0].to_show(_club())
    assert show.tickets[0].price is None
