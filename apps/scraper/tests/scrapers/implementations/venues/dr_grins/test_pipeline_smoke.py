"""Pipeline smoke tests for the Dr. Grins public-page scraper."""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.dr_grins import DrGrinsEvent
from laughtrack.scrapers.implementations.venues.dr_grins.data import (
    DrGrinsPageData,
)
from laughtrack.scrapers.implementations.venues.dr_grins.extractor import (
    DrGrinsExtractor,
)
from laughtrack.scrapers.implementations.venues.dr_grins.scraper import (
    DrGrinsScraper,
)

LISTING_URL = "https://www.thebob.com/drgrins/"
DETAIL_URL = "https://www.thebob.com/drgrins/comedian/index.html?id=514"
TICKET_URL = "https://www.etix.com/ticket/v/35455/drgrins-comedy-club-at-the-bob"


def _club() -> Club:
    club = Club(
        id=207,
        name="Dr. Grins Comedy Club",
        address="20 Monroe Ave NW",
        website="https://www.thebob.com/drgrins/",
        popularity=0,
        zip_code="49503",
        phone_number="",
        visible=True,
        timezone="America/Detroit",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="dr_grins",
        source_url=LISTING_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _listing_page() -> str:
    return f"""
    <html><body>
      <a href="{DETAIL_URL}">
        <div class="show-title">Andy Hendrickson</div>
        <div class="show-copy">May&nbsp;7-9&nbsp;@ Dr. Grins</div>
      </a>
      <a href="{DETAIL_URL}">
        <div class="show-title">Andy Hendrickson</div>
      </a>
      <a href="https://www.thebob.com/drgrins/comedian/index.html?id=1080">
        <div class="show-title">Caitlin Peluffo</div>
      </a>
    </body></html>
    """


def _detail_page() -> str:
    return f"""
    <html><body>
      <div class="feature-title">Andy Hendrickson</div>
      <div class="button-box-feature">
        <a class="feature-button" href="{TICKET_URL}" target="_blank">Tickets</a>
      </div>
      <div class="show-date"><span class="bold">May&nbsp;7</span>&nbsp;&nbsp8pm&nbsp;$11.95</div>
      <div class="show-date"><span class="bold">May&nbsp;8</span>&nbsp;&nbsp7:15pm&nbsp;$16.95&nbsp;<span class="bold">&bull;</span>&nbsp;9:45pm&nbsp;$16.95</div>
      <div class="show-date"><span class="bold">May&nbsp;9</span>&nbsp;&nbsp7:15pm&nbsp;$21.95&nbsp;<span class="bold">&bull;</span>&nbsp;9:45pm&nbsp;$21.95</div>
    </body></html>
    """


def test_extract_detail_urls_dedupes_listing_links():
    urls = DrGrinsExtractor.extract_detail_urls(_listing_page())

    assert urls == [
        DETAIL_URL,
        "https://www.thebob.com/drgrins/comedian/index.html?id=1080",
    ]


def test_extract_events_expands_each_public_show_time():
    events = DrGrinsExtractor.extract_events(_detail_page(), detail_url=DETAIL_URL)

    assert len(events) == 5
    assert {event.title for event in events} == {"Andy Hendrickson"}
    assert [(event.date_str, event.time_str) for event in events] == [
        ("May 7", "8pm"),
        ("May 8", "7:15pm"),
        ("May 8", "9:45pm"),
        ("May 9", "7:15pm"),
        ("May 9", "9:45pm"),
    ]
    assert all(event.detail_url == DETAIL_URL for event in events)
    assert all(event.ticket_url == TICKET_URL for event in events)


@pytest.mark.asyncio
async def test_collect_scraping_targets_uses_public_bob_listing(monkeypatch):
    scraper = DrGrinsScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        assert url == LISTING_URL
        return _listing_page()

    monkeypatch.setattr(DrGrinsScraper, "fetch_html", fake_fetch_html)

    targets = await scraper.collect_scraping_targets()

    assert targets == [
        DETAIL_URL,
        "https://www.thebob.com/drgrins/comedian/index.html?id=1080",
    ]


@pytest.mark.asyncio
async def test_get_data_returns_page_data_from_public_detail(monkeypatch):
    scraper = DrGrinsScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        assert url == DETAIL_URL
        return _detail_page()

    monkeypatch.setattr(DrGrinsScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(DETAIL_URL)

    assert isinstance(result, DrGrinsPageData)
    assert len(result.event_list) == 5


def test_to_show_uses_public_detail_page_as_show_page():
    event = DrGrinsEvent(
        title="Andy Hendrickson",
        date_str="May 8",
        time_str="7:15pm",
        detail_url=DETAIL_URL,
        ticket_url=TICKET_URL,
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Andy Hendrickson"
    assert show.date.hour == 19
    assert show.date.minute == 15
    assert show.show_page_url == DETAIL_URL
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == TICKET_URL


def test_to_show_accepts_abbreviated_month_names():
    event = DrGrinsEvent(
        title="Al Jackson",
        date_str="Jun 4",
        time_str="8pm",
        detail_url="https://www.thebob.com/drgrins/comedian/index.html?id=815",
        ticket_url=TICKET_URL,
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.date.month == 6
    assert show.date.day == 4
    assert show.date.hour == 20


def test_to_show_returns_none_for_unparseable_time():
    event = DrGrinsEvent(
        title="Andy Hendrickson",
        date_str="May 8",
        time_str="not a time",
        detail_url=DETAIL_URL,
        ticket_url=TICKET_URL,
    )

    assert event.to_show(_club()) is None
