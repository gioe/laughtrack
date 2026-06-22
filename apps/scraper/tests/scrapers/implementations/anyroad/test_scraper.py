"""Tests for the AnyRoad experiences-API scraper.

The smoke test drives the full ``scrape_async`` pipeline against captured real
fixtures (Rozzie Square Theater: ComedySportz® / Riot Improv Mainstage / Rozzie
Queer Comedy Night) so a transformer/extractor/wiring regression is caught.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.app.registry import discover_scrapers
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.anyroad.scraper import AnyRoadScraper

_FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


@pytest.fixture
def club() -> Club:
    _c = Club(
        id=999,
        name="The Rozzie Square Theater",
        address="5 Basile St",
        website="http://www.rozziesquaretheater.com/",
        popularity=0,
        zip_code="02131",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        city="Boston",
        state="MA",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="anyroad",
        scraper_key="anyroad",
        source_url="https://app.anyroad.com/i/plugin/rozziesquaretheater",
        external_id="rozziesquaretheater",
        metadata={},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_registry_resolves_anyroad_key():
    assert discover_scrapers().get("anyroad") is AnyRoadScraper


def test_resolve_plugin_id_prefers_external_id(club):
    assert AnyRoadScraper(club)._resolve_plugin_id() == "rozziesquaretheater"


def test_resolve_plugin_id_from_metadata():
    c = Club(id=1, name="V", address="", website="", popularity=0, zip_code="",
             phone_number="", visible=True, timezone="America/New_York", city="", state="MA")
    c.active_scraping_source = ScrapingSource(
        platform="anyroad", scraper_key="anyroad", external_id=None,
        metadata={"plugin_id": "fromMeta"},
    )
    assert AnyRoadScraper(c)._resolve_plugin_id() == "fromMeta"


def test_resolve_plugin_id_parsed_from_source_url():
    c = Club(id=1, name="V", address="", website="", popularity=0, zip_code="",
             phone_number="", visible=True, timezone="America/New_York", city="", state="MA")
    c.active_scraping_source = ScrapingSource(
        platform="anyroad", scraper_key="anyroad", external_id=None,
        source_url="https://app.anyroad.com/i/plugin/parsedFromUrl/tours",
        metadata={},
    )
    assert AnyRoadScraper(c)._resolve_plugin_id() == "parsedFromUrl"


@pytest.mark.asyncio
async def test_scraper_full_pipeline_produces_shows(monkeypatch, club):
    scraper = AnyRoadScraper(club)
    page1 = _load("experiences_page1.json")
    page2 = _load("experiences_page2_empty.json")

    calls: list[int] = []

    async def fake_fetch_json(url, **kwargs):
        qs = parse_qs(urlparse(url).query)
        assert qs["plugin_id"] == ["rozziesquaretheater"]
        page = int(qs["page"][0])
        calls.append(page)
        return page1 if page == 1 else page2

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    shows = await scraper.scrape_async()

    # Fixture: ComedySportz (4 dates) + Riot Improv (4) + Queer Comedy (2) = 10.
    assert len(shows) == 10
    assert {s.club_id for s in shows} == {club.id}
    names = {s.name for s in shows}
    assert "ComedySportz®" in names  # CSz Boston resident company
    assert any("Riot Improv" in n for n in names)  # Riot Theater resident company
    assert any("Queer Comedy" in n for n in names)  # Rozzie's own show

    csz = next(s for s in shows if s.name == "ComedySportz®")
    assert csz.show_page_url.endswith("comedysportz-597fdff3-6214-443a-8fcd-0e05e5e197d5?lang=en-US") or \
        "comedysportz" in csz.show_page_url
    assert csz.tickets and csz.tickets[0].price == 13.0

    # Pagination stopped at the empty page (page 1 then page 2).
    assert calls == [1, 2]


@pytest.mark.asyncio
async def test_no_plugin_id_yields_no_shows(monkeypatch):
    c = Club(id=2, name="No Config", address="", website="", popularity=0, zip_code="",
             phone_number="", visible=True, timezone="America/New_York", city="", state="MA")
    c.active_scraping_source = ScrapingSource(
        platform="anyroad", scraper_key="anyroad", external_id=None, metadata={},
    )
    scraper = AnyRoadScraper(c)

    async def fail_fetch(url, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("fetch_json should not run without a plugin id")

    monkeypatch.setattr(scraper, "fetch_json", fail_fetch)
    assert await scraper.scrape_async() == []
