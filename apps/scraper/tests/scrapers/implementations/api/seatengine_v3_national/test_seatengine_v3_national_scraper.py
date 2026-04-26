"""Unit tests for SeatEngineV3NationalScraper."""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from unittest.mock import AsyncMock, MagicMock, patch

from laughtrack.scrapers.implementations.api.seatengine_v3_national.scraper import (
    SeatEngineV3NationalScraper,
)
from laughtrack.core.entities.club.model import Club, ScrapingSource


_V3_UUID = "cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3"
_V3_UUID2 = "e7ea1e53-8a31-48b6-bfe4-fd9672791615"

# CDX API response format: [[header], [url1], [url2], ...]
_CDX_RESPONSE_WITH_TWO_VENUES = [
    ["original"],
    [f"https://v-{_V3_UUID}.seatengine.net/events"],
    [f"https://v-{_V3_UUID}.seatengine.net/contact"],  # duplicate — deduped
    [f"https://v-{_V3_UUID2}.seatengine.net/"],
]

_VENUE_RESPONSE_1 = {
    "data": {
        "venue": {
            "uuid": _V3_UUID,
            "name": "The Comedy Studio",
            "website": "https://thecomedystudio.com",
            "settings": {
                "address": "5 John F. Kennedy St",
                "city": "Cambridge",
                "state": "MA",
                "zipcode": "02138",
            },
        }
    }
}

_VENUE_RESPONSE_2 = {
    "data": {
        "venue": {
            "uuid": _V3_UUID2,
            "name": "Cafe Coda",
            "website": "https://cafecoda.com",
            "settings": {
                "address": "180 State St",
                "city": "Madison",
                "state": "WI",
                "zipcode": "53703",
            },
        }
    }
}


@pytest.fixture
def platform_club() -> Club:
    """Minimal 'platform' club row that triggers the v3 national scraper."""
    _c = Club(id=999, name='SeatEngine V3 National', address='', website='', popularity=0, zip_code='', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='seatengine_v3_national', scraper_key='seatengine_v3_national', source_url='www.seatengine.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_venue_dict(uuid=_V3_UUID, name="The Comedy Studio"):
    return {
        "uuid": uuid,
        "name": name,
        "website": "https://thecomedystudio.com",
        "address": "5 John F. Kennedy St",
        "city": "Cambridge",
        "state": "MA",
        "zipCode": "02138",
    }


def _make_club(club_id=42, name="The Comedy Studio", seatengine_id=_V3_UUID):
    _c = Club(id=club_id, name=name, address='5 John F. Kennedy St', website='https://thecomedystudio.com', popularity=0, zip_code='02138', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='seatengine_v3', scraper_key='seatengine_v3', source_url=f'https://v-{seatengine_id}.seatengine.net', external_id=seatengine_id)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


# ------------------------------------------------------------------ #
# collect_scraping_targets                                             #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_collect_targets_returns_national(platform_club):
    s = SeatEngineV3NationalScraper(platform_club)
    targets = await s.collect_scraping_targets()
    assert targets == ["national"]


# ------------------------------------------------------------------ #
# scrape_async — empty discovery                                      #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_empty_response(platform_club):
    scraper = SeatEngineV3NationalScraper(platform_club)

    with patch.object(scraper, "_fetch_v3_venues", new=AsyncMock(return_value=[])):
        shows = await scraper.scrape_async()

    assert shows == []


# ------------------------------------------------------------------ #
# scrape_async — venues are upserted, no shows returned              #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_scrape_async_upserts_venues_returns_no_shows(platform_club):
    """scrape_async upserts discovered venues and returns [] (discovery only)."""
    venues = [_make_venue_dict(_V3_UUID), _make_venue_dict(_V3_UUID2, name="Cafe Coda")]
    upserted_club = _make_club()

    scraper = SeatEngineV3NationalScraper(platform_club)

    with patch.object(scraper, "_fetch_v3_venues", new=AsyncMock(return_value=venues)):
        with patch.object(
            scraper._club_handler,
            "upsert_for_seatengine_v3_venue",
            return_value=upserted_club,
        ) as mock_upsert:
            shows = await scraper.scrape_async()

    assert shows == []
    assert mock_upsert.call_count == 2


# ------------------------------------------------------------------ #
# _discover_uuids_from_cdx                                           #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_discover_uuids_parses_cdx_response(platform_club):
    """CDX response with two unique v3 subdomains yields two UUIDs (deduped)."""
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.fetch_json = AsyncMock(return_value=_CDX_RESPONSE_WITH_TWO_VENUES)

    uuids = await scraper._discover_uuids_from_cdx()

    assert set(uuids) == {_V3_UUID, _V3_UUID2}


@pytest.mark.asyncio
async def test_discover_uuids_deduplicates(platform_club):
    """Multiple CDX rows for the same subdomain produce one UUID."""
    cdx = [
        ["original"],
        [f"https://v-{_V3_UUID}.seatengine.net/"],
        [f"https://v-{_V3_UUID}.seatengine.net/events"],
        [f"https://v-{_V3_UUID}.seatengine.net/contact"],
    ]
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.fetch_json = AsyncMock(return_value=cdx)

    uuids = await scraper._discover_uuids_from_cdx()

    assert uuids == [_V3_UUID]


@pytest.mark.asyncio
async def test_discover_uuids_ignores_non_v3_urls(platform_club):
    """CDX rows for seatengine.net itself (no v- prefix) are skipped."""
    cdx = [
        ["original"],
        ["https://seatengine.net/"],
        ["https://www.seatengine.net/"],
        [f"https://v-{_V3_UUID}.seatengine.net/events"],
    ]
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.fetch_json = AsyncMock(return_value=cdx)

    uuids = await scraper._discover_uuids_from_cdx()

    assert uuids == [_V3_UUID]


@pytest.mark.asyncio
async def test_discover_uuids_returns_empty_on_network_failure(platform_club):
    """CDX network error returns [] without raising."""
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.fetch_json = AsyncMock(side_effect=RuntimeError("timeout"))

    uuids = await scraper._discover_uuids_from_cdx()

    assert uuids == []


@pytest.mark.asyncio
async def test_discover_uuids_returns_empty_on_empty_cdx_response(platform_club):
    """CDX returning only a header row (no venue rows) returns []."""
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.fetch_json = AsyncMock(return_value=[["original"]])

    uuids = await scraper._discover_uuids_from_cdx()

    assert uuids == []


# ------------------------------------------------------------------ #
# _fetch_venue_by_uuid                                                #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_fetch_venue_by_uuid_success(platform_club):
    """Successful GraphQL venue response is mapped to the expected dict shape."""
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.post_json = AsyncMock(return_value=_VENUE_RESPONSE_1)

    venue = await scraper._fetch_venue_by_uuid(_V3_UUID)

    assert venue is not None
    assert venue["uuid"] == _V3_UUID
    assert venue["name"] == "The Comedy Studio"
    assert venue["website"] == "https://thecomedystudio.com"
    assert venue["address"] == "5 John F. Kennedy St"
    assert venue["city"] == "Cambridge"
    assert venue["state"] == "MA"
    assert venue["zipCode"] == "02138"


@pytest.mark.asyncio
async def test_fetch_venue_by_uuid_graphql_error_returns_none(platform_club):
    """GraphQL errors in the venue response return None without raising."""
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.post_json = AsyncMock(
        return_value={"errors": [{"message": "venue not found"}]}
    )

    venue = await scraper._fetch_venue_by_uuid(_V3_UUID)

    assert venue is None


@pytest.mark.asyncio
async def test_fetch_venue_by_uuid_network_failure_returns_none(platform_club):
    """Network exception for venue query returns None without raising."""
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.post_json = AsyncMock(side_effect=RuntimeError("connection refused"))

    venue = await scraper._fetch_venue_by_uuid(_V3_UUID)

    assert venue is None


@pytest.mark.asyncio
async def test_fetch_venue_by_uuid_null_venue_data_returns_none(platform_club):
    """Response with data.venue = null returns None."""
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.post_json = AsyncMock(return_value={"data": {"venue": None}})

    venue = await scraper._fetch_venue_by_uuid(_V3_UUID)

    assert venue is None


# ------------------------------------------------------------------ #
# _fetch_v3_venues — integration of CDX + GraphQL                   #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_fetch_v3_venues_returns_venue_list(platform_club):
    """Full flow: CDX yields two UUIDs, venue query returns both venues."""
    scraper = SeatEngineV3NationalScraper(platform_club)

    with patch.object(
        scraper, "_discover_uuids_from_cdx", new=AsyncMock(return_value=[_V3_UUID, _V3_UUID2])
    ):
        with patch.object(
            scraper,
            "_fetch_venue_by_uuid",
            side_effect=[_make_venue_dict(_V3_UUID), _make_venue_dict(_V3_UUID2, name="Cafe Coda")],
        ):
            venues = await scraper._fetch_v3_venues()

    assert len(venues) == 2
    assert venues[0]["uuid"] == _V3_UUID
    assert venues[1]["name"] == "Cafe Coda"


@pytest.mark.asyncio
async def test_fetch_v3_venues_returns_empty_when_cdx_empty(platform_club):
    """CDX finding no UUIDs means _fetch_v3_venues returns []."""
    scraper = SeatEngineV3NationalScraper(platform_club)

    with patch.object(scraper, "_discover_uuids_from_cdx", new=AsyncMock(return_value=[])):
        venues = await scraper._fetch_v3_venues()

    assert venues == []


@pytest.mark.asyncio
async def test_fetch_v3_venues_skips_failed_venue_fetches(platform_club):
    """A failed venue GraphQL fetch does not abort other venues."""
    scraper = SeatEngineV3NationalScraper(platform_club)

    with patch.object(
        scraper, "_discover_uuids_from_cdx", new=AsyncMock(return_value=[_V3_UUID, _V3_UUID2])
    ):
        with patch.object(
            scraper,
            "_fetch_venue_by_uuid",
            side_effect=[_make_venue_dict(_V3_UUID), None],
        ):
            venues = await scraper._fetch_v3_venues()

    assert len(venues) == 1
    assert venues[0]["uuid"] == _V3_UUID


# ------------------------------------------------------------------ #
# _upsert_venues — exception isolation per venue                     #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_upsert_venues_exception_does_not_abort_loop(platform_club):
    """A DB exception for one venue does not prevent others from being upserted."""
    venues = [
        _make_venue_dict(_V3_UUID, name="Good Club"),
        _make_venue_dict(_V3_UUID2, name="Bad Club"),
        _make_venue_dict("aaaaaaaa-0000-0000-0000-000000000003", name="Also Good Club"),
    ]
    good_club = _make_club()

    def _upsert(venue):
        if venue.get("name") == "Bad Club":
            raise RuntimeError("DB error")
        return good_club

    scraper = SeatEngineV3NationalScraper(platform_club)

    with patch.object(
        scraper._club_handler,
        "upsert_for_seatengine_v3_venue",
        side_effect=_upsert,
    ) as mock_upsert:
        await scraper._upsert_venues(venues)

    assert mock_upsert.call_count == 3


@pytest.mark.asyncio
async def test_upsert_venues_skips_invalid_venues(platform_club):
    """Venues rejected by the handler (None return) are counted as skipped."""
    venues = [_make_venue_dict(_V3_UUID)]
    scraper = SeatEngineV3NationalScraper(platform_club)

    with patch.object(
        scraper._club_handler,
        "upsert_for_seatengine_v3_venue",
        return_value=None,
    ) as mock_upsert:
        await scraper._upsert_venues(venues)

    assert mock_upsert.call_count == 1
