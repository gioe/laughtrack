"""
Smoke tests for Laugh Factory Covina using TixrScraper.

Covina's Tixr group page (tixr.com/groups/laughfactorycovina, group id 1613)
is a known DataDome-blocked source: TixrScraper short-circuits the direct
page scrape entirely and serves events from the Tixr group-events API
fallback through the residential proxy (skip_direct=True, single page).
These tests assert that short-circuit behavior — no direct Tixr page fetch
ever happens for this venue. Full HTML-pipeline coverage (URL extraction,
Org JSON-LD filtering) lives in
tests/scrapers/implementations/api/tixr/test_pipeline_smoke.py against
non-blocked fixtures.
"""

import importlib.util
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.scrapers.implementations.api.tixr.scraper import TixrScraper
from laughtrack.scrapers.implementations.api.tixr.data import TixrPageData


GROUP_URL = "https://www.tixr.com/groups/laughfactorycovina"
EVENT_URL = "https://www.tixr.com/groups/laughfactorycovina/events/comedy-night-12345"


def _club(metadata: dict | None = {"tixr_group_id": 1613}) -> Club:
    _c = Club(id=200, name='Laugh Factory Covina', address='104 N Citrus Ave', website='https://www.laughfactory.com/covina', popularity=0, zip_code='91723', phone_number='', visible=True, timezone='America/Los_Angeles')
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform='tixr',
        scraper_key='tixr',
        source_url=GROUP_URL,
        external_id=None,
        metadata=metadata,
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _tixr_event() -> TixrEvent:
    show = Show(
        name="Comedy Night at Laugh Factory Covina",
        club_id=200,
        # Far-future date per the no-time-bomb test convention
        date=datetime(2099, 4, 10, 19, 30, tzinfo=timezone.utc),
        show_page_url=EVENT_URL,
        lineup=[],
        tickets=[Ticket(price=20.0, purchase_url=EVENT_URL, sold_out=False, type="General Admission")],
        supplied_tags=["event"],
        description=None,
        timezone="America/Los_Angeles",
        room="",
    )
    return TixrEvent.from_tixr_show(show=show, source_url=EVENT_URL, event_id="12345")


def _blocked_fetch_mock() -> AsyncMock:
    """
    Direct-fetch mock that fails loudly if called. get_data() swallows
    exceptions into a None return, so callers must ALSO assert_not_called()
    on this mock after the call under test.
    """
    return AsyncMock(
        side_effect=AssertionError(
            "Known DataDome-blocked Tixr group must not fetch its page directly"
        )
    )


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_skips_group_page_discovery(monkeypatch):
    """
    collect_scraping_targets() returns only the group URL without fetching the
    DataDome-blocked group page for pagination discovery.
    """
    scraper = TixrScraper(_club())
    fetch_mock = _blocked_fetch_mock()
    monkeypatch.setattr(scraper, "_fetch_calendar_html", fetch_mock)

    assert await scraper.collect_scraping_targets() == [GROUP_URL]
    fetch_mock.assert_not_called()


@pytest.mark.asyncio
async def test_get_data_short_circuits_to_group_events_api_fallback(monkeypatch):
    """
    get_data() never fetches the blocked group page — it goes straight to the
    Tixr group-events API through the residential proxy (skip_direct=True,
    single page) and returns TixrPageData from the fallback events.
    """
    monkeypatch.setenv("TIXR_GROUP_EVENTS_API_FALLBACK", "1")
    scraper = TixrScraper(_club())
    event = _tixr_event()

    fetch_mock = _blocked_fetch_mock()
    monkeypatch.setattr(scraper, "_fetch_calendar_html", fetch_mock)
    scraper.tixr_client.fetch_group_events = AsyncMock(return_value=[event])
    scraper.tixr_client.get_event_detail_from_url = AsyncMock()

    result = await scraper.get_data(GROUP_URL)

    assert isinstance(result, TixrPageData), (
        "get_data() did not return TixrPageData from the group-events API fallback"
    )
    assert [e.event_id for e in result.event_list] == ["12345"]
    scraper.tixr_client.fetch_group_events.assert_awaited_once_with(
        "1613",
        max_pages=1,
        skip_direct=True,
    )
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()
    fetch_mock.assert_not_called()


@pytest.mark.asyncio
async def test_get_data_short_circuits_via_url_fragment_when_metadata_missing(monkeypatch):
    """
    The URL-fragment safety net (_KNOWN_DATADOME_GROUP_URL_FRAGMENTS) still
    short-circuits when the scraping source has no tixr_group_id metadata —
    group-id resolution falls back to the URL slug.
    """
    monkeypatch.setenv("TIXR_GROUP_EVENTS_API_FALLBACK", "1")
    scraper = TixrScraper(_club(metadata={}))
    event = _tixr_event()

    fetch_mock = _blocked_fetch_mock()
    monkeypatch.setattr(scraper, "_fetch_calendar_html", fetch_mock)
    scraper.tixr_client.fetch_group_events = AsyncMock(return_value=[event])
    scraper.tixr_client.get_event_detail_from_url = AsyncMock()

    result = await scraper.get_data(GROUP_URL)

    assert isinstance(result, TixrPageData)
    assert [e.event_id for e in result.event_list] == ["12345"]
    scraper.tixr_client.fetch_group_events.assert_awaited_once_with(
        "laughfactorycovina",
        max_pages=1,
        skip_direct=True,
    )
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()
    fetch_mock.assert_not_called()


@pytest.mark.asyncio
async def test_get_data_returns_none_when_fallback_has_no_events(monkeypatch):
    """
    get_data() returns None when the group-events API fallback yields no
    events — still without ever attempting the blocked direct fetch.
    """
    monkeypatch.setenv("TIXR_GROUP_EVENTS_API_FALLBACK", "1")
    scraper = TixrScraper(_club())

    fetch_mock = _blocked_fetch_mock()
    monkeypatch.setattr(scraper, "_fetch_calendar_html", fetch_mock)
    scraper.tixr_client.fetch_group_events = AsyncMock(return_value=[])

    result = await scraper.get_data(GROUP_URL)

    assert result is None
    scraper.tixr_client.fetch_group_events.assert_awaited_once()
    fetch_mock.assert_not_called()


@pytest.mark.asyncio
async def test_get_data_returns_none_when_fallback_disabled(monkeypatch):
    """
    With the group-events API fallback disabled, get_data() returns None and
    skips both the blocked direct fetch and the group-events API call.
    """
    monkeypatch.delenv("TIXR_GROUP_EVENTS_API_FALLBACK", raising=False)
    scraper = TixrScraper(_club())

    fetch_mock = _blocked_fetch_mock()
    monkeypatch.setattr(scraper, "_fetch_calendar_html", fetch_mock)
    scraper.tixr_client.fetch_group_events = AsyncMock(return_value=[_tixr_event()])

    result = await scraper.get_data(GROUP_URL)

    assert result is None
    scraper.tixr_client.fetch_group_events.assert_not_called()
    fetch_mock.assert_not_called()


def test_can_transform_accepts_tixr_event():
    """
    Transformation pipeline accepts TixrEvent — catches type-mismatch regressions
    where the transformer's can_transform() silently rejects all events.
    """
    scraper = TixrScraper(_club())
    event = _tixr_event()
    page_data = TixrPageData(event_list=[event])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert shows is not None and len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 shows for a valid TixrEvent — "
        "check TixrVenueEventTransformer.can_transform()"
    )
