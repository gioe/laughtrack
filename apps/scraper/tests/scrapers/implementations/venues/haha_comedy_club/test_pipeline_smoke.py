"""
Smoke tests for the HAHA Comedy Club scraper pipeline.

Verifies that get_data() returns TixrPageData with events when the calendar
page HTML contains JSON-LD Event blocks with accompanying time elements, and
returns None on empty/malformed input.

The scraper parses event data directly from the venue calendar HTML without
fetching individual Tixr event pages.
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.api.tixr.page_data import TixrPageData
from laughtrack.scrapers.implementations.venues.haha_comedy_club.scraper import HahaComedyClubScraper

CALENDAR_URL = "https://www.hahacomedyclub.com/calendar"

# Minimal Webflow calendar HTML block containing one JSON-LD Event + time element.
_ONE_EVENT_HTML = """
<div class="event-item w-dyn-item">
  <div class="schema w-embed w-script">
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Event",
      "name": "Comedy Night",
      "startDate": "Apr 01, 2026",
      "endDate": "Apr 01, 2026",
      "performer": {"@type": "Person", "name": "Test Comedian"},
      "offers": {
        "@type": "Offer",
        "name": "General Admission",
        "price": "20",
        "priceCurrency": "USD",
        "url": "https://tixr.com/e/12345",
        "availability": "https://schema.org/InStock"
      }
    }
    </script>
  </div>
  <a href="https://tixr.com/e/12345" class="ticket-links grid w-inline-block">
    <div class="event-card grid">
      <div class="date-info grid">
        <div class="month day time">8:00 pm</div>
      </div>
    </div>
  </a>
</div>
"""


def _club() -> Club:
    return Club(
        id=163,
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


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """
    get_data() returns TixrPageData with at least one TixrEvent when the
    calendar page HTML contains a valid JSON-LD Event block with a time element.
    """
    scraper = HahaComedyClubScraper(_club())

    monkeypatch.setattr(
        scraper,
        "fetch_html",
        AsyncMock(return_value=_ONE_EVENT_HTML),
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData), (
        "get_data() did not return TixrPageData — check scraper pipeline"
    )
    assert result.get_event_count() > 0, (
        "get_data() returned 0 events from valid calendar HTML — "
        "check _parse_events_from_html()"
    )
    event = result.event_list[0]
    assert event.title == "Comedy Night"
    assert event.show.date.hour == 20  # 8:00 pm Los Angeles
    assert event.event_id == "12345"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_fetch_returns_none(monkeypatch):
    """get_data() returns None when fetch_html returns None."""
    scraper = HahaComedyClubScraper(_club())

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=None))

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_html_has_no_events(monkeypatch):
    """get_data() returns None when the calendar HTML contains no JSON-LD Event blocks."""
    scraper = HahaComedyClubScraper(_club())

    monkeypatch.setattr(
        scraper,
        "fetch_html",
        AsyncMock(return_value="<html><body>No events</body></html>"),
    )

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_skips_malformed_jsonld_without_crashing(monkeypatch):
    """get_data() skips malformed JSON-LD blocks and returns None if nothing parses."""
    scraper = HahaComedyClubScraper(_club())

    bad_html = """
    <div class="event-item w-dyn-item">
      <script type="application/ld+json">{ this is not valid json }</script>
    </div>
    """
    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=bad_html))

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None


def test_parse_date_with_time():
    """_parse_date() correctly combines a JSON-LD date and an HTML time string."""
    dt = HahaComedyClubScraper._parse_date("Apr 01, 2026", "8:00 pm")
    assert dt is not None
    assert dt.hour == 20
    assert dt.minute == 0


def test_parse_date_without_time_defaults_to_midnight():
    """_parse_date() returns midnight when no time string is provided."""
    dt = HahaComedyClubScraper._parse_date("Apr 01, 2026", None)
    assert dt is not None
    assert dt.hour == 0
    assert dt.minute == 0


def test_parse_date_returns_none_for_unparseable_date():
    """_parse_date() returns None for an unrecognized date format."""
    dt = HahaComedyClubScraper._parse_date("not a date", "8:00 pm")
    assert dt is None
