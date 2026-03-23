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
from laughtrack.core.entities.club.model import Club


_V3_UUID = "cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3"
_V3_UUID2 = "aa3b1111-1111-1111-1111-000000000001"


@pytest.fixture
def platform_club() -> Club:
    """Minimal 'platform' club row that triggers the v3 national scraper."""
    return Club(
        id=999,
        name="SeatEngine V3 National",
        address="",
        website="",
        scraping_url="www.seatengine.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        scraper="seatengine_v3_national",
    )


def _make_venue_dict(uuid=_V3_UUID, name="The Comedy Studio", address="1236 Mass Ave, Cambridge, MA", zip_code="02139"):
    return {"uuid": uuid, "name": name, "address": address, "zipCode": zip_code, "website": "https://thecomedystudio.com", "city": "Cambridge", "state": "MA"}


def _make_club(club_id=42, name="The Comedy Studio", seatengine_id=_V3_UUID):
    return Club(
        id=club_id,
        name=name,
        address="1236 Mass Ave, Cambridge, MA",
        website="https://thecomedystudio.com",
        scraping_url=f"https://v-{seatengine_id}.seatengine.net",
        popularity=0,
        zip_code="02139",
        phone_number="",
        visible=True,
        scraper="seatengine_v3",
        seatengine_id=seatengine_id,
    )


# ------------------------------------------------------------------ #
# collect_scraping_targets                                             #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_collect_targets_returns_national(platform_club):
    s = SeatEngineV3NationalScraper(platform_club)
    targets = await s.collect_scraping_targets()
    assert targets == ["national"]


# ------------------------------------------------------------------ #
# scrape_async — empty API response                                   #
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
    venues = [_make_venue_dict(_V3_UUID), _make_venue_dict(_V3_UUID2, name="Brokerage Comedy Club")]
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
# _fetch_v3_venues — GraphQL error path                              #
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_fetch_v3_venues_returns_empty_on_graphql_errors(platform_club):
    """GraphQL errors in the response result in [] without raising."""
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.post_json = AsyncMock(return_value={"errors": [{"message": "Unknown field 'venuesList'"}]})

    venues = await scraper._fetch_v3_venues()

    assert venues == []


@pytest.mark.asyncio
async def test_fetch_v3_venues_returns_empty_on_network_failure(platform_club):
    """Network exception results in [] without raising."""
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.post_json = AsyncMock(side_effect=RuntimeError("connection timeout"))

    venues = await scraper._fetch_v3_venues()

    assert venues == []


@pytest.mark.asyncio
async def test_fetch_v3_venues_returns_empty_on_null_response(platform_club):
    """None response from post_json results in []."""
    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.post_json = AsyncMock(return_value=None)

    venues = await scraper._fetch_v3_venues()

    assert venues == []


@pytest.mark.asyncio
async def test_fetch_v3_venues_returns_venue_list(platform_club):
    """Successful response returns the venues array."""
    venues_data = [_make_venue_dict(_V3_UUID), _make_venue_dict(_V3_UUID2, name="Brokerage Comedy Club")]
    response = {"data": {"venuesList": {"venues": venues_data}}}

    scraper = SeatEngineV3NationalScraper(platform_club)
    scraper.post_json = AsyncMock(return_value=response)

    venues = await scraper._fetch_v3_venues()

    assert len(venues) == 2
    assert venues[0]["uuid"] == _V3_UUID
    assert venues[1]["name"] == "Brokerage Comedy Club"


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
        # Should not raise even though one venue errors
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
