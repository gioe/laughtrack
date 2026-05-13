"""Pipeline smoke tests for the Soboba Casino Resort calendar scraper."""

from datetime import date

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.soboba_casino_resort import SobobaCasinoResortEvent
from laughtrack.scrapers.implementations.venues.soboba_casino_resort.data import (
    SobobaCasinoResortPageData,
)
from laughtrack.scrapers.implementations.venues.soboba_casino_resort.extractor import (
    SobobaCasinoResortExtractor,
)
from laughtrack.scrapers.implementations.venues.soboba_casino_resort.scraper import (
    SobobaCasinoResortScraper,
)

CALENDAR_URL = "https://soboba.com/entertainment/calendar"
JUNE_URL = "https://soboba.com/entertainment/calendar/monthly/2026/6/list"
MAY_URL = "https://soboba.com/entertainment/calendar/monthly/2026/5/list"
JULY_URL = "https://soboba.com/entertainment/calendar/monthly/2026/7/list"
DETAIL_URL = "https://soboba.com/entertainment/calendar/event-center/dl-hughley"
TICKET_URL = "https://sobobacasino.yapsody.com/event/index/868865/dl-hughley"


def _club() -> Club:
    club = Club(
        id=2413,
        name="SCR Event Center at Soboba Casino Resort - Complex",
        address="22777 Soboba Rd",
        website="https://soboba.com",
        popularity=0,
        zip_code="92583",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="soboba_casino_resort",
        source_url=CALENDAR_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _listing_page() -> str:
    return f"""
    <html><body>
      <div class="calendar-list-item vevent hidden">
        <a href="/entertainment/calendar/cabaret-lounge/red-corvette" class="thumb"
           aria-labelled="Red Corvette, CABARET LOUNGE">
          <span class="screen-reader-only">Event Details</span>
        </a>
        <div class="nearest-date"><span>Jun</span><span>12</span><span>Friday</span></div>
        <div class="description">
          <h4 class="h2 small">Red Corvette</h4>
          <div class="dates">
            <abbr class="dtstart"> Jun 12, 2026 </abbr>
            <div class="times"><abbr title="8:00 PM">8:00 PM - 9:30 PM</abbr></div>
          </div>
        </div>
        <nav>
          <div class="cat-name">CABARET LOUNGE</div>
          <a class="button" href="/entertainment/calendar/cabaret-lounge/red-corvette">Event Details</a>
        </nav>
      </div>
      <div class="calendar-list-item vevent hidden">
        <a href="/entertainment/calendar/event-center/frankie-quinones" class="thumb"
           aria-labelled="Frankie Qui&ntilde;ones, SCR EVENT CENTER">
          <span class="screen-reader-only">Event Details</span>
        </a>
        <div class="nearest-date"><span>May</span><span>16</span><span>Saturday</span></div>
        <div class="description">
          <h4 class="h2 small">Frankie Qui&ntilde;ones</h4>
          <div class="dates">
            <abbr class="dtstart"> May 16, 2026 </abbr>
            <div class="times"><abbr title="8:00 PM">8:00 PM - 9:30 PM</abbr></div>
          </div>
        </div>
        <nav>
          <div class="cat-name">SCR EVENT CENTER</div>
          <a class="button" href="/entertainment/calendar/event-center/frankie-quinones">Event Details</a>
        </nav>
      </div>
      <div class="calendar-list-item vevent hidden">
        <a href="/entertainment/calendar/event-center/dl-hughley" class="thumb"
           aria-labelled="D.L. Hughley, SCR EVENT CENTER">
          <span class="screen-reader-only">Event Details</span>
        </a>
        <div class="nearest-date"><span>Jun</span><span>13</span><span>Saturday</span></div>
        <div class="description">
          <h4 class="h2 small">D.L. Hughley</h4>
          <div class="dates">
            <abbr class="dtstart"> Jun 13, 2026 </abbr>
            <div class="times"><abbr title="8:00 PM">8:00 PM - 9:30 PM</abbr></div>
          </div>
        </div>
        <nav>
          <div class="cat-name">SCR EVENT CENTER</div>
          <a class="button" href="/entertainment/calendar/event-center/dl-hughley">Event Details</a>
        </nav>
      </div>
      <div class="calendar-list-item vevent hidden">
        <a href="/entertainment/calendar/event-center/steve-trevino" class="thumb"
           aria-labelled="Steve Trevi&ntilde;o, SCR EVENT CENTER">
          <span class="screen-reader-only">Event Details</span>
        </a>
        <div class="nearest-date"><span>Jul</span><span>24</span><span>Friday</span></div>
        <div class="description">
          <h4 class="h2 small">Steve Trevi&ntilde;o</h4>
          <div class="dates">
            <abbr class="dtstart"> Jul 24, 2026 </abbr>
            <div class="times"><abbr title="9:00 PM">9:00 PM - 10:30 PM</abbr></div>
          </div>
        </div>
        <nav>
          <div class="cat-name">SCR EVENT CENTER</div>
          <a class="button" href="/entertainment/calendar/event-center/steve-trevino">Event Details</a>
        </nav>
      </div>
    </body></html>
    """


def _detail_page() -> str:
    return f"""
    <html><body>
      <p class="dates">
        <small>Saturday, June 13, 2026</small>
        <abbr class="dtstart hide" title="2026-06-13">June 13, 2026</abbr>
      </p>
      <div class="times"><abbr title="8:00 PM">8:00 PM - 9:30 PM</abbr></div>
      <p>Soboba Casino Resort Event Center | June 13 | 8:00 PM - 9:30 PM | Doors open at 7 PM</p>
      <p>Where Comedy Meets Fearless Truth</p>
      <p><a class="button" title="Book Now" href="{TICKET_URL}" target="_blank">
        <span class="screen-reader-only">Book Now </span>Purchase Tickets
      </a></p>
    </body></html>
    """


def test_extract_listing_events_includes_hidden_load_more_cards():
    events = SobobaCasinoResortExtractor.extract_listing_events(_listing_page(), CALENDAR_URL)

    assert len(events) == 4
    assert [event.title for event in events] == [
        "Red Corvette",
        "Frankie Quiñones",
        "D.L. Hughley",
        "Steve Treviño",
    ]
    dl_hughley = events[2]
    assert dl_hughley.date_str == "Jun 13, 2026"
    assert dl_hughley.time_str == "8:00 PM"
    assert dl_hughley.room == "SCR EVENT CENTER"
    assert dl_hughley.detail_url == DETAIL_URL


def test_enrich_event_from_detail_page_adds_yapsody_ticket_url_and_description():
    event = SobobaCasinoResortExtractor.extract_listing_events(_listing_page(), CALENDAR_URL)[1]

    enriched = SobobaCasinoResortExtractor.enrich_event_from_detail_page(
        event,
        _detail_page(),
    )

    assert enriched.ticket_url == TICKET_URL
    assert "Where Comedy Meets Fearless Truth" in (enriched.description or "")


@pytest.mark.asyncio
async def test_collect_scraping_targets_uses_bounded_month_pagination(monkeypatch):
    scraper = SobobaCasinoResortScraper(_club(), max_months=3, start_date=date(2026, 5, 13))

    targets = await scraper.collect_scraping_targets()

    assert targets == [
        MAY_URL,
        JUNE_URL,
        JULY_URL,
    ]


@pytest.mark.asyncio
async def test_get_data_fetches_details_and_dedupes_events(monkeypatch):
    scraper = SobobaCasinoResortScraper(_club(), max_months=1)
    seen_urls: list[str] = []

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        seen_urls.append(url)
        if url == JUNE_URL:
            return _listing_page()
        if url == DETAIL_URL:
            return _detail_page()
        if url.endswith("/frankie-quinones"):
            return """
            <html><body>
              <p>Comedian and actor bringing nonstop laughs.</p>
              <p><a class="button" href="https://sobobacasino.yapsody.com/event/index/865983/frankie-quinones">Purchase Tickets</a></p>
            </body></html>
            """
        if url.endswith("/steve-trevino"):
            return """
            <html><body>
              <p>Steve turns everyday married life into comedy and big laughs.</p>
              <p><a class="button" href="https://sobobacasino.yapsody.com/event/index/865291/steve-trevino">Purchase Tickets</a></p>
            </body></html>
            """
        if url.endswith("/red-corvette"):
            return """
            <html><body>
              <p>A tribute concert celebrating the music of Prince.</p>
              <p><a class="button" href="https://sobobacasino.yapsody.com/event/index/868591/red-corvette-a-prince-tribute-band">Purchase Tickets</a></p>
            </body></html>
            """
        return ""

    monkeypatch.setattr(SobobaCasinoResortScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(JUNE_URL)

    assert isinstance(result, SobobaCasinoResortPageData)
    assert len(result.event_list) == 3
    assert [event.title for event in result.event_list] == [
        "Frankie Quiñones",
        "D.L. Hughley",
        "Steve Treviño",
    ]
    assert result.event_list[1].ticket_url == TICKET_URL
    assert seen_urls.count(DETAIL_URL) == 1


def test_to_show_uses_detail_page_and_yapsody_ticket_url():
    event = SobobaCasinoResortEvent(
        title="D.L. Hughley",
        date_str="Jun 13, 2026",
        time_str="8:00 PM",
        room="SCR EVENT CENTER",
        detail_url=DETAIL_URL,
        ticket_url=TICKET_URL,
        description="Where Comedy Meets Fearless Truth",
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "D.L. Hughley"
    assert show.date.year == 2026
    assert show.date.month == 6
    assert show.date.day == 13
    assert show.date.hour == 20
    assert show.room == "SCR EVENT CENTER"
    assert show.show_page_url == DETAIL_URL
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == TICKET_URL


def test_transformation_pipeline_produces_shows():
    scraper = SobobaCasinoResortScraper(_club())
    page_data = SobobaCasinoResortPageData(
        event_list=[
            SobobaCasinoResortEvent(
                title="D.L. Hughley",
                date_str="Jun 13, 2026",
                time_str="8:00 PM",
                room="SCR EVENT CENTER",
                detail_url=DETAIL_URL,
                ticket_url=TICKET_URL,
            )
        ]
    )

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert shows[0].name == "D.L. Hughley"
