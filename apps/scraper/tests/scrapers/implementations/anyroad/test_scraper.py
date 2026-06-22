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


def _detail_html(dates: dict) -> str:
    """A minimal AnyRoad booking detail page embedding tour_availability.dates."""
    blob = json.dumps(dates)
    return (
        '<!DOCTYPE html><html><body><div data-react-props=\'{"x":1}\'>'
        '{"booking":{},"tour_availability":{"isLoading":false,"cached":{},'
        f'"dates":{blob}}},"trailing":1}}'
        "</div></body></html>"
    )


# Real per-experience availability keyed by the slug in the detail URL. CSz and
# Riot both have a 2026-07-18 occurrence but at *different* real times, so they
# stay distinct under the (club, date, room) key.
_AVAILABILITY_BY_SLUG = {
    "comedysportz-597fdff3-6214-443a-8fcd-0e05e5e197d5": {
        "2026-06-27": {" 6:00pm": 23},
        "2026-07-18": {" 6:00pm": 20},
    },
    "riot-improv-mainstage-stories-to-scenes": {
        "2026-07-18": {" 8:00pm": 5},
    },
    "roslindale-queer-comedy-night": {
        "2026-07-17": {" 7:30pm": 0},
    },
}


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
    # Mirror the real DB load path: the plugin id is wired in metadata.plugin_id
    # (scraping_sources has no external_id column), with source_url as fallback.
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="custom",
        scraper_key="anyroad",
        source_url="https://app.anyroad.com/i/plugin/rozziesquaretheater",
        external_id=None,
        metadata={"plugin_id": "rozziesquaretheater"},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_registry_resolves_anyroad_key():
    assert discover_scrapers().get("anyroad") is AnyRoadScraper


def test_resolve_plugin_id_from_metadata_prod_wire(club):
    # The canonical production wire: metadata.plugin_id (no external_id column).
    assert AnyRoadScraper(club)._resolve_plugin_id() == "rozziesquaretheater"


def test_resolve_plugin_id_external_id_fallback():
    # Forward-compat: if a future schema ever populates external_id, it resolves
    # when metadata.plugin_id is absent.
    c = Club(id=1, name="V", address="", website="", popularity=0, zip_code="",
             phone_number="", visible=True, timezone="America/New_York", city="", state="MA")
    c.active_scraping_source = ScrapingSource(
        platform="custom", scraper_key="anyroad", external_id="fromExternal",
        metadata={},
    )
    assert AnyRoadScraper(c)._resolve_plugin_id() == "fromExternal"


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


def _slug_of(url: str) -> str:
    return urlparse(url).path.rstrip("/").split("/")[-1]


@pytest.mark.asyncio
async def test_scraper_full_pipeline_uses_real_detail_times(monkeypatch, club):
    scraper = AnyRoadScraper(club)
    page1 = _load("experiences_page1.json")
    page2 = _load("experiences_page2_empty.json")

    async def fake_fetch_json(url, **kwargs):
        qs = parse_qs(urlparse(url).query)
        assert qs["plugin_id"] == ["rozziesquaretheater"]
        return page1 if int(qs["page"][0]) == 1 else page2

    async def fake_fetch_html(url, **kwargs):
        return _detail_html(_AVAILABILITY_BY_SLUG[_slug_of(url)])

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)

    shows = await scraper.scrape_async()

    # One show per (experience, date, time) from the *detail* availability:
    # CSz 2 + Riot 1 + Queer 1 = 4.
    assert len(shows) == 4
    assert {s.club_id for s in shows} == {club.id}

    csz = [s for s in shows if s.name == "ComedySportz®"]
    assert len(csz) == 2
    # Real 6:00pm time from the detail page, NOT the 9:00 AM list placeholder.
    assert all(s.date.isoformat() == f"{s.date.date()}T18:00:00-04:00" for s in csz)
    assert csz[0].tickets and csz[0].tickets[0].price == 13.0
    assert csz[0].room == "18b Corinth Street, Boston, MA"

    # CSz (6pm) and Riot (8pm) both fall on 2026-07-18 — distinct real times keep
    # them as two separate shows rather than collapsing under (club, date, room).
    on_0718 = sorted(s.date.isoformat() for s in shows if s.date.date().isoformat() == "2026-07-18")
    assert on_0718 == ["2026-07-18T18:00:00-04:00", "2026-07-18T20:00:00-04:00"]


@pytest.mark.asyncio
async def test_detail_fetch_failure_falls_back_to_placeholder_schedule(monkeypatch, club):
    scraper = AnyRoadScraper(club)
    page1 = _load("experiences_page1.json")
    page2 = _load("experiences_page2_empty.json")

    async def fake_fetch_json(url, **kwargs):
        return page1 if int(parse_qs(urlparse(url).query)["page"][0]) == 1 else page2

    async def failing_fetch_html(url, **kwargs):
        raise RuntimeError("detail page unreachable")

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper, "fetch_html", failing_fetch_html)

    shows = await scraper.scrape_async()

    # Every detail fetch failed, so each experience falls back to its list
    # placeholder schedule (CSz 4 + Riot 4 + Queer 2 = 10) at the 9:00 AM nominal.
    assert len(shows) == 10
    csz = next(s for s in shows if s.name == "ComedySportz®")
    assert csz.date.isoformat().endswith("T09:00:00-04:00")


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
