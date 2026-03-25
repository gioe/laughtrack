"""
Pipeline smoke tests for HaHaComedyClubScraper.

Exercises collect_scraping_targets() and get_data() against mocked HTML and
a mocked TixrClient, verifying that Tixr short URLs are correctly extracted
and resolved to TixrEvents.
"""

import importlib.util
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.scrapers.implementations.venues.haha_comedy_club.scraper import (
    HaHaComedyClubScraper,
)
from laughtrack.scrapers.implementations.venues.haha_comedy_club.page_data import (
    HaHaComedyClubPageData,
)
from laughtrack.scrapers.implementations.venues.haha_comedy_club.extractor import (
    HaHaComedyClubExtractor,
)

CALENDAR_URL = "https://www.hahacomedyclub.com/calendar"


def _club() -> Club:
    return Club(
        id=999,
        name="HAHA Comedy Club",
        address="4712 Lankershim Blvd",
        website="https://www.hahacomedyclub.com",
        scraping_url=CALENDAR_URL,
        popularity=0,
        zip_code="91602",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _make_tixr_event(event_id: str, title: str) -> TixrEvent:
    show = Show(
        name=title,
        club_id=999,
        date=datetime(2026, 4, 1, 20, 0, tzinfo=timezone.utc),
        show_page_url=f"https://tixr.com/e/{event_id}",
        lineup=[],
        tickets=[Ticket(price=0.0, purchase_url=f"https://tixr.com/e/{event_id}", sold_out=False, type="General Admission")],
        supplied_tags=["event"],
        description=None,
        timezone=None,
        room="",
    )
    return TixrEvent.from_tixr_show(show=show, source_url=f"https://tixr.com/e/{event_id}", event_id=event_id)


def _calendar_html(tixr_ids: list[str]) -> str:
    """Render a minimal calendar page with Tixr short-URL ticket links."""
    links = "".join(
        f'<a href="https://tixr.com/e/{id}" class="buy-tickets-btn">Buy Tickets</a>'
        for id in tixr_ids
    )
    return f"<html><body><div class='calendar'>{links}</div></body></html>"


# ---------------------------------------------------------------------------
# HaHaComedyClubExtractor unit tests
# ---------------------------------------------------------------------------


def test_extractor_finds_tixr_short_urls():
    """extract_tixr_urls() picks up tixr.com/e/{id} links."""
    html = _calendar_html(["177558", "176996", "175370"])
    urls = HaHaComedyClubExtractor.extract_tixr_urls(html)
    assert urls == [
        "https://tixr.com/e/177558",
        "https://tixr.com/e/176996",
        "https://tixr.com/e/175370",
    ]


def test_extractor_deduplicates_urls():
    """extract_tixr_urls() returns each URL only once even if it appears multiple times."""
    html = (
        '<a href="https://tixr.com/e/12345">Buy</a>'
        '<a href="https://tixr.com/e/12345">Buy Again</a>'
        '<a href="https://tixr.com/e/99999">Other</a>'
    )
    urls = HaHaComedyClubExtractor.extract_tixr_urls(html)
    assert urls == ["https://tixr.com/e/12345", "https://tixr.com/e/99999"]


def test_extractor_returns_empty_for_no_tixr_urls():
    """extract_tixr_urls() returns [] when no Tixr links are present."""
    html = "<html><body><p>No shows</p></body></html>"
    urls = HaHaComedyClubExtractor.extract_tixr_urls(html)
    assert urls == []


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_returns_calendar_url():
    """collect_scraping_targets() returns only the calendar page URL."""
    scraper = HaHaComedyClubScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert targets[0].rstrip("/") == CALENDAR_URL.rstrip("/")


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() extracts Tixr URLs and resolves them to TixrEvents."""
    scraper = HaHaComedyClubScraper(_club())

    html = _calendar_html(["177558", "176996"])
    event_a = _make_tixr_event("177558", "Open Mic Night")
    event_b = _make_tixr_event("176996", "Percy Rustomji and Friends")

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return html

    monkeypatch.setattr(HaHaComedyClubScraper, "fetch_html", fake_fetch_html)

    scraper.tixr_client.get_event_detail_from_url = AsyncMock(
        side_effect=lambda url: event_a if "177558" in url else event_b
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, HaHaComedyClubPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Open Mic Night" in titles
    assert "Percy Rustomji and Friends" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_tixr_urls(monkeypatch):
    """get_data() returns None when no Tixr links are found on the page."""
    scraper = HaHaComedyClubScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body><p>No shows</p></body></html>"

    monkeypatch.setattr(HaHaComedyClubScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_tixr_client_returns_nothing(monkeypatch):
    """get_data() returns None when TixrClient returns None for all URLs."""
    scraper = HaHaComedyClubScraper(_club())

    html = _calendar_html(["177558"])

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return html

    monkeypatch.setattr(HaHaComedyClubScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(return_value=None)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None
