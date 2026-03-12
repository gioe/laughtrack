"""Unit tests for SeatEngineNationalScraper."""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from unittest.mock import AsyncMock, MagicMock, patch

from laughtrack.scrapers.implementations.api.seatengine_national.scraper import (
    SeatEngineNationalScraper,
)
from laughtrack.core.entities.club.model import Club


@pytest.fixture
def platform_club() -> Club:
    """Minimal 'platform' club row that triggers the national scraper."""
    return Club(
        id=999,
        name="SeatEngine National",
        address="",
        website="",
        scraping_url="www.seatengine.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        scraper="seatengine_national",
    )


def _make_venue_dict(venue_id=458, name="McGuire's Comedy Club", address="123 Main St", zip_code="10001"):
    return {"id": venue_id, "name": name, "address": address, "zip": zip_code, "website": ""}


def _make_club(club_id=42, name="McGuire's Comedy Club", seatengine_id="458"):
    return Club(
        id=club_id,
        name=name,
        address="123 Main St",
        website="",
        scraping_url="www.seatengine.com",
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
        scraper="seatengine",
        seatengine_id=seatengine_id,
    )


# ------------------------------------------------------------------ #
# collect_scraping_targets                                             #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_collect_targets_returns_national(platform_club):
    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        s = SeatEngineNationalScraper(platform_club)
    targets = await s.collect_scraping_targets()
    assert targets == ["national"]


# ------------------------------------------------------------------ #
# scrape_async — empty API response                                    #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_empty_response(platform_club):
    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)

    with patch.object(scraper, "_fetch_seatengine_venues", new=AsyncMock(return_value=[])):
        shows = await scraper.scrape_async()

    assert shows == []


# ------------------------------------------------------------------ #
# scrape_async — venues are upserted, no shows returned               #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_upserts_venues_returns_no_shows(platform_club):
    """scrape_async upserts discovered venues and returns [] (enumeration only)."""
    venues = [_make_venue_dict(458), _make_venue_dict(457, name="Brokerage Comedy Club")]
    upserted_club = _make_club()

    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)

    with patch.object(scraper, "_fetch_seatengine_venues", new=AsyncMock(return_value=venues)):
        with patch.object(
            scraper._club_handler,
            "upsert_for_seatengine_venue",
            return_value=upserted_club,
        ) as mock_upsert:
            shows = await scraper.scrape_async()

    assert shows == []
    assert mock_upsert.call_count == 2


# ------------------------------------------------------------------ #
# _fetch_seatengine_venues — pagination                               #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_fetch_venues_paginates_until_last_page(platform_club, monkeypatch):
    """_fetch_seatengine_venues follows pagination until last_page is reached."""
    page1 = {"data": [_make_venue_dict(458)], "meta": {"last_page": 2}}
    page2 = {"data": [_make_venue_dict(457, name="Brokerage")], "meta": {"last_page": 2}}

    call_count = {"n": 0}

    async def fake_fetch_json(url, **kwargs):
        call_count["n"] += 1
        return page1 if call_count["n"] == 1 else page2

    monkeypatch.setattr(
        "laughtrack.infrastructure.config.config_manager.ConfigManager.get_config",
        lambda *a, **kw: "fake_token",
    )

    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)
    scraper.fetch_json = fake_fetch_json

    venues = await scraper._fetch_seatengine_venues()

    assert len(venues) == 2
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_fetch_venues_exits_on_empty_page(platform_club, monkeypatch):
    """_fetch_seatengine_venues stops when data list is empty."""
    page1 = {"data": [_make_venue_dict(458)], "meta": {"last_page": 10}}
    page2 = {"data": [], "meta": {"last_page": 10}}

    call_count = {"n": 0}

    async def fake_fetch_json(url, **kwargs):
        call_count["n"] += 1
        return page1 if call_count["n"] == 1 else page2

    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)
    scraper.fetch_json = fake_fetch_json

    venues = await scraper._fetch_seatengine_venues()

    assert len(venues) == 1
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_fetch_venues_exits_on_null_response(platform_club):
    """_fetch_seatengine_venues stops when fetch_json returns None."""
    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)
    scraper.fetch_json = AsyncMock(return_value=None)

    venues = await scraper._fetch_seatengine_venues()

    assert venues == []


# ------------------------------------------------------------------ #
# _upsert_venues — skip venues without id                             #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_upsert_venues_skips_missing_id(platform_club):
    """Venues with no id are skipped; the rest are processed."""
    venues = [{"name": "No Id Club"}, _make_venue_dict(458)]
    upserted_club = _make_club()

    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)

    with patch.object(
        scraper._club_handler,
        "upsert_for_seatengine_venue",
        return_value=upserted_club,
    ) as mock_upsert:
        await scraper._upsert_venues(venues)

    # Only the venue with an id should be passed to the handler
    assert mock_upsert.call_count == 1


# ------------------------------------------------------------------ #
# _upsert_venues — exception isolation per venue                      #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_upsert_venues_exception_does_not_abort_loop(platform_club):
    """A DB exception for one venue should not prevent others from being upserted."""
    venues = [
        _make_venue_dict(458, name="Good Club"),
        _make_venue_dict(457, name="Bad Club"),
        _make_venue_dict(456, name="Also Good Club"),
    ]
    good_club = _make_club()

    def _upsert(venue):
        if venue.get("name") == "Bad Club":
            raise RuntimeError("DB error")
        return good_club

    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)

    with patch.object(scraper._club_handler, "upsert_for_seatengine_venue", side_effect=_upsert) as mock_upsert:
        # Should not raise
        await scraper._upsert_venues(venues)

    assert mock_upsert.call_count == 3
