from __future__ import annotations

from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.next_stop_comedy.extractor import (
    extract_event_urls,
    extract_json_ld_events,
)
from laughtrack.scrapers.implementations.next_stop_comedy.scraper import (
    NextStopComedyScraper,
)


_EVENT_HTML = """
<html><body>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "ComedyEvent",
  "name": "Trillium - Canton",
  "description": "Next Stop Comedy brings the best comedians.",
  "url": "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09",
  "startDate": "2026-07-09T19:00:00-04:00",
  "location": {
    "@type": "Place",
    "name": "Trillium - Canton",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "100 Royall Street, Canton, MA 02021",
      "addressLocality": "Canton",
      "addressRegion": "MA",
      "postalCode": "02021",
      "addressCountry": "US"
    }
  },
  "performer": [
    {"@type": "Person", "name": "Zach Valencia"},
    {"@type": "Person", "name": "Dan Boulger"}
  ],
  "offers": {
    "@type": "AggregateOffer",
    "lowPrice": 27,
    "priceCurrency": "USD",
    "url": "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09",
    "availability": "https://schema.org/InStock"
  }
}
</script>
</body></html>
"""


@pytest.fixture
def promoter_proxy() -> Club:
    club = Club(
        id=Club.SYNTHETIC_PROXY_PLACEHOLDER_ID,
        name="Next Stop Comedy",
        address="",
        website="https://www.nextstopcomedy.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=False,
        is_synthetic=True,
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        platform="custom",
        scraper_key="next_stop_comedy",
        source_url="https://www.nextstopcomedy.com/events",
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _venue_club(venue: dict) -> Club:
    return Club(
        id=4242,
        name=venue["name"],
        address=venue.get("address", ""),
        website="",
        popularity=0,
        zip_code=venue.get("zip_code", ""),
        phone_number="",
        visible=True,
        timezone=venue.get("timezone") or "America/New_York",
    )


def test_extract_event_urls_from_initial_html_and_api_payload():
    html = """
    <a href="/events/trillium-canton-2026-07-09">Show</a>
    <a href="https://www.nextstopcomedy.com/events/lake-norman-brewery-2026-07-09">Show</a>
    <a href="/classes/not-a-show">Class</a>
    """
    api_events = [
        {"slug": "recon-brewing-butler-2026-07-16"},
        {"slug": "trillium-canton-2026-07-09"},
    ]

    urls = extract_event_urls(html, api_events)

    assert urls == [
        "https://www.nextstopcomedy.com/events/lake-norman-brewery-2026-07-09",
        "https://www.nextstopcomedy.com/events/recon-brewing-butler-2026-07-16",
        "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09",
    ]


def test_extract_json_ld_event_to_show_with_lineup_and_ticket():
    events = extract_json_ld_events(_EVENT_HTML)

    assert len(events) == 1
    event = events[0]
    assert event.title == "Trillium - Canton"
    assert event.venue_name == "Trillium - Canton"
    assert event.venue_address == "100 Royall Street, Canton, MA 02021"
    assert event.venue_zip == "02021"

    show = event.to_show(_venue_club(event.venue_payload()))

    assert show.club_id == 4242
    assert show.show_page_url == "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09"
    assert [comedian.name for comedian in show.lineup] == ["Zach Valencia", "Dan Boulger"]
    assert show.tickets[0].price == 27
    assert show.tickets[0].purchase_url == show.show_page_url


@pytest.mark.asyncio
async def test_scrape_walks_load_more_and_routes_to_discovered_venues(monkeypatch, promoter_proxy):
    scraper = NextStopComedyScraper(promoter_proxy)
    fetched = []

    async def fake_fetch(url):
        fetched.append(url)
        if url == "https://www.nextstopcomedy.com/events":
            return '<a href="/events/trillium-canton-2026-07-09">Show</a>'
        if url == "https://www.nextstopcomedy.com/events/trillium-canton-2026-07-09":
            return _EVENT_HTML
        raise AssertionError(f"unexpected fetch {url}")

    async def fake_fetch_json(url):
        if url.endswith("offset=48"):
            return {
                "events": [{"slug": "trillium-canton-2026-07-09"}],
                "hasMore": False,
                "nextOffset": 72,
            }
        raise AssertionError(f"unexpected json fetch {url}")

    monkeypatch.setattr(scraper, "_fetch_page", fake_fetch)
    monkeypatch.setattr(scraper, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper._club_handler, "upsert_discovered_venue", _venue_club)

    shows = await scraper.scrape_async()

    assert len(shows) == 1
    assert shows[0].club_id == 4242
    assert [comedian.name for comedian in shows[0].lineup] == ["Zach Valencia", "Dan Boulger"]
    assert "https://www.nextstopcomedy.com/events" in fetched
