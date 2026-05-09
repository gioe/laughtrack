"""
Tests that legacy Tixr-only venue wrappers (St. Marks, Improv Asylum) have
been absorbed into the shared Tixr scrapers.

The legacy ``StMarksScraper`` and ``ImprovAsylumScraper`` classes have been
removed; their venue rows now route through the generic ``TixrPublicCardScraper``
and ``TixrScraper`` respectively. These tests pin both halves of that
behavior:

* St. Marks resolves through the generic public-card path and never fetches
  Tixr detail pages (those are DataDome-blocked in automation).
* Improv Asylum resolves through the generic Tixr scraper and still falls
  back to the Pixl Calendar API when the Tixr group page returns no event
  URLs.
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.tixr.data import TixrPageData
from laughtrack.scrapers.implementations.api.tixr.scraper import (
    TixrPublicCardScraper,
    TixrScraper,
)


ST_MARKS_CALENDAR_URL = "https://www.stmarkscomedyclub.com/calendar"
ST_MARKS_TIXR_URL = "https://www.tixr.com/groups/stmarks/events/comedy-night-12345"

IMPROV_ASYLUM_TIXR_URL = "https://www.tixr.com/groups/improvasylum"
IMPROV_ASYLUM_PIXL_API_URL = "https://calendar.improvasylum.com/api/events/improv-asylum"


def _st_marks_club() -> Club:
    club = Club(
        id=16,
        name="St. Marks Comedy Club",
        address="",
        website="https://www.stmarkscomedyclub.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="tixr",
        scraper_key="tixr_public_card",
        source_url=ST_MARKS_CALENDAR_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _improv_asylum_club() -> Club:
    club = Club(
        id=141,
        name="Improv Asylum",
        address="216 Hanover St",
        website="https://improvasylum.com",
        popularity=0,
        zip_code="02113",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="tixr",
        scraper_key="tixr",
        source_url=IMPROV_ASYLUM_TIXR_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _st_marks_card_html() -> str:
    """Webflow-style card from St. Marks' /calendar page with full event data."""
    return f"""<html><body>
<div class="event-item w-dyn-item" role="listitem">
  <a class="ticket-links grid w-inline-block" href="{ST_MARKS_TIXR_URL}">
    <div class="text-block-35">St. Marks Comedy Night</div>
    <div class="event-card grid">
      <div class="date-info grid">
        <div class="month grid date">Wed</div>
        <div class="month grid">Jun</div>
        <div class="month grid custom-filter">Jun</div>
        <div class="month day grid">10</div>
        <div class="month day time">7:30 pm</div>
      </div>
    </div>
  </a>
</div>
</body></html>"""


def _improv_asylum_pixl_response() -> dict:
    return {
        "events": [
            {
                "id": "d3b148b6-0c3c-4f11-86fa-ef5c6a24c800",
                "title": "Improv Asylum&#39;s Main Stage Show",
                "description": "Fast-paced improv",
                "start": "2026-05-08T23:00:00.000Z",
                "end": "2026-05-09T00:30:00.000Z",
                "price": 30,
                "venue": "Improv Asylum",
                "ticketUrl": (
                    "https://www.tixr.com/groups/improvasylum/events/"
                    "improv-asylum-s-main-stage-show-169028"
                ),
                "status": "available",
                "timezone": "America/New_York",
                "sales": [
                    {
                        "id": 1852654,
                        "name": "General Admission",
                        "currentPrice": 33.54,
                        "state": "OPEN",
                    },
                    {
                        "id": 1852658,
                        "name": "Premium",
                        "currentPrice": 37.18,
                        "state": "OPEN",
                    },
                ],
            }
        ]
    }


# ---------------------------------------------------------------------------
# Criterion 6733 — St. Marks resolves through the generic Tixr scraper path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_st_marks_uses_generic_tixr_path(monkeypatch):
    """The legacy ``st_marks`` wrapper key is unregistered, and St. Marks'
    Webflow calendar page is parsed by the shared ``TixrPublicCardScraper``
    without any fetch against Tixr-hosted event detail pages.
    """
    resolver = ScraperResolver()
    assert resolver.get("st_marks") is None, (
        "Legacy 'st_marks' scraper key is still registered — venue wrapper "
        "should be removed in favor of the generic Tixr scrapers"
    )
    assert resolver.get("tixr_public_card") is TixrPublicCardScraper

    scraper = TixrPublicCardScraper(_st_marks_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _st_marks_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(side_effect=AssertionError("Tixr detail pages should not be fetched")),
    )

    result = await scraper.get_data(ST_MARKS_CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 1
    event = result.event_list[0]
    assert event.title == "St. Marks Comedy Night"
    assert event.source_url == ST_MARKS_TIXR_URL
    assert event.show.show_page_url == ST_MARKS_TIXR_URL
    assert event.show.tickets[0].purchase_url == ST_MARKS_TIXR_URL
    assert event.show.date.hour == 19
    assert event.show.date.minute == 30
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


# ---------------------------------------------------------------------------
# Criterion 6734 — Improv Asylum generic Tixr path preserves the Pixl fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_improv_asylum_generic_path_preserves_pixl_fallback(monkeypatch):
    """The legacy ``improv_asylum`` wrapper key is unregistered, and the
    generic ``TixrScraper`` still falls back to ``calendar.improvasylum.com``
    when the Tixr group page returns no extractable event URLs (the
    DataDome-blocked path).
    """
    resolver = ScraperResolver()
    assert resolver.get("improv_asylum") is None, (
        "Legacy 'improv_asylum' scraper key is still registered — venue "
        "wrapper should be removed in favor of the generic Tixr scraper"
    )
    assert resolver.get("tixr") is TixrScraper

    scraper = TixrScraper(_improv_asylum_club())

    async def fake_fetch_calendar_html(url):
        return "<html><title>tixr.com</title><body>DataDome challenge</body></html>"

    pixl_url_seen: list[str] = []

    async def fake_fetch_json(url, **kwargs):
        pixl_url_seen.append(url)
        return _improv_asylum_pixl_response()

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)
    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock()

    result = await scraper.get_data(IMPROV_ASYLUM_TIXR_URL)

    assert pixl_url_seen == [IMPROV_ASYLUM_PIXL_API_URL]
    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    event = result.event_list[0]
    assert event.title == "Improv Asylum's Main Stage Show"
    assert event.event_id == "169028"
    assert event.show.date.isoformat() == "2026-05-08T19:00:00-04:00"
    assert event.show.show_page_url == (
        "https://www.tixr.com/groups/improvasylum/events/"
        "improv-asylum-s-main-stage-show-169028"
    )
    assert [ticket.type for ticket in event.show.tickets] == [
        "General Admission",
        "Premium",
    ]
    assert [ticket.price for ticket in event.show.tickets] == [33.54, 37.18]
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()
