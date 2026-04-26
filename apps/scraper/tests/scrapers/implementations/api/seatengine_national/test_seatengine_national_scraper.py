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
from laughtrack.core.entities.club.model import Club, ScrapingSource


@pytest.fixture
def platform_club() -> Club:
    """Minimal 'platform' club row that triggers the national scraper."""
    _c = Club(id=999, name='SeatEngine National', address='', website='', popularity=0, zip_code='', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='seatengine_national', scraper_key='seatengine_national', source_url='www.seatengine.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_venue_dict(venue_id=458, name="McGuire's Comedy Club", address="123 Main St", zip_code="10001"):
    return {"id": venue_id, "name": name, "address": address, "zip": zip_code, "website": ""}


def _make_club(club_id=42, name="McGuire's Comedy Club", seatengine_id="458"):
    _c = Club(id=club_id, name=name, address='123 Main St', website='', popularity=0, zip_code='10001', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='seatengine', scraper_key='seatengine', source_url='www.seatengine.com', external_id=seatengine_id)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


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
# _fetch_seatengine_venues — concurrent per-venue scan                #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_fetch_venues_returns_named_venues(platform_club):
    """_fetch_seatengine_venues collects venues that have a non-empty name."""
    # IDs 1 and 2 have data; ID 3 has null data (empty slot)
    def _fake_fetch_json(url, **kwargs):
        vid = int(url.rstrip("/").split("/")[-1])
        if vid == 1:
            return {"data": _make_venue_dict(1, name="Helium Comedy Club")}
        if vid == 2:
            return {"data": _make_venue_dict(2, name="Stress Factory")}
        return {"data": None}

    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)
    scraper._venue_scan_max_id = 3
    scraper.fetch_json = AsyncMock(side_effect=_fake_fetch_json)

    venues = await scraper._fetch_seatengine_venues()

    assert len(venues) == 2
    names = {v["name"] for v in venues}
    assert names == {"Helium Comedy Club", "Stress Factory"}


@pytest.mark.asyncio
async def test_fetch_venues_filters_null_data(platform_club):
    """_fetch_seatengine_venues skips IDs where data is null."""
    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)
    scraper._venue_scan_max_id = 3
    scraper.fetch_json = AsyncMock(return_value={"data": None})

    venues = await scraper._fetch_seatengine_venues()

    assert venues == []


@pytest.mark.asyncio
async def test_fetch_venues_filters_nameless_venues(platform_club):
    """_fetch_seatengine_venues skips venues where name is empty/None."""
    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)
    scraper._venue_scan_max_id = 2
    scraper.fetch_json = AsyncMock(return_value={"data": {"id": 1, "name": None}})

    venues = await scraper._fetch_seatengine_venues()

    assert venues == []


@pytest.mark.asyncio
async def test_fetch_venues_handles_per_id_error(platform_club):
    """An exception for one venue ID does not abort the full scan."""
    call_count = {"n": 0}

    def _side_effect(url, **kwargs):
        call_count["n"] += 1
        vid = int(url.rstrip("/").split("/")[-1])
        if vid == 2:
            raise RuntimeError("network error")
        return {"data": _make_venue_dict(vid, name=f"Club {vid}")}

    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)
    scraper._venue_scan_max_id = 3
    scraper.fetch_json = AsyncMock(side_effect=_side_effect)

    venues = await scraper._fetch_seatengine_venues()

    # IDs 1 and 3 succeed; ID 2 is skipped due to error
    assert len(venues) == 2
    assert call_count["n"] == 3


@pytest.mark.asyncio
async def test_fetch_venues_exits_on_null_fetch_response(platform_club):
    """_fetch_seatengine_venues handles fetch_json returning None gracefully."""
    with patch("laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config", return_value="fake_token"):
        scraper = SeatEngineNationalScraper(platform_club)
    scraper._venue_scan_max_id = 3
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
