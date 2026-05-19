"""Tests for the Troy Savings Bank Music Hall official-events scraper."""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.troy_savings_bank_music_hall.data import (
    TroySavingsBankMusicHallPageData,
)
from laughtrack.scrapers.implementations.venues.troy_savings_bank_music_hall.extractor import (
    TroySavingsBankMusicHallExtractor,
)
from laughtrack.scrapers.implementations.venues.troy_savings_bank_music_hall.scraper import (
    TroySavingsBankMusicHallScraper,
)

LIST_URL = "https://www.troymusichall.org/events/?searchType=7"
LESLIE_DETAIL_URL = "https://www.troymusichall.org/events/3012/leslie-jones-i-m-hot-tour-/"
LESLIE_TICKET_URL = "https://cart.troymusichall.org/33985/leslie-jones-im-hot-tour"


def _club() -> Club:
    club = Club(
        id=2579,
        name="Troy Savings Bank Music Hall",
        address="30 Second Street",
        website="https://www.troymusichall.org/",
        popularity=0,
        city="Troy",
        state="NY",
        zip_code="12180",
        phone_number="518-273-0038",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1700,
        club_id=club.id,
        platform="custom",
        scraper_key="troy_savings_bank_music_hall",
        source_url=LIST_URL,
        external_id=None,
        metadata={},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _listing_html() -> str:
    return """
    <div class="row">
      <div class="col-lg-4 col-md-6 item">
        <div class="show-item">
          <div class="show-date-short">
            <span class="month">Jun</span>
            <span class="day">14 </span>
            <span class="time">2:00PM</span>
          </div>
          <div class="show-title">
            <a href="https://www.troymusichall.org/events/3010/late-nite-catechism/"
               title="Late Nite Catechism 3: Til Death Do Us Part">
               Late Nite Catechism 3: Til Death Do Us Part
            </a>
          </div>
          <div class="show-subHead"></div>
          <div class="show-links float">
            <a href="https://cart.troymusichall.org/28/late-nite-catechism" class="btn buyticket">Get Tickets!</a>
          </div>
        </div>
      </div>
      <div class="col-lg-4 col-md-6 item">
        <div class="show-item">
          <div class="show-date-short">
            <span class="month">Aug</span>
            <span class="day">11 </span>
            <span class="time">7:00PM</span>
          </div>
          <div class="show-title">
            <a href="https://www.troymusichall.org/events/3000/ilana-glazer-live-/" title="ILANA GLAZER LIVE!">ILANA GLAZER LIVE!</a>
          </div>
          <div class="show-subHead"></div>
          <div class="show-links float">
            <a href="https://cart.troymusichall.org/33985/ilana-glazer-live" class="btn buyticket">Get Tickets!</a>
          </div>
        </div>
      </div>
      <div class="col-lg-4 col-md-6 item">
        <div class="show-item">
          <div class="show-date-short">
            <span class="month">Aug</span>
            <span class="day">22 </span>
            <span class="time">7:00PM</span>
          </div>
          <div class="show-title">
            <a href="https://www.troymusichall.org/events/3017/please-don-t-destroy-live/" title="Please Don’t Destroy: LIVE">Please Don’t Destroy: LIVE</a>
          </div>
          <div class="show-subHead">Martin Herlihy, Ben Marshall and John Higgins perform an hour of live sketch comedy</div>
          <div class="show-links float">
            <a href="https://cart.troymusichall.org/33985/please-dont-destroy-live" class="btn buyticket">Get Tickets!</a>
          </div>
        </div>
      </div>
      <div class="col-lg-4 col-md-6 item">
        <div class="show-item">
          <div class="show-date-short">
            <span class="month">Oct</span>
            <span class="day">10 </span>
            <span class="time">8:00PM</span>
          </div>
          <div class="show-title">
            <a href="https://www.troymusichall.org/events/3012/leslie-jones-i-m-hot-tour-/" title="Leslie Jones: I’m Hot Tour ">Leslie Jones: I’m Hot Tour </a>
          </div>
          <div class="show-subHead"></div>
          <div class="show-links float">
            <a href="https://cart.troymusichall.org/33985/leslie-jones-im-hot-tour" class="btn buyticket">Get Tickets!</a>
          </div>
        </div>
      </div>
      <div class="col-lg-4 col-md-6 item">
        <div class="show-item">
          <div class="show-date-short">
            <span class="month">Oct</span>
            <span class="day">23 </span>
            <span class="time">7:30PM</span>
          </div>
          <div class="show-title">
            <a href="https://www.troymusichall.org/events/3016/whose-line-is-it-anyway-/" title="Whose Live Anyway?">Whose Live Anyway?</a>
          </div>
          <div class="show-subHead"></div>
          <div class="show-links float">
            <a href="https://cart.troymusichall.org/34242/whose-live-anyway" class="btn buyticket">Get Tickets!</a>
          </div>
        </div>
      </div>
    </div>
    """


def _detail_html() -> str:
    return """
    <div id="shows-tickets">
      <div class="show-date-short" itemprop="startDate" content="2026-10-10T20:00">
        <span class="month">Oct</span><span class="day">10 </span><span class="time">8:00PM</span>
      </div>
      <div class="eventName" itemprop="name performer">Leslie Jones: I’m Hot Tour </div>
      <div class="show-links float">
        <a href="https://cart.troymusichall.org/33985/leslie-jones-im-hot-tour" class="btn buyticket">Get Tickets!</a>
      </div>
      <div class="editor show-desc-editor">
        Leslie Jones is a three-time Primetime Emmy Award nominee and co-hosts THE FCKRY with comedian Lenny Marcus.
      </div>
    </div>
    """


def test_extractor_parses_current_comedy_listing_events():
    events = TroySavingsBankMusicHallExtractor.extract_listing_events(_listing_html(), LIST_URL)

    assert [event.title for event in events] == [
        "Late Nite Catechism 3: Til Death Do Us Part",
        "ILANA GLAZER LIVE!",
        "Please Don’t Destroy: LIVE",
        "Leslie Jones: I’m Hot Tour",
        "Whose Live Anyway?",
    ]
    leslie = events[3]
    assert leslie.date_str == "Oct 10 2026"
    assert leslie.time_str == "8:00PM"
    assert leslie.detail_url == LESLIE_DETAIL_URL
    assert leslie.ticket_url == LESLIE_TICKET_URL


def test_detail_enrichment_adds_description_and_ticket_url():
    event = TroySavingsBankMusicHallExtractor.extract_listing_events(
        _listing_html(),
        LIST_URL,
    )[3]

    enriched = TroySavingsBankMusicHallExtractor.enrich_event_from_detail_page(
        event,
        _detail_html(),
    )

    assert enriched.ticket_url == LESLIE_TICKET_URL
    assert enriched.date_str == "Oct 10 2026"
    assert enriched.time_str == "8:00PM"
    assert "three-time Primetime Emmy Award nominee" in enriched.description
    assert "comedian Lenny Marcus" in enriched.description


def test_detail_enrichment_uses_detail_year_when_list_year_is_stale():
    event = TroySavingsBankMusicHallExtractor.extract_listing_events(
        _listing_html(),
        LIST_URL,
        year=2027,
    )[3]

    enriched = TroySavingsBankMusicHallExtractor.enrich_event_from_detail_page(
        event,
        _detail_html(),
    )

    assert event.date_str == "Oct 10 2027"
    assert enriched.date_str == "Oct 10 2026"
    assert enriched.time_str == "8:00PM"


@pytest.mark.asyncio
async def test_scraper_fetches_list_and_detail_pages(monkeypatch):
    fetched_urls: list[str] = []

    async def fake_fetch_html(self, url: str):
        fetched_urls.append(url)
        if url == LIST_URL:
            return _listing_html()
        return _detail_html()

    monkeypatch.setattr(TroySavingsBankMusicHallScraper, "fetch_html", fake_fetch_html)
    scraper = TroySavingsBankMusicHallScraper(_club())

    page_data = await scraper.get_data(LIST_URL)

    assert isinstance(page_data, TroySavingsBankMusicHallPageData)
    assert len(page_data.event_list) == 5
    assert page_data.event_list[3].description.startswith("Leslie Jones is")
    assert f"{LESLIE_DETAIL_URL}?" in fetched_urls


def test_event_converts_leslie_jones_to_local_show():
    event = TroySavingsBankMusicHallExtractor.enrich_event_from_detail_page(
        TroySavingsBankMusicHallExtractor.extract_listing_events(_listing_html(), LIST_URL)[3],
        _detail_html(),
    )

    show = event.to_show(_club(), enhanced=False)

    assert show is not None
    assert show.name == "Leslie Jones: I’m Hot Tour"
    assert show.date.isoformat() == "2026-10-10T20:00:00-04:00"
    assert show.show_page_url == f"{LESLIE_DETAIL_URL}?"
    assert show.tickets[0].purchase_url == LESLIE_TICKET_URL
    assert "comedy" in show.supplied_tags
