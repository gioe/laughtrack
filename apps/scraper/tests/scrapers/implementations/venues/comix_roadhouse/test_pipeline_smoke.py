"""Pipeline smoke tests for ComixRoadhouseScraper."""

from datetime import date

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.comix_roadhouse.extractor import (
    ComixRoadhouseExtractor,
)
from laughtrack.scrapers.implementations.venues.comix_roadhouse.scraper import (
    ComixRoadhouseScraper,
)

SCRAPING_URL = "https://www.comixroadhouse.com/calendar/in-the-comedy-club"


def _club() -> Club:
    club = Club(
        id=9999,
        name="Comix Roadhouse",
        address="1 Mohegan Sun Blvd",
        website="https://www.comixroadhouse.com/",
        popularity=0,
        zip_code="06382",
        phone_number="860-862-7000",
        visible=True,
        timezone="America/New_York",
        city="Uncasville",
        state="CT",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="comix_roadhouse",
        source_url=SCRAPING_URL,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


LISTING_HTML = """
<html><body>
<div role="list">
  <div role="listitem">
    <a href="/comics/preacher-lawson-092626" class="schedule-event heaa w-inline-block">
      <div class="schedule-speaker-name aa">PREACHER LAWSON</div>
      <div class="schedule-event-time tp">Sep 24 - 26</div>
    </a>
  </div>
  <div role="listitem">
    <a href="/comics/line-dancing-jul2026" class="schedule-event heaa w-inline-block">
      <div class="schedule-speaker-name aa">LINE DANCING W/ J-KRAK</div>
      <div class="schedule-event-time tp">Jul 2 - 31</div>
    </a>
  </div>
</div>
<a href="?032cf745_page=2" aria-label="Next Page" class="w-pagination-next">Next</a>
</body></html>
"""


DETAIL_HTML = """
<html><body>
<h1>PREACHER LAWSON</h1>
<div class="schedule w-dyn-list">
  <div role="list" class="w-dyn-items">
    <div role="listitem" class="w-dyn-item">
      <a href="https://events.leapevents.com/event/preacher-lawson-092626k7ajclx"
         target="_blank" class="schedule-event com w-inline-block">
        <div class="schedule-speaker-name">PREACHER LAWSON</div>
        <div class="schedule-event-time">9/24/2026</div>
        <h6 class="nm">8:00 pm</h6>
        <div class="button small">Get Tickets</div>
      </a>
    </div>
    <div role="listitem" class="w-dyn-item">
      <a href="https://events.leapevents.com/event/preacher-lawson-092626ung7tzy"
         target="_blank" class="schedule-event com w-inline-block">
        <div class="schedule-speaker-name">PREACHER LAWSON</div>
        <div class="schedule-event-time">9/26/2026</div>
        <h6 class="nm">6:00 pm</h6>
        <div class="button small">Get Tickets</div>
      </a>
    </div>
  </div>
</div>
<div class="text-grey w-richtext"><p>High-energy stand-up comedian.</p></div>
</body></html>
"""


def test_extract_listing_urls_filters_non_comedy_utility_pages():
    urls = ComixRoadhouseExtractor.extract_listing_urls(LISTING_HTML)

    assert urls == ["https://www.comixroadhouse.com/comics/preacher-lawson-092626"]


def test_extract_next_page_url_from_webflow_pagination():
    next_url = ComixRoadhouseExtractor.extract_next_page_url(LISTING_HTML, SCRAPING_URL)

    assert next_url == "https://www.comixroadhouse.com/calendar/in-the-comedy-club?032cf745_page=2"


def test_extract_detail_events_with_ticket_urls():
    events = ComixRoadhouseExtractor.extract_events_from_detail(
        DETAIL_HTML,
        "https://www.comixroadhouse.com/comics/preacher-lawson-092626",
    )

    assert len(events) == 2
    assert [event.name for event in events] == ["PREACHER LAWSON", "PREACHER LAWSON"]
    assert [event.start_date for event in events] == ["2026-09-24 20:00:00", "2026-09-26 18:00:00"]
    assert [event.ticket_url for event in events] == [
        "https://events.leapevents.com/event/preacher-lawson-092626k7ajclx",
        "https://events.leapevents.com/event/preacher-lawson-092626ung7tzy",
    ]
    assert {event.show_page_url for event in events} == {
        "https://www.comixroadhouse.com/comics/preacher-lawson-092626"
    }


@pytest.mark.asyncio
async def test_get_data_fetches_listing_pages_and_detail_pages(monkeypatch):
    scraper = ComixRoadhouseScraper(_club())
    fetched = []

    pages = {
        SCRAPING_URL: LISTING_HTML,
        "https://www.comixroadhouse.com/calendar/in-the-comedy-club?032cf745_page=2": """
          <html><body>
            <a href="/comics/another-comic-100326" class="schedule-event heaa w-inline-block">
              <div class="schedule-speaker-name aa">ANOTHER COMIC</div>
              <div class="schedule-event-time tp">Oct 3</div>
            </a>
          </body></html>
        """,
        "https://www.comixroadhouse.com/comics/preacher-lawson-092626": DETAIL_HTML,
        "https://www.comixroadhouse.com/comics/another-comic-100326": DETAIL_HTML.replace(
            "PREACHER LAWSON", "ANOTHER COMIC"
        ).replace("9/24/2026", "10/3/2026"),
    }

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        fetched.append(url)
        return pages[url]

    monkeypatch.setattr(ComixRoadhouseScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(SCRAPING_URL)

    assert result is not None
    assert len(result.event_list) == 4
    assert fetched == [
        SCRAPING_URL,
        "https://www.comixroadhouse.com/calendar/in-the-comedy-club?032cf745_page=2",
        "https://www.comixroadhouse.com/comics/preacher-lawson-092626",
        "https://www.comixroadhouse.com/comics/another-comic-100326",
    ]


def test_scraper_class_has_correct_key():
    assert ComixRoadhouseScraper.key == "comix_roadhouse"
