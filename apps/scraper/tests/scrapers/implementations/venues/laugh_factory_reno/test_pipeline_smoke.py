"""
Smoke tests for the Laugh Factory Reno scraper pipeline.

Verifies that get_data() returns LaughFactoryRenoPageData with at least one event
when the CMS page contains valid `.show-sec.jokes` HTML.

This catches silent empty-result regressions where HTML fetch succeeds but the
extractor fails to parse any events.
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.tixologi import TixologiEvent
from laughtrack.scrapers.implementations.venues.laugh_factory_reno.scraper import LaughFactoryRenoScraper
from laughtrack.scrapers.implementations.venues.laugh_factory_reno.data import LaughFactoryRenoPageData
from laughtrack.scrapers.implementations.venues.laugh_factory_reno.extractor import LaughFactoryRenoEventExtractor


SCRAPING_URL = "https://www.laughfactory.com/reno"

TICKET_URL = "https://www.laughfactory.club/checkout/show/abc-123-uuid"


def _club() -> Club:
    return Club(
        id=210,
        name="Laugh Factory Reno",
        address="407 N Virginia St",
        website="https://www.laughfactory.com/reno",
        scraping_url=SCRAPING_URL,
        popularity=0,
        zip_code="89501",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _show_html(date: str = "Wed\xa0Apr 10", time: str = "7:00 PM") -> str:
    """Minimal HTML containing one `.show-sec.jokes` div."""
    return f"""<html><body>
<div class="clubs-list-section">
  <div class="show-sec jokes">
    <div class="shedule">
      <span class="date">{date}</span>
      <span class="timing">{time}</span>
      <div class="tickets">
        <a href="{TICKET_URL}" class="readmore-btn ticket-toggle-btn">Buy Tickets</a>
      </div>
    </div>
    <div class="show-content">
      <div class="show-top-content-sec">
        <h4>Comedy Night</h4>
        <div class="show-thumbnails-sec">
          <figure><figcaption>Jane Doe</figcaption></figure>
        </div>
      </div>
    </div>
  </div>
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Extractor unit tests
# ---------------------------------------------------------------------------


def test_extractor_parses_single_show():
    """extract_shows() returns one TixologiEvent from valid HTML."""
    events = LaughFactoryRenoEventExtractor.extract_shows(
        _show_html(), club_id=210, timezone="America/Los_Angeles"
    )
    assert len(events) == 1
    event = events[0]
    assert event.title == "Comedy Night"
    assert event.date_str == "Apr 10"
    assert event.time_str == "7:00 PM"
    assert event.ticket_url == TICKET_URL
    assert event.punchup_id == "abc-123-uuid"
    assert "Jane Doe" in event.comedians


def test_extractor_returns_empty_for_no_shows():
    """extract_shows() returns [] when no `.show-sec.jokes` divs are found."""
    events = LaughFactoryRenoEventExtractor.extract_shows(
        "<html><body>No shows here</body></html>",
        club_id=210,
        timezone="America/Los_Angeles",
    )
    assert events == []


# ---------------------------------------------------------------------------
# Scraper smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """
    get_data() returns LaughFactoryRenoPageData with at least one TixologiEvent
    when the CMS page HTML contains valid `.show-sec.jokes` divs.
    """
    scraper = LaughFactoryRenoScraper(_club())

    monkeypatch.setattr(
        scraper.tixologi_client,
        "fetch_shows_page",
        AsyncMock(return_value=_show_html()),
    )

    result = await scraper.get_data(SCRAPING_URL)

    assert isinstance(result, LaughFactoryRenoPageData), (
        "get_data() did not return LaughFactoryRenoPageData — check scraper pipeline"
    )
    assert result.get_event_count() > 0, (
        "get_data() returned 0 events from valid HTML — "
        "check LaughFactoryRenoEventExtractor.extract_shows()"
    )


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_html(monkeypatch):
    """get_data() returns None when the CMS page fetch fails."""
    scraper = LaughFactoryRenoScraper(_club())

    monkeypatch.setattr(
        scraper.tixologi_client,
        "fetch_shows_page",
        AsyncMock(return_value=None),
    )

    result = await scraper.get_data(SCRAPING_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_shows(monkeypatch):
    """get_data() returns None when the CMS page contains no show divs."""
    scraper = LaughFactoryRenoScraper(_club())

    monkeypatch.setattr(
        scraper.tixologi_client,
        "fetch_shows_page",
        AsyncMock(return_value="<html><body>No events</body></html>"),
    )

    result = await scraper.get_data(SCRAPING_URL)
    assert result is None


def test_can_transform_accepts_tixologi_event():
    """
    Transformation pipeline accepts TixologiEvent — catches type-mismatch regressions
    where the transformer's can_transform() silently rejects all events.
    """
    club = _club()
    scraper = LaughFactoryRenoScraper(club)
    event = TixologiEvent(
        club_id=club.id,
        title="Comedy Night",
        date_str="Apr 10",
        time_str="7:00 PM",
        ticket_url=TICKET_URL,
        timezone="America/Los_Angeles",
        comedians=["Jane Doe"],
        punchup_id="abc-123-uuid",
    )
    page_data = LaughFactoryRenoPageData(event_list=[event])

    shows = scraper.transformation_pipeline.transform(page_data)

    assert shows is not None and len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 shows for a valid TixologiEvent — "
        "check LaughFactoryRenoEventTransformer.can_transform()"
    )
