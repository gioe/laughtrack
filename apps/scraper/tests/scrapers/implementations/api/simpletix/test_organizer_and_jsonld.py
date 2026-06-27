"""Tests for SimpleTix organizer-page enumeration + JSON-LD event fallback (TASK-3345).

Commonwealth Comedy Club (Dayton, KY) uses SimpleTix with a full rotating
calendar: an organizer page (`{org}.simpletix.com/`) listing dozens of one-off
comedian bookings, each on its own `/e/...` event page. Those single-date pages
render no `var timeArray` — only JSON-LD `Event` data. These tests cover the two
enhancements that onboard such a venue:

1. `collect_scraping_targets` enumerates the organizer page's `/e/...` links.
2. `get_data` falls back to JSON-LD events (UTC -> venue-local wall-clock) when
   the page has no timeArray.
"""

import pytest
from datetime import datetime
from unittest.mock import patch

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.simpletix.scraper import SimpleTixScraper
from laughtrack.scrapers.implementations.api.simpletix.data import SimpleTixPageData
from laughtrack.scrapers.implementations.api.simpletix.extractor import SimpleTixExtractor


ORGANIZER_URL = "https://commonwealthcomedyclub.simpletix.com/"
SINGLE_EVENT_URL = "https://www.simpletix.com/e/improvcity-show-tickets-249393"


def _club() -> Club:
    _c = Club(
        id=99001, name='Commonwealth Comedy Club', address='522 5th Ave, Dayton, KY 41074',
        website='https://commonwealthcomedyclub.com', popularity=0, zip_code='41074',
        phone_number='', visible=True, timezone='America/New_York',
    )
    _c.active_scraping_source = ScrapingSource(
        id=1, club_id=_c.id, platform='simpletix', scraper_key='simpletix',
        source_url=ORGANIZER_URL, external_id=None,
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


# Organizer listing: two distinct events, plus a third link that is the SAME
# event id (273173) under a differently-truncated slug — must dedupe to 2.
LISTING_HTML = """
<html><body>
<a href="/e/alex-kumin-presented-by-commonwealth-comed-tickets-273173">Alex Kumin</a>
<a href="/e/ariel-elias-presented-by-commonwealth-come-tickets-260223">Ariel Elias</a>
<a href="/e/alex-kumin-presented-by-commonwealth-c-tickets-273173">Alex Kumin (dupe)</a>
</body></html>
"""

# Single-date event page: NO timeArray, JSON-LD array with one future and one
# past Event. startDate is a UTC instant (the live SimpleTix shape).
JSONLD_EVENT_HTML = """
<html><head>
<script type="application/ld+json">
[
  {
    "@type": "Event",
    "name": "ALEX KUMIN presented by Commonwealth Comedy Club",
    "startDate": "2099-11-08T00:30:00+00:00",
    "endDate": "2099-11-08T02:00:00+00:00",
    "url": "https://www.simpletix.com/e/alex-kumin-presented-by-commonwealth-comed-tickets-273173",
    "location": {"@type": "Place", "name": "Commonwealth Comedy Club",
      "address": {"@type": "PostalAddress", "streetAddress": "522 5th Avenue",
        "addressLocality": "Dayton", "postalCode": "41074",
        "addressRegion": "Kentucky", "addressCountry": "US"}},
    "offers": [
      {"@type": "AggregateOffer", "priceCurrency": "USD", "lowPrice": 22.17, "highPrice": 22.17}
    ]
  },
  {
    "@type": "Event",
    "name": "PAST SHOW presented by Commonwealth Comedy Club",
    "startDate": "2000-01-02T00:30:00+00:00",
    "endDate": "2000-01-02T02:00:00+00:00",
    "url": "https://www.simpletix.com/e/alex-kumin-presented-by-commonwealth-comed-tickets-273173",
    "location": {"@type": "Place", "name": "Commonwealth Comedy Club",
      "address": {"@type": "PostalAddress", "streetAddress": "522 5th Avenue",
        "addressLocality": "Dayton", "postalCode": "41074",
        "addressRegion": "Kentucky", "addressCountry": "US"}},
    "offers": [
      {"@type": "AggregateOffer", "priceCurrency": "USD", "lowPrice": 22.17, "highPrice": 22.17}
    ]
  }
]
</script>
</head><body><h1>ALEX KUMIN presented by Commonwealth Comedy Club</h1></body></html>
"""


def test_is_listing_url():
    assert SimpleTixScraper._is_listing_url(ORGANIZER_URL) is True
    # Single-event www URLs are not listings (preserves original behaviour).
    assert SimpleTixScraper._is_listing_url(SINGLE_EVENT_URL) is False
    # Subdomain event permalink is not a listing either.
    assert SimpleTixScraper._is_listing_url(
        "https://commonwealthcomedyclub.simpletix.com/e/x-tickets-1"
    ) is False


def test_extract_listing_event_urls_dedupes_by_id():
    urls = SimpleTixExtractor.extract_listing_event_urls(LISTING_HTML)
    assert urls == [
        "https://www.simpletix.com/e/alex-kumin-presented-by-commonwealth-comed-tickets-273173",
        "https://www.simpletix.com/e/ariel-elias-presented-by-commonwealth-come-tickets-260223",
    ]


@pytest.mark.asyncio
async def test_collect_scraping_targets_enumerates_listing(monkeypatch):
    scraper = SimpleTixScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return LISTING_HTML

    monkeypatch.setattr(SimpleTixScraper, "fetch_html", fake_fetch_html)
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 2
    assert all(t.startswith("https://www.simpletix.com/e/") for t in targets)


@pytest.mark.asyncio
async def test_collect_scraping_targets_single_event_passthrough(monkeypatch):
    """A www single-event URL returns itself without fetching a listing."""
    club = _club()
    club.active_scraping_source = ScrapingSource(
        id=2, club_id=club.id, platform='simpletix', scraper_key='simpletix',
        source_url=SINGLE_EVENT_URL, external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    scraper = SimpleTixScraper(club)

    async def fail_fetch(self, url: str, **kwargs) -> str:  # pragma: no cover
        raise AssertionError("should not fetch a listing for a single-event URL")

    monkeypatch.setattr(SimpleTixScraper, "fetch_html", fail_fetch)
    assert await scraper.collect_scraping_targets() == [SINGLE_EVENT_URL]


@pytest.mark.asyncio
async def test_get_data_jsonld_fallback(monkeypatch):
    """get_data falls back to JSON-LD when no timeArray, converting UTC -> ET."""
    scraper = SimpleTixScraper(_club())
    event_url = "https://www.simpletix.com/e/alex-kumin-presented-by-commonwealth-comed-tickets-273173"

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return JSONLD_EVENT_HTML

    monkeypatch.setattr(SimpleTixScraper, "fetch_html", fake_fetch_html)

    with patch("laughtrack.scrapers.implementations.api.simpletix.scraper.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 1, 1)
        result = await scraper.get_data(event_url)

    assert isinstance(result, SimpleTixPageData)
    # Only the future event survives the past-event filter.
    assert len(result.event_list) == 1
    ev = result.event_list[0]
    assert ev.name == "ALEX KUMIN presented by Commonwealth Comedy Club"
    assert ev.price == 22.17
    assert ev.show_page_url == event_url
    # 2099-11-08T00:30 UTC -> America/New_York (EST, -5) -> 2099-11-07 19:30, naive.
    assert ev.start_date == datetime(2099, 11, 7, 19, 30)
    assert ev.start_date.tzinfo is None
