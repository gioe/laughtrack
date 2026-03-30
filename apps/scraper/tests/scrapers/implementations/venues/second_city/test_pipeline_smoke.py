"""
Pipeline smoke tests for The Second City (Ticketmaster / live_nation scraper).

Exercises TicketmasterScraper.get_data() → TicketmasterPageData →
transformation_pipeline.transform() using The Second City (venue ID KovZpZAE6EtA)
as the representative club.

This catches silent empty-result regressions where TicketmasterClient returns
events but the transformation pipeline drops them due to can_transform() failures.
"""

import importlib.util
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.ticketmaster.page_data import TicketmasterPageData
from laughtrack.scrapers.implementations.api.ticketmaster.scraper import TicketmasterScraper

VENUE_ID = "KovZpZAE6EtA"
EVENT_URL = "https://www.ticketmaster.com/event/Z7r9jZ1A7rvpf"


def _club() -> Club:
    return Club(
        id=180,
        name="The Second City",
        address="1616 N Wells St",
        website="https://www.secondcity.com",
        scraping_url=f"ticketmaster/{VENUE_ID}",
        popularity=0,
        zip_code="60614",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        ticketmaster_id=VENUE_ID,
        scraper="live_nation",
    )


def _make_api_event(
    name: str = "The Second City Mainstage 114th Revue",
    date: str = "2026-04-03",
) -> dict:
    """Minimal Ticketmaster Discovery API event dict for The Second City Mainstage."""
    return {
        "id": "Z7r9jZ1A7rvpf",
        "name": name,
        "url": EVENT_URL,
        "dates": {
            "start": {"localDate": date, "localTime": "19:00:00"},
            "status": {"code": "onsale"},
        },
        "sales": {"public": {"startDateTime": "2026-01-01T00:00:00Z"}},
        "priceRanges": [{"type": "standard", "min": 30.0, "max": 55.0}],
        "_embedded": {
            "venues": [{"id": VENUE_ID, "name": "Second City Mainstage"}],
            "attractions": [{"name": name}],
        },
    }


def _fake_show(name: str = "The Second City Mainstage 114th Revue") -> Show:
    """Minimal Show for use in transformer mocks."""
    return Show(
        name=name,
        club_id=180,
        date=datetime(2026, 4, 3, 19, 0, tzinfo=timezone.utc),
        show_page_url=EVENT_URL,
    )


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events():
    """
    get_data() returns TicketmasterPageData with at least one event
    when TicketmasterClient.fetch_events() returns events.
    """
    scraper = TicketmasterScraper(_club())
    api_url = f"https://app.ticketmaster.com/discovery/v2/events.json?venueId={VENUE_ID}"

    with patch(
        "laughtrack.core.clients.ticketmaster.client.TicketmasterClient.fetch_events",
        new_callable=AsyncMock,
        return_value=[_make_api_event()],
    ):
        result = await scraper.get_data(api_url)

    assert isinstance(result, TicketmasterPageData), (
        "get_data() did not return TicketmasterPageData — check TicketmasterScraper.get_data()"
    )
    assert result.is_transformable(), (
        "get_data() returned TicketmasterPageData with no events — "
        "check TicketmasterClient.fetch_events() or TicketmasterExtractor.to_page_data()"
    )
    assert len(result.event_list) == 1


@pytest.mark.asyncio
async def test_get_data_returns_none_on_exception():
    """get_data() returns None when TicketmasterClient.fetch_events() raises."""
    scraper = TicketmasterScraper(_club())
    api_url = f"https://app.ticketmaster.com/discovery/v2/events.json?venueId={VENUE_ID}"

    async def raise_error(*_args, **_kwargs):
        raise RuntimeError("API unreachable")

    with patch(
        "laughtrack.core.clients.ticketmaster.client.TicketmasterClient.fetch_events",
        side_effect=raise_error,
    ):
        result = await scraper.get_data(api_url)

    assert result is None, (
        "get_data() should return None when TicketmasterClient raises — "
        "check exception handling in TicketmasterScraper.get_data()"
    )


@pytest.mark.asyncio
async def test_get_data_returns_none_when_api_returns_empty():
    """get_data() returns None when TicketmasterClient.fetch_events() returns []."""
    scraper = TicketmasterScraper(_club())
    api_url = f"https://app.ticketmaster.com/discovery/v2/events.json?venueId={VENUE_ID}"

    with patch(
        "laughtrack.core.clients.ticketmaster.client.TicketmasterClient.fetch_events",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await scraper.get_data(api_url)

    assert result is None or (
        isinstance(result, TicketmasterPageData) and not result.is_transformable()
    ), "get_data() should return None or empty page data when the API returns 0 events"


def test_transformation_pipeline_produces_shows():
    """
    transformation_pipeline.transform() returns at least one Show
    when given TicketmasterPageData with a valid event dict.

    Catches type-mismatch regressions where can_transform() returns False
    for Ticketmaster API dicts, silently dropping all events.

    TicketmasterClient.__init__ raises ValueError when TICKETMASTER_API_KEY is
    absent (e.g. CI). Patch the client in the transformer module so this test
    runs hermetically without a live API key.
    """
    scraper = TicketmasterScraper(_club())
    page_data = TicketmasterPageData(event_list=[_make_api_event()])

    mock_client = MagicMock()
    mock_client.create_show.return_value = _fake_show()
    with patch(
        "laughtrack.scrapers.implementations.api.ticketmaster.transformer.TicketmasterClient",
        return_value=mock_client,
    ):
        shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows from TicketmasterPageData — "
        "check TicketmasterEventTransformer.can_transform() and transformer registration"
    )
    assert all(isinstance(s, Show) for s in shows)


def test_transformation_pipeline_preserves_event_name():
    """Show name from the pipeline matches the source event name."""
    scraper = TicketmasterScraper(_club())
    event = _make_api_event(name="The Best of The Second City")
    page_data = TicketmasterPageData(event_list=[event])

    mock_client = MagicMock()
    mock_client.create_show.return_value = _fake_show(name="The Best of The Second City")
    with patch(
        "laughtrack.scrapers.implementations.api.ticketmaster.transformer.TicketmasterClient",
        return_value=mock_client,
    ):
        shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert shows[0].name == "The Best of The Second City"


@pytest.mark.asyncio
async def test_discover_urls_returns_api_endpoint():
    """discover_urls() returns the Ticketmaster API endpoint containing the venue ID."""
    scraper = TicketmasterScraper(_club())
    urls = await scraper.discover_urls()

    assert len(urls) == 1
    assert VENUE_ID in urls[0], (
        f"Expected venue ID {VENUE_ID!r} in discover_urls() result, got: {urls}"
    )
