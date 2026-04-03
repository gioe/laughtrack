"""
Smoke tests for the Improv Asylum scraper pipeline.

Verifies that get_data() returns ImprovAsylumPageData with at least one event
when the Tixr group page contains event URLs and TixrClient resolves them.

This catches silent empty-result regressions (the failure mode from TASK-405/TASK-523)
where URL extraction succeeds but downstream event fetching returns nothing.
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
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.scrapers.implementations.venues.improv_asylum.scraper import ImprovAsylumScraper
from laughtrack.scrapers.implementations.venues.improv_asylum.data import ImprovAsylumPageData


GROUP_URL = "https://www.tixr.com/groups/improvasylum"
EVENT_URL = "https://www.tixr.com/groups/improvasylum/events/main-stage-12345"


def _club() -> Club:
    return Club(
        id=141,
        name="Improv Asylum",
        address="216 Hanover St",
        website="https://improvasylum.com",
        scraping_url=GROUP_URL,
        popularity=0,
        zip_code="02113",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _tixr_event() -> TixrEvent:
    show = Show(
        name="Improv Asylum Main Stage Show",
        club_id=141,
        date=datetime(2026, 4, 4, 19, 0, tzinfo=timezone.utc),
        show_page_url=EVENT_URL,
        lineup=[],
        tickets=[Ticket(price=25.0, purchase_url=EVENT_URL, sold_out=False, type="General Admission")],
        supplied_tags=["event"],
        description=None,
        timezone="America/New_York",
        room="",
    )
    return TixrEvent.from_tixr_show(show=show, source_url=EVENT_URL, event_id="12345")


def _group_page_html() -> str:
    """Minimal Tixr group page HTML containing one event link."""
    return f"""<html><body>
<a href="{EVENT_URL}">Main Stage Show - April 4</a>
</body></html>"""


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """
    get_data() returns ImprovAsylumPageData with at least one TixrEvent
    when the group page HTML contains event URLs and TixrClient resolves them.
    """
    scraper = ImprovAsylumScraper(_club())

    monkeypatch.setattr(
        scraper.tixr_client,
        "_fetch_tixr_page",
        AsyncMock(return_value=_group_page_html()),
    )
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(return_value=_tixr_event()),
    )

    result = await scraper.get_data(GROUP_URL)

    assert isinstance(result, ImprovAsylumPageData), (
        "get_data() did not return ImprovAsylumPageData — check scraper pipeline"
    )
    assert result.get_event_count() > 0, (
        "get_data() returned 0 events from valid group page HTML — "
        "check extract_tixr_urls() or batch_scraper processing"
    )
    assert result.tixr_urls == [EVENT_URL]


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_html(monkeypatch):
    """get_data() returns None when the Tixr group page fetch fails."""
    scraper = ImprovAsylumScraper(_club())

    monkeypatch.setattr(
        scraper.tixr_client,
        "_fetch_tixr_page",
        AsyncMock(return_value=None),
    )

    result = await scraper.get_data(GROUP_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_event_urls(monkeypatch):
    """get_data() returns None when the group page contains no Tixr event URLs."""
    scraper = ImprovAsylumScraper(_club())

    monkeypatch.setattr(
        scraper.tixr_client,
        "_fetch_tixr_page",
        AsyncMock(return_value="<html><body>No events here</body></html>"),
    )

    result = await scraper.get_data(GROUP_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_all_events_fail(monkeypatch):
    """get_data() returns None when all TixrClient calls return None."""
    scraper = ImprovAsylumScraper(_club())

    monkeypatch.setattr(
        scraper.tixr_client,
        "_fetch_tixr_page",
        AsyncMock(return_value=_group_page_html()),
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
    from laughtrack.scrapers.implementations.venues.improv_asylum.data import ImprovAsylumPageData

    scraper = ImprovAsylumScraper(_club())
    event = _tixr_event()
    page_data = ImprovAsylumPageData(event_list=[event], tixr_urls=[EVENT_URL])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert shows is not None and len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 shows for a valid TixrEvent — "
        "check ImprovAsylumEventTransformer.can_transform()"
    )
