"""
Smoke tests for the Laugh Boston scraper pipeline.

Verifies that get_data() returns LaughBostonPageData with at least one event
when the homepage contains Tixr event URLs and TixrClient resolves them.

This catches silent empty-result regressions where URL extraction succeeds
but downstream event fetching returns nothing.
"""

import importlib.util
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.scrapers.implementations.venues.laugh_boston.scraper import LaughBostonScraper
from laughtrack.scrapers.implementations.venues.laugh_boston.page_data import LaughBostonPageData


GROUP_URL = "https://laughboston.com"
EVENT_URL = "https://www.tixr.com/groups/laughboston/events/comedy-night-12345"


def _club() -> Club:
    return Club(
        id=999,
        name="Laugh Boston",
        address="425 Summer St",
        website="https://laughboston.com",
        scraping_url=GROUP_URL,
        popularity=0,
        zip_code="02210",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _tixr_event() -> TixrEvent:
    show = Show(
        name="Comedy Night at Laugh Boston",
        club_id=999,
        date=datetime(2026, 4, 4, 19, 0, tzinfo=timezone.utc),
        show_page_url=EVENT_URL,
        lineup=[],
        tickets=[Ticket(price=30.0, purchase_url=EVENT_URL, sold_out=False, type="General Admission")],
        supplied_tags=["event"],
        description=None,
        timezone="America/New_York",
        room="",
    )
    return TixrEvent.from_tixr_show(show=show, source_url=EVENT_URL, event_id="12345")


def _homepage_html() -> str:
    """Minimal Laugh Boston homepage HTML containing one Tixr event link."""
    return f"""<html><body>
<a href="{EVENT_URL}">Comedy Night - April 4</a>
</body></html>"""


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """
    get_data() returns LaughBostonPageData with at least one TixrEvent
    when the homepage HTML contains event URLs and TixrClient resolves them.
    """
    scraper = LaughBostonScraper(_club())

    monkeypatch.setattr(
        scraper,
        "fetch_html",
        AsyncMock(return_value=_homepage_html()),
    )
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(return_value=_tixr_event()),
    )

    result = await scraper.get_data(GROUP_URL)

    assert isinstance(result, LaughBostonPageData), (
        "get_data() did not return LaughBostonPageData — check scraper pipeline"
    )
    assert result.get_event_count() > 0, (
        "get_data() returned 0 events from valid homepage HTML — "
        "check extract_tixr_urls() or batch_scraper processing"
    )
    assert result.tixr_urls == [EVENT_URL]


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_html(monkeypatch):
    """get_data() returns None when the homepage fetch fails (returns None)."""
    scraper = LaughBostonScraper(_club())

    monkeypatch.setattr(
        scraper,
        "fetch_html",
        AsyncMock(return_value=None),
    )

    result = await scraper.get_data(GROUP_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_event_urls(monkeypatch):
    """get_data() returns None when the homepage contains no Tixr event URLs."""
    scraper = LaughBostonScraper(_club())

    monkeypatch.setattr(
        scraper,
        "fetch_html",
        AsyncMock(return_value="<html><body>No events here</body></html>"),
    )

    result = await scraper.get_data(GROUP_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_all_events_fail(monkeypatch):
    """get_data() returns None when all TixrClient calls return None."""
    scraper = LaughBostonScraper(_club())

    monkeypatch.setattr(
        scraper,
        "fetch_html",
        AsyncMock(return_value=_homepage_html()),
    )
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(return_value=None),
    )

    result = await scraper.get_data(GROUP_URL)
    assert result is None


def test_can_transform_accepts_tixr_event():
    """
    Transformation pipeline accepts TixrEvent — catches type-mismatch regressions
    where the transformer's can_transform() silently rejects all events.
    """
    scraper = LaughBostonScraper(_club())
    event = _tixr_event()
    page_data = LaughBostonPageData(event_list=[event], tixr_urls=[EVENT_URL])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert shows is not None and len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 shows for a valid TixrEvent — "
        "check LaughBostonEventTransformer.can_transform()"
    )
