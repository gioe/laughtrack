"""
Smoke tests for House of Comedy Bloomington scraper pipeline.

House of Comedy Bloomington (moa.houseofcomedy.net) lists shows on its own
homepage with long-form Tixr links (tixr.com/groups/houseofcomedymn/events/*).
Uses the generic TixrScraper (scraper='tixr') — no custom scraper code needed.

Verifies that get_data() returns TixrPageData with at least one event when
the venue homepage contains Tixr event URLs and TixrClient resolves them.
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
from laughtrack.scrapers.implementations.api.tixr.scraper import TixrScraper
from laughtrack.scrapers.implementations.api.tixr.page_data import TixrPageData


VENUE_URL = "https://moa.houseofcomedy.net/"
EVENT_URL = "https://www.tixr.com/groups/houseofcomedymn/events/comedy-night-178358"


def _club() -> Club:
    return Club(
        id=300,
        name="House of Comedy Bloomington",
        address="60 E Broadway Ave",
        website="https://moa.houseofcomedy.net",
        scraping_url=VENUE_URL,
        popularity=0,
        zip_code="55425",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _tixr_event() -> TixrEvent:
    show = Show(
        name="Comedy Night",
        club_id=300,
        date=datetime(2026, 4, 10, 19, 30, tzinfo=timezone.utc),
        show_page_url=EVENT_URL,
        lineup=[],
        tickets=[Ticket(price=25.0, purchase_url=EVENT_URL, sold_out=False, type="General Admission")],
        supplied_tags=["event"],
        description=None,
        timezone="America/Chicago",
        room="",
    )
    return TixrEvent.from_tixr_show(show=show, source_url=EVENT_URL, event_id="178358")


def _venue_page_html() -> str:
    """Minimal venue homepage HTML containing one houseofcomedymn Tixr event link."""
    return f"""<html><body>
<a href="{EVENT_URL}">Comedy Night - April 10</a>
</body></html>"""


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """
    get_data() returns TixrPageData with at least one TixrEvent when the venue
    homepage HTML contains houseofcomedymn Tixr event URLs and TixrClient resolves them.
    """
    scraper = TixrScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _venue_page_html()

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(return_value=_tixr_event()),
    )

    result = await scraper.get_data(VENUE_URL)

    assert isinstance(result, TixrPageData), (
        "get_data() did not return TixrPageData — check scraper pipeline"
    )
    assert result.get_event_count() > 0, (
        "get_data() returned 0 events from valid venue page HTML — "
        "check extract_tixr_urls() or batch_scraper processing"
    )


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_event_urls(monkeypatch):
    """get_data() returns None when the venue page contains no Tixr event URLs."""
    scraper = TixrScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return "<html><body>No shows scheduled</body></html>"

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(VENUE_URL)
    assert result is None


def test_transformation_pipeline_produces_shows():
    """
    transformation_pipeline.transform() returns at least one Show for a valid TixrEvent.

    Catches regressions where can_transform() returns False for TixrEvent,
    causing transform() to silently return an empty list.
    """
    scraper = TixrScraper(_club())
    event = _tixr_event()
    page_data = TixrPageData(event_list=[event])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows — "
        "check can_transform() and that the transformer is registered "
        "with the correct generic type"
    )
    assert all(isinstance(s, Show) for s in shows)
