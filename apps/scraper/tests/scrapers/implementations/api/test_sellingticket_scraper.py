"""Tests for the generic SellingTicket HTML list scraper."""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.sellingticket.extractor import (
    SellingTicketExtractor,
)
from laughtrack.scrapers.implementations.api.sellingticket.scraper import (
    GenericSellingTicketScraper,
)


LIST_URL = (
    "https://secure.sellingticket.com/design22/clients/list/"
    "index_byUserListAll.aspx?OrganizationID=64"
)


def _club(metadata: dict | None = None) -> Club:
    club = Club(
        id=2572,
        name="Polk Theatre Florida",
        address="121 South Florida Avenue, Lakeland FL",
        website="https://www.polktheatre.org",
        popularity=0,
        zip_code="33801",
        phone_number="863-682-7553",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1581,
        club_id=club.id,
        platform="custom",
        scraper_key="sellingticket",
        source_url=LIST_URL,
        external_id=None,
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _html() -> str:
    return """
    <table>
      <tr>
        <td>Title Event</td><td>Address</td><td>WeekDay</td>
        <td>Date &amp; Time</td><td>Ticket</td>
      </tr>
      <tr>
        <td>Film: The Graduate</td>
        <td>121 South Florida Avenue, Lakeland FL</td>
        <td>Monday</td>
        <td>5/18/2026 6:30:00 PM</td>
        <td><a href="/design22/clients/index.aspx?designID=38526&amp;OrganizationID=64">Buy</a></td>
      </tr>
      <tr>
        <td>OMGITSWICKS &amp; FRIENDS pres. by Brickhouse Comedy Prod.</td>
        <td>121 South Florida Avenue, Lakeland FL</td>
        <td>Saturday</td>
        <td>8/29/2026 7:00:00 PM</td>
        <td><a href="/design22/clients/index.aspx?designID=38435&amp;OrganizationID=64">Buy</a></td>
      </tr>
    </table>
    """


def test_extractor_parses_event_rows_and_absolute_ticket_urls():
    events = SellingTicketExtractor.extract_events(_html(), LIST_URL)

    assert len(events) == 2
    assert events[0].title == "Film: The Graduate"
    assert events[0].date_time == "5/18/2026 6:30:00 PM"
    assert events[0].ticket_url == (
        "https://secure.sellingticket.com/design22/clients/index.aspx"
        "?designID=38526&OrganizationID=64"
    )
    assert events[1].title == "OMGITSWICKS & FRIENDS pres. by Brickhouse Comedy Prod."


@pytest.mark.asyncio
async def test_scraper_applies_metadata_include_patterns(monkeypatch):
    async def fake_fetch_html(self, url: str):
        return _html()

    monkeypatch.setattr(GenericSellingTicketScraper, "fetch_html", fake_fetch_html)

    scraper = GenericSellingTicketScraper(
        _club(metadata={"include_title_patterns": ["Comedy", "OMGITSWICKS"]})
    )

    page_data = await scraper.get_data(LIST_URL)

    assert page_data is not None
    assert [event.title for event in page_data.event_list] == [
        "OMGITSWICKS & FRIENDS pres. by Brickhouse Comedy Prod."
    ]


def test_event_converts_to_show_with_local_timezone():
    event = SellingTicketExtractor.extract_events(_html(), LIST_URL)[1]

    show = event.to_show(_club(), enhanced=False)

    assert show is not None
    assert show.name == "OMGITSWICKS & FRIENDS pres. by Brickhouse Comedy Prod."
    assert show.date.isoformat() == "2026-08-29T19:00:00-04:00"
    assert show.tickets[0].purchase_url.endswith("designID=38435&OrganizationID=64")
    assert "comedy" in show.supplied_tags
