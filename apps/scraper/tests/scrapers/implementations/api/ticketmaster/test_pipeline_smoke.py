"""
Parametrized pipeline smoke tests covering all live_nation (Ticketmaster) venues.

Exercises TicketmasterScraper.get_data() → TicketmasterPageData →
transformation_pipeline.transform() for every venue that uses scraper='live_nation'.

Adding a new live_nation venue? Append a _VenueFixture entry to _VENUES below —
no new test file needed.

This catches silent empty-result regressions where TicketmasterClient returns
events but the transformation pipeline drops them due to can_transform() failures.
"""

import dataclasses
import importlib.util
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.ticketmaster.data import TicketmasterPageData
from laughtrack.scrapers.implementations.api.ticketmaster.scraper import TicketmasterScraper


@dataclasses.dataclass
class _VenueFixture:
    venue_id: str
    name: str
    address: str
    website: str
    zip_code: str
    tz: str
    event_id: str       # synthetic fake ID — never a real Ticketmaster event ID
    performer: str      # default performer name used in test events


_VENUES = [
    _VenueFixture(
        venue_id="KovZpZAEvtFA",
        name="Punch Line Philly",
        address="33 E. Laurel Street",
        website="https://www.punchlinephilly.com",
        zip_code="19123",
        tz="America/New_York",
        event_id="FAKE0000PLPHL001",
        performer="Devon Walker",
    ),
    _VenueFixture(
        venue_id="KovZpZAEkFEA",
        name="Cobb's Comedy Club",
        address="915 Columbus Ave",
        website="https://www.cobbscomedy.com",
        zip_code="94133",
        tz="America/Los_Angeles",
        event_id="FAKE0000COBBS001",
        performer="Sam Tallent",
    ),
    _VenueFixture(
        venue_id="KovZpZAE6e7A",
        name="Punch Line Comedy Club - San Francisco",
        address="444 Battery Street",
        website="https://www.punchlinecomedyclub.com",
        zip_code="94111",
        tz="America/Los_Angeles",
        event_id="FAKE0000PLSF001",
        performer="Ivan Decker",
    ),
    _VenueFixture(
        venue_id="KovZ917ARGO",
        name="Punch Line Comedy Club Houston",
        address="1204 Caroline Street",
        website="https://www.punchlinehtx.com",
        zip_code="77002",
        tz="America/Chicago",
        event_id="FAKE0000PLHTX001",
        performer="Jimmy Dore",
    ),
    _VenueFixture(
        venue_id="KovZpZAFJEvA",
        name="Just the Funny",
        address="3119 Coral Way",
        website="https://www.justthefunny.com",
        zip_code="33145",
        tz="America/New_York",
        event_id="FAKE0000JTFNY001",
        performer="Friday Night Live - Improv Comedy Miami Show",
    ),
    _VenueFixture(
        venue_id="KovZpZAE6EtA",
        name="The Second City",
        address="1616 N Wells St",
        website="https://www.secondcity.com",
        zip_code="60614",
        tz="America/Chicago",
        event_id="FAKE00002CTY001",
        performer="The Second City Mainstage 114th Revue",
    ),
]


def _club(v):
    # type: (_VenueFixture) -> Club
    return Club(
        id=999,
        name=v.name,
        address=v.address,
        website=v.website,
        scraping_url=f"ticketmaster/{v.venue_id}",
        popularity=0,
        zip_code=v.zip_code,
        phone_number="",
        visible=True,
        timezone=v.tz,
        ticketmaster_id=v.venue_id,
        scraper="live_nation",
    )


def _make_api_event(v, name=None):
    # type: (_VenueFixture, Optional[str]) -> dict
    performer = name if name is not None else v.performer
    return {
        "id": v.event_id,
        "name": performer,
        "url": f"https://www.ticketmaster.com/event/{v.event_id}",
        "dates": {
            "start": {"localDate": "2026-04-10", "localTime": "20:00:00"},
            "status": {"code": "onsale"},
        },
        "sales": {"public": {"startDateTime": "2026-01-01T00:00:00Z"}},
        "priceRanges": [{"type": "standard", "min": 25.0, "max": 45.0}],
        "_embedded": {
            "venues": [{"id": v.venue_id, "name": v.name}],
            "attractions": [{"name": performer}],
        },
    }


def _fake_show(v, name=None):
    # type: (_VenueFixture, Optional[str]) -> Show
    return Show(
        name=name if name is not None else v.performer,
        club_id=999,
        date=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
        show_page_url=f"https://www.ticketmaster.com/event/{v.event_id}",
    )


# ---------------------------------------------------------------------------
# Parametrized smoke tests — one run per venue in _VENUES
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("v", _VENUES, ids=lambda v: v.venue_id)
async def test_get_data_returns_page_data_with_events(v):
    """
    get_data() returns TicketmasterPageData with at least one event
    when TicketmasterClient.fetch_events() returns events.
    """
    scraper = TicketmasterScraper(_club(v))
    api_url = f"https://app.ticketmaster.com/discovery/v2/events.json?venueId={v.venue_id}"

    mock_client = MagicMock()
    mock_client.fetch_events = AsyncMock(return_value=[_make_api_event(v)])
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
@pytest.mark.parametrize("v", _VENUES, ids=lambda v: v.venue_id)
async def test_get_data_returns_none_on_exception(v):
    """get_data() returns None when TicketmasterClient.fetch_events() raises."""
    scraper = TicketmasterScraper(_club(v))
    api_url = f"https://app.ticketmaster.com/discovery/v2/events.json?venueId={v.venue_id}"

    mock_client = MagicMock()
    mock_client.fetch_events = AsyncMock(side_effect=RuntimeError("API unreachable"))
    with patch(
        "laughtrack.scrapers.implementations.api.ticketmaster.scraper.TicketmasterClient",
        return_value=mock_client,
    ):
        result = await scraper.get_data(api_url)

    assert result is None, (
        "get_data() should return None when TicketmasterClient raises — "
        "check exception handling in TicketmasterScraper.get_data()"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("v", _VENUES, ids=lambda v: v.venue_id)
async def test_get_data_returns_non_transformable_when_api_returns_empty(v):
    """get_data() returns a non-transformable TicketmasterPageData when fetch_events() returns []."""
    scraper = TicketmasterScraper(_club(v))
    api_url = f"https://app.ticketmaster.com/discovery/v2/events.json?venueId={v.venue_id}"

    mock_client = MagicMock()
    mock_client.fetch_events = AsyncMock(return_value=[])
    with patch(
        "laughtrack.scrapers.implementations.api.ticketmaster.scraper.TicketmasterClient",
        return_value=mock_client,
    ):
        result = await scraper.get_data(api_url)

    assert isinstance(result, TicketmasterPageData) and not result.is_transformable(), (
        "get_data() should return a non-transformable TicketmasterPageData when the API returns 0 events"
    )


@pytest.mark.parametrize("v", _VENUES, ids=lambda v: v.venue_id)
def test_transformation_pipeline_produces_shows(v):
    """
    transformation_pipeline.transform() returns at least one Show
    when given TicketmasterPageData with a valid event dict.

    Catches type-mismatch regressions where can_transform() returns False
    for Ticketmaster API dicts, silently dropping all events.

    TicketmasterClient.__init__ raises ValueError when TICKETMASTER_API_KEY is
    absent (e.g. CI). Patch the client in the transformer module so this test
    runs hermetically without a live API key.
    """
    scraper = TicketmasterScraper(_club(v))
    page_data = TicketmasterPageData(event_list=[_make_api_event(v)])

    mock_client = MagicMock()
    mock_client.create_show.return_value = _fake_show(v)
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


@pytest.mark.parametrize("v", _VENUES, ids=lambda v: v.venue_id)
def test_transformation_pipeline_preserves_event_name(v):
    """Show name from the pipeline matches the source event name."""
    scraper = TicketmasterScraper(_club(v))
    event_name = "Test Comedian"
    event = _make_api_event(v, name=event_name)
    page_data = TicketmasterPageData(event_list=[event])

    mock_client = MagicMock()
    mock_client.create_show.return_value = _fake_show(v, name=event_name)
    with patch(
        "laughtrack.scrapers.implementations.api.ticketmaster.transformer.TicketmasterClient",
        return_value=mock_client,
    ):
        shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert shows[0].name == event_name


@pytest.mark.asyncio
@pytest.mark.parametrize("v", _VENUES, ids=lambda v: v.venue_id)
async def test_discover_urls_returns_api_endpoint(v):
    """discover_urls() returns the Ticketmaster API endpoint containing the venue ID."""
    scraper = TicketmasterScraper(_club(v))
    urls = await scraper.discover_urls()

    assert len(urls) == 1
    assert v.venue_id in urls[0], (
        f"Expected venue ID {v.venue_id!r} in discover_urls() result, got: {urls}"
    )
