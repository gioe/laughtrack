from __future__ import annotations

import json

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
    assert event.venue_address == "100 Royall Street, Canton, MA 02021, US"
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


@pytest.mark.parametrize(
    "address,expected",
    [
        (
            {
                "streetAddress": "100 Royall Street",
                "addressLocality": "Canton",
                "addressRegion": "MA",
                "postalCode": "02021",
                "addressCountry": "US",
            },
            "100 Royall Street, Canton, MA 02021, US",
        ),
        (
            {
                "streetAddress": "100 Royall Street, Canton, MA 02021",
                "addressLocality": "Canton",
                "addressRegion": "MA",
                "postalCode": "02021",
                "addressCountry": {"@type": "Country", "name": "US"},
            },
            "100 Royall Street, Canton, MA 02021, US",
        ),
        (
            {
                "streetAddress": "100 Royall Street, Canton, MA 02021, US",
                "addressLocality": "Canton",
                "addressRegion": "MA",
                "postalCode": "02021",
                "addressCountry": "US",
            },
            "100 Royall Street, Canton, MA 02021, US",
        ),
        (
            {
                "streetAddress": "100 Royall Street, Canton",
                "addressLocality": "Canton",
                "addressRegion": "MA",
                "postalCode": "02021",
                "addressCountry": "US",
            },
            "100 Royall Street, Canton, MA 02021, US",
        ),
        (
            {
                "streetAddress": "1 Boston Road",
                "addressLocality": "Boston",
                "addressRegion": "MA",
                "addressCountry": "US",
            },
            "1 Boston Road, Boston, MA, US",
        ),
        (
            {
                "streetAddress": " 100 Royall Street ",
                "addressLocality": "",
                "addressRegion": None,
                "addressCountry": {},
            },
            "100 Royall Street",
        ),
        (
            {
                "addressLocality": "Canton",
                "addressRegion": "MA",
                "postalCode": "02021",
                "addressCountry": {"name": "US"},
            },
            "Canton, MA 02021, US",
        ),
    ],
)
def test_extract_preserves_structured_address_evidence(address, expected):
    node = json.loads(_EVENT_HTML.split('<script type="application/ld+json">')[1].split("</script>")[0])
    node["location"]["address"] = address
    html = '<script type="application/ld+json">' + json.dumps(node) + "</script>"
    event = extract_json_ld_events(html)[0]
    assert event.venue_address == expected
    assert event.venue_payload()["address"] == expected


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, "America/New_York"),
        ({"eventDate": "2026-07-09T23:00:00Z"}, "America/New_York"),
        ({"eventDate": "2026-07-10T23:00:00Z"}, None),
        ({"eventSlug": "other-event"}, None),
        ({"currentEventId": "other-id"}, None),
        ({"venueTimezone": "invalid/timezone"}, None),
        ({"eventId": None, "currentEventId": None}, None),
    ],
)
def test_timezone_uses_only_matching_main_event_props(changes, expected):
    props = {
        "eventSlug": "trillium-canton-2026-07-09",
        "eventId": "current-id",
        "currentEventId": "current-id",
        "venueTimezone": "America/New_York",
        "nearbyShows": [{"slug": "other-event", "venueTimezone": "America/Los_Angeles"}],
    }
    props.update(changes)
    flight = "1:" + json.dumps(["$", "component", None, props]) + "\n"
    html = _EVENT_HTML + "<script>self.__next_f.push(" + json.dumps([1, flight]) + ")</script>"
    event = extract_json_ld_events(html)[0]
    assert event.venue_timezone == expected
    assert event.venue_payload()["timezone"] == expected
    assert event.start_date.isoformat() == "2026-07-09T19:00:00-04:00"


def test_cancelled_page_without_main_props_does_not_use_nearby_timezone():
    flight = (
        "1:"
        + json.dumps({"nearbyShows": [{"slug": "trillium-canton-2026-07-09", "venueTimezone": "America/Los_Angeles"}]})
        + "\n"
    )
    html = _EVENT_HTML.replace(
        '"@type": "ComedyEvent",', '"@type": "ComedyEvent", "eventStatus": "https://schema.org/EventCancelled",'
    )
    html += "<script>self.__next_f.push(" + json.dumps([1, flight]) + ")</script>"
    assert extract_json_ld_events(html)[0].venue_timezone is None


@pytest.mark.parametrize(
    "zones,expected", [(["America/New_York"], "America/New_York"), (["America/New_York", "America/Los_Angeles"], None)]
)
def test_main_timezone_split_flight_chunks_and_conflicting_props(zones, expected):
    props = [
        {"eventSlug": "trillium-canton-2026-07-09", "eventId": "id", "currentEventId": "id", "venueTimezone": zone}
        for zone in zones
    ]
    flight = "1:" + json.dumps(props) + "\n"
    chunks = [flight[: len(flight) // 2], flight[len(flight) // 2 :]]
    html = _EVENT_HTML + "".join(
        "<script>self.__next_f.push(" + json.dumps([1, chunk]) + ")</script>" for chunk in chunks
    )
    assert extract_json_ld_events(html)[0].venue_timezone == expected
