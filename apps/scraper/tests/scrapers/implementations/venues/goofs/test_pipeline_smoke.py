"""
Pipeline smoke test for GoofsComedyClubScraper.

Exercises collect_scraping_targets() -> get_data() against an HTML fixture
matching the actual goofscomedy.com /p/shows RSC payload structure.
"""

import json

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.goofs.scraper import GoofsComedyClubScraper
from laughtrack.scrapers.implementations.venues.goofs.data import GoofsPageData


SHOWS_URL = "https://goofscomedy.com/p/shows"


def _club() -> Club:
    _c = Club(id=142, name='Goofs Comedy Club', address='432 McGrath Highway, Somerville, MA', website='https://goofscomedy.com', popularity=0, zip_code='02143', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='goofscomedy.com/p/shows', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_rsc_html(shows: list) -> str:
    """Embed a shows list in a minimal Next.js RSC __next_f.push payload."""
    inner_obj = {"initialShows": shows}
    inner_json = json.dumps(inner_obj)
    escaped = json.dumps(inner_json)[1:-1]
    return f'<html><head></head><body><script>self.__next_f.push([1,"{escaped}"])</script></body></html>'


def _show_dict(id_=403, title="Friday Night Live", date="2026-03-27", time="9:00 PM"):
    return {
        "id": id_,
        "slug": f"{date}-2100",
        "date": date,
        "time": time,
        "computedDisplayTitle": title,
        "headlinerName": "Jane Doe",
        "priceGaCents": 2000,
    }


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_single_url():
    """collect_scraping_targets() must return the club's scraping URL."""
    scraper = GoofsComedyClubScraper(_club())
    urls = await scraper.collect_scraping_targets()
    assert len(urls) == 1
    assert "goofscomedy.com" in urls[0]


@pytest.mark.asyncio
async def test_get_data_returns_events_from_rsc_fixture(monkeypatch):
    """get_data() parses the RSC payload and returns GoofsPageData with events."""
    scraper = GoofsComedyClubScraper(_club())
    html = _make_rsc_html([_show_dict(id_=1), _show_dict(id_=2, title="Late Show")])

    async def fake_fetch_html(self, url: str) -> str:
        return html

    monkeypatch.setattr(GoofsComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SHOWS_URL)

    assert isinstance(result, GoofsPageData), "get_data() did not return GoofsPageData"
    assert len(result.event_list) == 2, (
        f"Expected 2 events, got {len(result.event_list)} — "
        "check GoofsEventExtractor against RSC payload HTML"
    )
    titles = {e.display_title for e in result.event_list}
    assert "Friday Night Live" in titles
    assert "Late Show" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when the page returns empty HTML."""
    scraper = GoofsComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return ""

    monkeypatch.setattr(GoofsComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SHOWS_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_shows_in_payload(monkeypatch):
    """get_data() returns None when the RSC payload has no initialShows data."""
    scraper = GoofsComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return "<html><body><p>No shows found</p></body></html>"

    monkeypatch.setattr(GoofsComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SHOWS_URL)
    assert result is None


@pytest.mark.asyncio
async def test_can_transform_not_defined_on_scraper():
    """GoofsComedyClubScraper must not define can_transform() — it's dead code."""
    assert not hasattr(GoofsComedyClubScraper, "can_transform") or (
        "can_transform" not in GoofsComedyClubScraper.__dict__
    ), "can_transform() must be removed from GoofsComedyClubScraper (dead code)"
