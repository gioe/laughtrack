"""
Pipeline smoke tests for SeatEngineV3Scraper.

Verifies that collect_scraping_targets(), get_data(), and transform_data()
wire together correctly for the SeatEngine v3 (GraphQL) platform.

v3 venues use a UUID-based identifier and fetch events via a single
GraphQL query to services.seatengine.com/api/v3/public.
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.api.seatengine_v3.scraper import SeatEngineV3Scraper
from laughtrack.scrapers.implementations.api.seatengine_v3.page_data import SeatEngineV3PageData


VENUE_UUID = "cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3"
VENUE_URL = "https://v-cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3.seatengine.net"


def _club(seatengine_id: str = VENUE_UUID) -> Club:
    return Club(
        id=999,
        name="The Comedy Studio",
        address="5 John F. Kennedy St",
        website="https://thecomedystudio.com",
        scraping_url=VENUE_URL,
        popularity=0,
        zip_code="02138",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        seatengine_id=seatengine_id,
    )


def _graphql_response(
    event_name: str = "Tuesday Night Comedy",
    comedian: str = "Alice Smith",
    event_uuid: str = "ev-uuid-1",
    show_uuid: str = "sh-uuid-1",
    price_cents: int = 1500,
) -> dict:
    """Minimal SeatEngine v3 GraphQL eventsList response."""
    return {
        "data": {
            "eventsList": {
                "events": [
                    {
                        "uuid": event_uuid,
                        "name": event_name,
                        "status": "UPCOMING",
                        "soldOut": False,
                        "page": {"path": "/events/tuesday-night"},
                        "talents": [{"name": comedian}],
                        "shows": [
                            {
                                "uuid": show_uuid,
                                "startDateTime": "2026-04-15T20:00:00-04:00",
                                "soldOut": False,
                                "status": "UPCOMING",
                                "inventories": [
                                    {
                                        "uuid": "inv-1",
                                        "title": "General Admission",
                                        "name": "GA",
                                        "price": price_cents,
                                        "active": True,
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }
    }


# ---------------------------------------------------------------------------
# collect_scraping_targets()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_venue_uuid():
    """collect_scraping_targets() returns the club's seatengine_id (UUID) as the sole target."""
    scraper = SeatEngineV3Scraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert targets == [VENUE_UUID]


def test_init_raises_when_seatengine_id_missing():
    """SeatEngineV3Scraper raises ValueError when seatengine_id is absent."""
    club = _club(seatengine_id="")
    with pytest.raises(ValueError, match="seatengine_id"):
        SeatEngineV3Scraper(club)


# ---------------------------------------------------------------------------
# get_data() — posts GraphQL and returns SeatEngineV3PageData
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events():
    """get_data() wraps GraphQL results in SeatEngineV3PageData with one record per show."""
    scraper = SeatEngineV3Scraper(_club())
    scraper.post_json = AsyncMock(return_value=_graphql_response())

    result = await scraper.get_data(VENUE_UUID)

    assert isinstance(result, SeatEngineV3PageData)
    assert len(result.event_list) == 1
    assert result.event_list[0]["event_name"] == "Tuesday Night Comedy"
    assert result.is_transformable()


@pytest.mark.asyncio
async def test_get_data_returns_empty_page_data_on_graphql_error():
    """get_data() returns empty SeatEngineV3PageData when the GraphQL response has errors."""
    scraper = SeatEngineV3Scraper(_club())
    scraper.post_json = AsyncMock(
        return_value={"errors": [{"message": "venue not found"}]}
    )

    result = await scraper.get_data(VENUE_UUID)

    assert isinstance(result, SeatEngineV3PageData)
    assert result.event_list == []
    assert not result.is_transformable()


@pytest.mark.asyncio
async def test_get_data_returns_empty_page_data_on_request_failure():
    """get_data() returns empty SeatEngineV3PageData when post_json raises."""
    scraper = SeatEngineV3Scraper(_club())
    scraper.post_json = AsyncMock(side_effect=RuntimeError("connection refused"))

    result = await scraper.get_data(VENUE_UUID)

    assert isinstance(result, SeatEngineV3PageData)
    assert result.event_list == []


# ---------------------------------------------------------------------------
# transform_data() — wires get_data → Show objects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_data_extracts_show_name_lineup_and_ticket():
    """transform_data() produces Show objects with name, lineup, and ticket price."""
    scraper = SeatEngineV3Scraper(_club())
    scraper.post_json = AsyncMock(return_value=_graphql_response(comedian="Alice Smith", price_cents=2000))

    page_data = await scraper.get_data(VENUE_UUID)
    shows = scraper.transform_data(page_data, source_url=VENUE_UUID)

    assert len(shows) == 1
    show = shows[0]
    assert show.name == "Tuesday Night Comedy"

    assert len(show.lineup) == 1
    assert show.lineup[0].name == "Alice Smith"

    # 2000 cents → $20.00
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 20.0
    assert not show.tickets[0].sold_out


@pytest.mark.asyncio
async def test_transform_data_returns_empty_for_empty_page_data():
    """transform_data() returns [] when page_data has no events."""
    scraper = SeatEngineV3Scraper(_club())
    scraper.post_json = AsyncMock(return_value={"errors": [{"message": "no events"}]})

    page_data = await scraper.get_data(VENUE_UUID)
    shows = scraper.transform_data(page_data, source_url=VENUE_UUID)

    assert shows == []
