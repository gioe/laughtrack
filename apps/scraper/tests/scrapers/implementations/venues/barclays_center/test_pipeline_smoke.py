"""Pipeline smoke tests for the Barclays Center comedy category scraper."""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.barclays_center.extractor import (
    BarclaysCenterExtractor,
)
from laughtrack.scrapers.implementations.venues.barclays_center.scraper import (
    BarclaysCenterScraper,
)

CATEGORY_URL = "https://www.barclayscenter.com/events/category/comedy"
DETAIL_URL = "https://www.barclayscenter.com/events/detail/nick-cannon-wild-n-out-live-no-filter-2026"
TICKET_URL = "https://www.ticketmaster.com/event/3000648FD9FB7F6A"
SPORTS_DETAIL_URL = "https://www.barclayscenter.com/events/detail/new-york-liberty-2026"


def _club() -> Club:
    club = Club(
        id=2464,
        name="Barclays Center",
        address="620 Atlantic Ave",
        website="https://www.barclayscenter.com",
        popularity=0,
        zip_code="11217",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="barclays_center",
        source_url=CATEGORY_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _listing_page() -> str:
    return f"""
    <html><body>
      <div id="list" class="list">
        <div class="entry featured clearfix">
          <div class="info clearfix">
            <a class="title-container" href="{DETAIL_URL} ">
              <div class="date grid-only btn btn-gradient">
                <span class="m-date__singleDate">
                  <span class="m-date__month">June </span>
                  <span class="m-date__day">28</span>
                </span>
              </div>
              <h3>Nick Cannon Presents Wild ‘N Out Live No Filter</h3>
            </a>
          </div>
          <div class="buttons event_buttons list-only show-on-hover button_count_2">
            <a class="tickets" href="{TICKET_URL}?CAMEFROM=CFC_BARCLAYS_CTR_WEB_EVENTPAGE_WILDNOUT">
              Buy Tickets
            </a>
            <a class="more" href="{DETAIL_URL}" title="More Info">Info</a>
          </div>
        </div>
      </div>
      <div class="entry clearfix">
        <a class="title-container" href="{SPORTS_DETAIL_URL}">
          <h3>New York Liberty vs Dallas Wings</h3>
        </a>
      </div>
    </body></html>
    """


def _detail_page() -> str:
    return f"""
    <html><body>
      <div class="content clearfix event-details">
        <h1 class="summary">Nick Cannon Presents Wild ‘N Out Live No Filter</h1>
        <div class="ticket btn-gradient">
          <a class="tickets" href="{TICKET_URL}?utm_source=barclayscenter.com" target="_blank">
            Buy Tickets
          </a>
        </div>
        <div class="detail_holder clearfix">
          <div class="details">
            <ul>
              <li class="date clearfix">
                <label>Date</label>
                <div class="info-bit-wrapper">
                  <span class="m-date__singleDate">
                    <span class="m-date__month">June </span>
                    <span class="m-date__day">28</span>
                    <span class="m-date__year">, 2026</span>
                  </span>
                </div>
                <span class="time">8:00PM</span>
              </li>
            </ul>
          </div>
        </div>
        <div class="event-info">
          <h2>Event Information</h2>
          Nick Cannon Presents Wild ‘N Out Live No Filter with Tim Chantarangsu,
          Michael Blackson, Rip Micheals, Maddy Smith, DC Young Fly, and DJ D-Wrek.
        </div>
      </div>
    </body></html>
    """


def test_extract_listing_events_uses_official_category_list_only():
    events = BarclaysCenterExtractor.extract_listing_events(_listing_page(), CATEGORY_URL)

    assert len(events) == 1
    assert events[0].title == "Nick Cannon Presents Wild ‘N Out Live No Filter"
    assert events[0].detail_url == DETAIL_URL
    assert events[0].ticket_url.startswith(TICKET_URL)


def test_enrich_event_from_detail_page_adds_date_time_ticket_and_description():
    event = BarclaysCenterExtractor.extract_listing_events(_listing_page(), CATEGORY_URL)[0]

    enriched = BarclaysCenterExtractor.enrich_event_from_detail_page(event, _detail_page())

    assert enriched.date_str == "June 28, 2026"
    assert enriched.time_str == "8:00PM"
    assert enriched.ticket_url.startswith(TICKET_URL)
    assert "Michael Blackson" in (enriched.description or "")


def test_event_to_show_uses_detail_url_as_show_page_and_ticketmaster_ticket():
    event = BarclaysCenterExtractor.enrich_event_from_detail_page(
        BarclaysCenterExtractor.extract_listing_events(_listing_page(), CATEGORY_URL)[0],
        _detail_page(),
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Nick Cannon Presents Wild ‘N Out Live No Filter"
    assert show.show_page_url == DETAIL_URL
    assert show.date.year == 2026
    assert show.date.hour == 20
    assert show.tickets[0].purchase_url.startswith(TICKET_URL)


@pytest.mark.asyncio
async def test_get_data_fetches_detail_pages_and_returns_enriched_events(monkeypatch):
    scraper = BarclaysCenterScraper(_club())
    seen_urls: list[str] = []

    async def fake_fetch_html(url: str, **kwargs) -> str:
        seen_urls.append(url)
        if url == CATEGORY_URL:
            return _listing_page()
        if url == DETAIL_URL:
            return _detail_page()
        return ""

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)

    page_data = await scraper.get_data(CATEGORY_URL)

    assert page_data is not None
    assert [event.title for event in page_data.event_list] == [
        "Nick Cannon Presents Wild ‘N Out Live No Filter"
    ]
    assert seen_urls == [CATEGORY_URL, DETAIL_URL]
