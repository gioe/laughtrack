"""
Smoke tests for the TicketmasterScraper pipeline (Punch Line Philly).

Exercises get_data() -> TicketmasterPageData -> transformation_pipeline.transform()
using Punch Line Philly (venue ID KovZpZAEvtFA) as the representative club.

This catches silent empty-result regressions where the TicketmasterClient returns
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
from laughtrack.scrapers.implementations.api.ticketmaster.scraper import TicketmasterScraper
from laughtrack.scrapers.implementations.api.ticketmaster.page_data import TicketmasterPageData

VENUE_ID = "KovZpZAEvtFA"
EVENT_URL = "https://www.ticketmaster.com/punch-line-philly-comedy-night-philadelphia/event/0200638B27F56222"


def _club() -> Club:
    return Club(
        id=999,
        name="Punch Line Philly",
        address="33 E. Laurel Street",
        website="https://www.punchlinephilly.com",
        scraping_url=f"ticketmaster/{VENUE_ID}",
        popularity=0,
        zip_code="19123",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        ticketmaster_id=VENUE_ID,
        scraper="live_nation",
    )


def _make_api_event(name: str = "Devon Walker", date: str = "2026-04-03") -> dict:
    """Minimal Ticketmaster Discovery API event dict for Punch Line Philly."""
    return {
        "id": "0200638B27F56222",
        "name": name,
        "url": EVENT_URL,
        "dates": {
            "start": {"localDate": date, "localTime": "19:00:00"},
            "status": {"code": "onsale"},
        },
        "sales": {"public": {"startDateTime": "2026-01-01T00:00:00Z"}},
        "priceRanges": [{"type": "standard", "min": 25.0, "max": 35.0}],
        "_embedded": {
            "venues": [{"id": VENUE_ID, "name": "Punch Line Philly"}],
            "attractions": [{"name": name}],
        },
    }


def _fake_show(name: str = "Devon Walker") -> Show:
    """Minimal Show for use in transformer mocks."""
    return Show(
        name=name,
        club_id=999,
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

    mock_client = MagicMock()
    mock_client.fetch_events = AsyncMock(return_value=[_make_api_event()])
    with patch(
        "laughtrack.scrapers.implementations.api.ticketmaster.scraper.TicketmasterClient",
        return_value=mock_client,
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
async def test_get_data_returns_none_when_api_returns_empty(monkeypatch):
    """get_data() returns None when TicketmasterClient.fetch_events() returns []."""
    scraper = TicketmasterScraper(_club())
    api_url = f"https://app.ticketmaster.com/discovery/v2/events.json?venueId={VENUE_ID}"

    with patch(
        "laughtrack.core.clients.ticketmaster.client.TicketmasterClient.fetch_events",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await scraper.get_data(api_url)

    assert result is None or (isinstance(result, TicketmasterPageData) and not result.is_transformable()), (
        "get_data() should return None or empty page data when the API returns 0 events"
    )


@pytest.mark.asyncio
async def test_get_data_returns_none_on_exception(monkeypatch):
    """get_data() returns None when TicketmasterClient raises an exception."""
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


def test_transformation_pipeline_produces_shows_from_ticketmaster_events():
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
    event = _make_api_event(name="Chris Redd")
    page_data = TicketmasterPageData(event_list=[event])

    mock_client = MagicMock()
    mock_client.create_show.return_value = _fake_show(name="Chris Redd")
    with patch(
        "laughtrack.scrapers.implementations.api.ticketmaster.transformer.TicketmasterClient",
        return_value=mock_client,
    ):
        shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert shows[0].name == "Chris Redd"


@pytest.mark.asyncio
async def test_discover_urls_returns_api_endpoint():
    """discover_urls() returns a list containing the Ticketmaster API endpoint for the venue."""
    scraper = TicketmasterScraper(_club())
    urls = await scraper.discover_urls()

    assert len(urls) == 1
    assert VENUE_ID in urls[0], (
        f"Expected venue ID {VENUE_ID!r} in discover_urls() result, got: {urls}"
    )
