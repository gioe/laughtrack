"""
Pipeline smoke tests for MadridComedyLabScraper.

Exercises get_data() against mocked JSON responses and verifies
the full transformation pipeline produces Show objects.
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.madrid_comedy_lab import MadridComedyLabEvent
from laughtrack.scrapers.implementations.venues.madrid_comedy_lab.scraper import (
    MadridComedyLabScraper,
    _FIENTA_API_URL,
)
from laughtrack.scrapers.implementations.venues.madrid_comedy_lab.data import (
    MadridComedyLabPageData,
)
from laughtrack.scrapers.implementations.venues.madrid_comedy_lab.extractor import (
    MadridComedyLabEventExtractor,
)


def _club() -> Club:
    _c = Club(id=200, name='Madrid Comedy Lab', address='Calle del Amor de Dios 13', website='https://madridcomedylab.com', popularity=0, zip_code='28014', phone_number='', visible=True, timezone='Europe/Madrid')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://fienta.com/api/v1/public/events?organizer=24814', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _api_event(
    id_=177670,
    title="Dark Humour Night",
    starts_at="2099-01-01 20:30:00",
    ends_at="2099-01-01 22:00:00",
    url="https://fienta.com/dark-humour-night-lab-177670",
    sale_status="onSale",
) -> dict:
    return {
        "id": id_,
        "title": title,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "url": url,
        "sale_status": sale_status,
        "description": "<p>Comedy show</p>",
    }


def _api_response(events: list[dict]) -> dict:
    return {"success": {}, "count": len(events), "events": events}


# ---------------------------------------------------------------------------
# collect_scraping_targets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets():
    scraper = MadridComedyLabScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert targets == [_FIENTA_API_URL]


# ---------------------------------------------------------------------------
# get_data tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data(monkeypatch):
    """get_data() returns MadridComedyLabPageData with parsed events."""
    scraper = MadridComedyLabScraper(_club())

    async def fake_fetch(self, url):
        return _api_response([
            _api_event(id_=1, title="Show A"),
            _api_event(id_=2, title="Show B"),
        ])

    monkeypatch.setattr(MadridComedyLabScraper, "fetch_json", fake_fetch)

    result = await scraper.get_data(_FIENTA_API_URL)

    assert isinstance(result, MadridComedyLabPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert titles == {"Show A", "Show B"}


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_response(monkeypatch):
    """get_data() returns None when API returns no data."""
    scraper = MadridComedyLabScraper(_club())

    async def fake_fetch(self, url):
        return None

    monkeypatch.setattr(MadridComedyLabScraper, "fetch_json", fake_fetch)

    result = await scraper.get_data(_FIENTA_API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_no_events(monkeypatch):
    """get_data() returns None when extractor finds no events."""
    scraper = MadridComedyLabScraper(_club())

    async def fake_fetch(self, url):
        return _api_response([])

    monkeypatch.setattr(MadridComedyLabScraper, "fetch_json", fake_fetch)

    result = await scraper.get_data(_FIENTA_API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_filters_excluded_titles(monkeypatch):
    """get_data() excludes events with Gift/Valencia in title."""
    scraper = MadridComedyLabScraper(_club())

    async def fake_fetch(self, url):
        return _api_response([
            _api_event(id_=1, title="Comedy Night"),
            _api_event(id_=2, title="Gift Card"),
            _api_event(id_=3, title="Valencia Show"),
        ])

    monkeypatch.setattr(MadridComedyLabScraper, "fetch_json", fake_fetch)

    result = await scraper.get_data(_FIENTA_API_URL)

    assert result is not None
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Comedy Night"


@pytest.mark.asyncio
async def test_get_data_returns_none_on_exception(monkeypatch):
    """get_data() returns None when fetch raises an exception."""
    scraper = MadridComedyLabScraper(_club())

    async def fake_fetch(self, url):
        raise ConnectionError("Network error")

    monkeypatch.setattr(MadridComedyLabScraper, "fetch_json", fake_fetch)

    result = await scraper.get_data(_FIENTA_API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_preserves_sale_status(monkeypatch):
    """get_data() preserves sale_status from API response."""
    scraper = MadridComedyLabScraper(_club())

    async def fake_fetch(self, url):
        return _api_response([_api_event(sale_status="soldOut")])

    monkeypatch.setattr(MadridComedyLabScraper, "fetch_json", fake_fetch)

    result = await scraper.get_data(_FIENTA_API_URL)

    assert result is not None
    assert result.event_list[0].sale_status == "soldOut"


# ---------------------------------------------------------------------------
# Full transformation pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transformation_pipeline_produces_shows(monkeypatch):
    """Full pipeline: get_data -> transform -> Show objects."""
    scraper = MadridComedyLabScraper(_club())

    async def fake_fetch(self, url):
        return _api_response([
            _api_event(id_=1, title="Carlos García Live"),
        ])

    monkeypatch.setattr(MadridComedyLabScraper, "fetch_json", fake_fetch)

    page_data = await scraper.get_data(_FIENTA_API_URL)
    assert page_data is not None

    shows = scraper.transformation_pipeline.transform(page_data)
    assert len(shows) >= 1
    assert shows[0].name == "Carlos García Live"
    assert shows[0].club_id == 200
    assert len(shows[0].lineup) == 1
    assert shows[0].lineup[0].name == "Carlos García"
