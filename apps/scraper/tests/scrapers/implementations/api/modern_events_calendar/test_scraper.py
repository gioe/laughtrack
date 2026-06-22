"""Tests for the generic Modern Events Calendar scraper."""

from urllib.parse import parse_qs, urlparse

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.modern_events_calendar.scraper import (
    ModernEventsCalendarScraper,
)


def _club() -> Club:
    club = Club(
        id=999,
        name="Moonlight Theatre",
        address="7 S 2nd Ave",
        website="https://moonlighttheatre.com/",
        popularity=0,
        zip_code="60174",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        city="St. Charles",
        state="IL",
    )
    source = ScrapingSource(
        id=999,
        club_id=999,
        platform="custom",
        scraper_key="modern_events_calendar",
        source_url="https://moonlighttheatre.com/wp-json/wp/v2/mec-events?mec_category=47",
        metadata={
            "per_page": 2,
            "max_pages": 2,
            "max_detail_pages": 10,
            "set_same_as_to_detail_url": True,
        },
    )
    club.active_scraping_source = source
    club.scraping_sources = [source]
    return club


def _json_ld_html(
    *,
    name: str = "Improv in the Moonlight",
    start_date: str = "2099-06-04T19:30:00-05:00",
    url: str = "https://moonlighttheatre.com/events/improv/",
) -> str:
    return f"""
    <html>
      <head>
        <script type="application/ld+json">
        {{
          "@context": "https://schema.org",
          "@type": "Event",
          "name": "{name}",
          "startDate": "{start_date}",
          "endDate": "2099-06-04T21:00:00-05:00",
          "url": "{url}",
          "location": {{
            "@type": "Place",
            "name": "Moonlight Theatre",
            "address": "7 S 2nd Ave, St. Charles, IL 60174"
          }},
          "offers": {{
            "@type": "Offer",
            "url": "{url}",
            "price": "10",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock"
          }},
          "description": "A perfect night of non-stop laughs."
        }}
        </script>
      </head>
    </html>
    """


def _mec_html_without_json_ld() -> str:
    return """
    <html>
      <head><title>Comedian Bob Marley - Rascals</title></head>
      <body>
        <h1 class="mec-single-title">Comedian Bob Marley</h1>
        <div class="mec-single-event-description">
          New England's King of Comedy returns to Worcester.
        </div>
        <div class="mec-single-event-date">
          <div class="mec-date">Date</div>
          <dl><dd>Jul 25 2099</dd></dl>
        </div>
        <div class="mec-single-event-time">
          <div class="mec-time">Time</div>
          <dl><dd>8:00 pm - 10:00 pm</dd></dl>
        </div>
        <div class="mec-event-cost">
          <div class="mec-cost">Cost</div>
          <dl><dd class="mec-events-event-cost">$39.50</dd></dl>
        </div>
        <a class="mec-booking-button" target="_blank"
           href="https://www.eventbrite.com/e/comedian-bob-marley-tickets-1983822484454">
          Buy Tickets
        </a>
      </body>
    </html>
    """


@pytest.mark.asyncio
async def test_collect_event_urls_paginates_wordpress_rest(monkeypatch):
    scraper = ModernEventsCalendarScraper(_club())
    calls = []
    pages = {
        1: [
            {"link": "https://moonlighttheatre.com/events/one/"},
            {"link": "https://moonlighttheatre.com/events/two/"},
        ],
        2: [
            {"link": "https://moonlighttheatre.com/events/two/"},
            {"link": "https://moonlighttheatre.com/events/three/"},
        ],
    }

    async def fake_fetch_json(url: str):
        calls.append(url)
        page = int(parse_qs(urlparse(url).query)["page"][0])
        return pages[page]

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)

    urls = await scraper._collect_event_urls(
        "https://moonlighttheatre.com/wp-json/wp/v2/mec-events?mec_category=47"
    )

    assert urls == [
        "https://moonlighttheatre.com/events/one/",
        "https://moonlighttheatre.com/events/two/",
        "https://moonlighttheatre.com/events/three/",
    ]
    assert len(calls) == 2
    assert "mec_category=47" in calls[0]
    assert "per_page=2" in calls[0]


@pytest.mark.asyncio
async def test_get_data_extracts_future_json_ld_and_filters_past(monkeypatch):
    scraper = ModernEventsCalendarScraper(_club())

    async def fake_collect_event_urls(source_url: str):
        return [
            "https://moonlighttheatre.com/events/future/",
            "https://moonlighttheatre.com/events/past/",
        ]

    async def fake_fetch_detail_html(url: str):
        if url.endswith("/past/"):
            return _json_ld_html(name="Past Comedy Night", start_date="2020-01-01T19:30:00-06:00", url=url)
        return _json_ld_html(name="Future Comedy Night", url=url)

    monkeypatch.setattr(scraper, "_collect_event_urls", fake_collect_event_urls)
    monkeypatch.setattr(scraper, "_fetch_detail_html", fake_fetch_detail_html)

    data = await scraper.get_data(
        "https://moonlighttheatre.com/wp-json/wp/v2/mec-events?mec_category=47"
    )

    assert data is not None
    assert len(data.event_list) == 1
    event = data.event_list[0]
    assert event.name == "Future Comedy Night"
    assert event.same_as == "https://moonlighttheatre.com/events/future/"


@pytest.mark.asyncio
async def test_get_data_uses_mec_html_fallback_when_json_ld_is_absent(monkeypatch):
    scraper = ModernEventsCalendarScraper(_club())

    async def fake_collect_event_urls(source_url: str):
        return ["https://moonlighttheatre.com/events/bob-marley/"]

    async def fake_fetch_detail_html(url: str):
        return _mec_html_without_json_ld()

    monkeypatch.setattr(scraper, "_collect_event_urls", fake_collect_event_urls)
    monkeypatch.setattr(scraper, "_fetch_detail_html", fake_fetch_detail_html)

    data = await scraper.get_data(
        "https://moonlighttheatre.com/wp-json/wp/v2/mec-events?mec_category=47"
    )

    assert data is not None
    assert len(data.event_list) == 1
    event = data.event_list[0]
    assert event.name == "Comedian Bob Marley"
    assert event.start_date.year == 2099
    assert event.start_date.hour == 20
    assert event.offers[0].price == "39.50"
    assert event.url == "https://www.eventbrite.com/e/comedian-bob-marley-tickets-1983822484454"
    assert event.same_as == "https://moonlighttheatre.com/events/bob-marley/"
    assert "King of Comedy" in event.description


@pytest.mark.asyncio
async def test_transformation_pipeline_produces_show(monkeypatch):
    scraper = ModernEventsCalendarScraper(_club())

    async def fake_collect_event_urls(source_url: str):
        return ["https://moonlighttheatre.com/events/future/"]

    async def fake_fetch_detail_html(url: str):
        return _json_ld_html(name="Improv in the Moonlight", url=url)

    monkeypatch.setattr(scraper, "_collect_event_urls", fake_collect_event_urls)
    monkeypatch.setattr(scraper, "_fetch_detail_html", fake_fetch_detail_html)

    data = await scraper.get_data(
        "https://moonlighttheatre.com/wp-json/wp/v2/mec-events?mec_category=47"
    )
    shows = scraper.transformation_pipeline.transform(data)

    assert len(shows) == 1
    assert shows[0].name == "Improv in the Moonlight"
    assert shows[0].show_page_url == "https://moonlighttheatre.com/events/future"
    assert shows[0].tickets[0].price == 10.0


@pytest.mark.asyncio
async def test_transformation_pipeline_produces_show_from_mec_html_fallback(monkeypatch):
    scraper = ModernEventsCalendarScraper(_club())

    async def fake_collect_event_urls(source_url: str):
        return ["https://moonlighttheatre.com/events/bob-marley/"]

    async def fake_fetch_detail_html(url: str):
        return _mec_html_without_json_ld()

    monkeypatch.setattr(scraper, "_collect_event_urls", fake_collect_event_urls)
    monkeypatch.setattr(scraper, "_fetch_detail_html", fake_fetch_detail_html)

    data = await scraper.get_data(
        "https://moonlighttheatre.com/wp-json/wp/v2/mec-events?mec_category=47"
    )
    shows = scraper.transformation_pipeline.transform(data)

    assert len(shows) == 1
    assert shows[0].name == "Comedian Bob Marley"
    assert shows[0].show_page_url == "https://moonlighttheatre.com/events/bob-marley"
    assert shows[0].tickets[0].price == 39.5
    assert shows[0].tickets[0].purchase_url == (
        "https://www.eventbrite.com/e/comedian-bob-marley-tickets-1983822484454"
    )
