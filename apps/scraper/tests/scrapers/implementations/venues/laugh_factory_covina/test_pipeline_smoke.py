"""
Smoke tests for Laugh Factory Covina using TixrScraper.

Laugh Factory Covina was migrated from a venue-specific laugh_factory_covina
scraper to the generic tixr scraper. These tests verify the generic pipeline
works correctly with Covina's Tixr group page URL.
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


def _club() -> Club:
    _c = Club(id=200, name='Laugh Factory Covina', address='104 N Citrus Ave', website='https://www.laughfactory.com/covina', popularity=0, zip_code='91723', phone_number='', visible=True, timezone='America/Los_Angeles')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='tixr', scraper_key='tixr', source_url=GROUP_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _tixr_event() -> TixrEvent:
    show = Show(
        name="Comedy Night at Laugh Factory Covina",
        club_id=200,
        date=datetime(2026, 4, 10, 19, 30, tzinfo=timezone.utc),
        show_page_url=EVENT_URL,
        lineup=[],
        tickets=[Ticket(price=20.0, purchase_url=EVENT_URL, sold_out=False, type="General Admission")],
        supplied_tags=["event"],
        description=None,
        timezone="America/Los_Angeles",
        room="",
    )
    return TixrEvent.from_tixr_show(show=show, source_url=EVENT_URL, event_id="12345")


def _group_page_html() -> str:
    """Minimal Tixr group page HTML containing one event link."""
    return f"""<html><body>
<a href="{EVENT_URL}">Comedy Night - April 10</a>
</body></html>"""


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """
    get_data() returns TixrPageData with at least one TixrEvent
    when the group page HTML contains event URLs and TixrClient resolves them.
    """
    scraper = TixrScraper(_club())

    # Mock _fetch_tixr_page (not fetch_html) because tixr.com URLs use the
    # DataDome-safe Tixr client path in TixrScraper.get_data()
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

    assert isinstance(result, TixrPageData), (
        "get_data() did not return TixrPageData — check scraper pipeline"
    )
    assert result.get_event_count() > 0, (
        "get_data() returned 0 events from valid group page HTML — "
        "check TixrExtractor.extract_tixr_urls() or batch_scraper processing"
    )


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_event_urls(monkeypatch):
    """get_data() returns None when the group page contains no Tixr event URLs."""
    scraper = TixrScraper(_club())

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
    scraper = TixrScraper(_club())

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


@pytest.mark.asyncio
async def test_get_data_filters_by_org_jsonld_when_present(monkeypatch):
    """
    get_data() uses TixrExtractor.extract_org_jsonld_event_urls() when an
    Organization JSON-LD block is present — only events in the block are
    processed; double-dash (client-side) URLs not in the block are skipped.
    """
    scraper = TixrScraper(_club())
    dropped_url = "https://www.tixr.com/groups/laughfactorycovina/events/other--99999"

    html_with_jsonld = f"""<html><head>
<script type="application/ld+json">
{{
  "@type": "Organization",
  "events": [{{"url": "{EVENT_URL}"}}]
}}
</script>
</head><body>
<a href="{EVENT_URL}">Comedy Night</a>
<a href="{dropped_url}">Dropped Show</a>
</body></html>"""

    monkeypatch.setattr(
        scraper.tixr_client,
        "_fetch_tixr_page",
        AsyncMock(return_value=html_with_jsonld),
    )
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(return_value=_tixr_event()),
    )

    result = await scraper.get_data(GROUP_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    scraper.tixr_client.get_event_detail_from_url.assert_called_once_with(EVENT_URL)


@pytest.mark.asyncio
async def test_get_data_filters_by_event_id_when_url_forms_differ(monkeypatch):
    """
    get_data() matches JSON-LD URLs against HTML URLs by numeric event ID, not
    by string equality.
    """
    scraper = TixrScraper(_club())

    long_url_in_html = "https://www.tixr.com/groups/laughfactorycovina/events/comedy-night-12345"
    short_url_in_jsonld = "https://www.tixr.com/e/12345"
    dropped_url = "https://www.tixr.com/groups/laughfactorycovina/events/other--99999"

    html_with_jsonld = f"""<html><head>
<script type="application/ld+json">
{{
  "@type": "Organization",
  "events": [{{"url": "{short_url_in_jsonld}"}}]
}}
</script>
</head><body>
<a href="{long_url_in_html}">Comedy Night</a>
<a href="{dropped_url}">Dropped Show</a>
</body></html>"""

    monkeypatch.setattr(
        scraper.tixr_client,
        "_fetch_tixr_page",
        AsyncMock(return_value=html_with_jsonld),
    )
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(return_value=_tixr_event()),
    )

    result = await scraper.get_data(GROUP_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    # The generic TixrExtractor deduplicates by event ID and prefers
    # short-form URLs — so when the JSON-LD contains a short-form URL
    # and the HTML has a long-form URL for the same event, the short-form
    # URL is used for the batch fetch (both resolve to the same event).
    scraper.tixr_client.get_event_detail_from_url.assert_called_once_with(
        "https://tixr.com/e/12345"
    )


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
