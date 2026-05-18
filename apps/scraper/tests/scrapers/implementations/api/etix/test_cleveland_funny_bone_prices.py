"""Cleveland Funny Bone Etix/Funny Bone listing price extraction."""

import pytest


ETIX_URL = "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=31603&orderBy=1&pageNumber=1"
SHOWS_URL = "https://cleveland.funnybone.com/shows/"
SOLO_TICKET_URL = "https://www.etix.com/ticket/p/11111111/kym-whitley-cleveland-funny-bone?partner_id=100"
SERIES_TICKET_URL = "https://www.etix.com/ticket/p/22222222/tony-roberts-cleveland-funny-bone?partner_id=100"
SOLO_EVENT_URL = "https://cleveland.funnybone.com/event/kym-whitley/cleveland-funny-bone/"
SERIES_EVENT_URL = "https://cleveland.funnybone.com/events/category/series/tony-roberts/cleveland-funny-bone/"


def _club():
    from laughtrack.core.entities.club.model import Club, ScrapingSource

    club = Club(
        id=1050,
        name="Cleveland Funny Bone",
        address="1148 Main Ave",
        website="https://cleveland.funnybone.com",
        popularity=0,
        zip_code="44113",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1500,
        club_id=club.id,
        platform="etix",
        scraper_key="etix",
        source_url="https://www.etix.com/ticket/v/31603/funny-bone-comedy-club-cleveland",
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _shows_html(include_price: bool = True) -> str:
    solo_price = (
        """
        <div class="eventCost rhp-event__cost--list">
          <span class="rhp-event__cost-text--list"> $60 to $100 </span>
        </div>
        """
        if include_price
        else ""
    )
    series_price = (
        """
        <div class="seriesCostDiv">
          <span class="rhp-event-price rhp-event__cost--list">$32 - $42</span>
        </div>
        """
        if include_price
        else ""
    )
    return f"""
    <html><body>
      <span class="rhp-events-list-separator-month"><span>May 2026</span></span>

      <div class="rhp-event__single-event--list eventWrapper">
        <a class="url" href="{SOLO_EVENT_URL}" title="Kym Whitley">
          <div class="eventMonth singleEventDate" id="eventDate">Fri, May 08</div>
        </a>
        <h2 class="rhp-event__title--list">Kym Whitley</h2>
        <span class="rhp-event__time-text--list">Doors: 6 pm // Show: 7 pm</span>
        {solo_price}
        <a class="btn btn-primary" href="{SOLO_TICKET_URL}" title="BUY TICKETS">BUY TICKETS</a>
      </div>

      <div class="rhp-event__single-series--list eventWrapper">
        <h2 class="rhp-event__title--list rhpEventHeader">
          <a class="url" href="{SERIES_EVENT_URL}" title="Tony Roberts">Tony Roberts</a>
        </h2>
        {series_price}
        <ul class="rhp-event-series-list">
          <li class="rhp-event-series-individual">
            <div class="rhp-event-series-date">May 09</div>
            <div class="rhp-event-series-time">Doors: 6 pm // Show: 7:30 pm</div>
            <a class="btn" href="{SERIES_TICKET_URL}" title="Tickets">Tickets</a>
          </li>
        </ul>
      </div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_public_listing_extracts_visible_price_ranges(monkeypatch):
    from laughtrack.scrapers.implementations.api.etix.data import EtixPageData
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    scraper = EtixScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        if url == ETIX_URL:
            return "<html><title>DataDome</title></html>"
        raise AssertionError(f"unexpected fetch_html: {url}")

    async def fake_fetch_html_bare(self, url: str) -> str:
        if url == SHOWS_URL:
            return _shows_html()
        raise AssertionError(f"unexpected fetch_html_bare: {url}")

    monkeypatch.setattr(EtixScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(EtixScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data(ETIX_URL)

    assert isinstance(result, EtixPageData)
    by_title = {event.title: event for event in result.event_list}
    assert by_title["Kym Whitley"].ticket_price == 60.0
    assert by_title["Tony Roberts"].ticket_price == 32.0


def test_etix_event_to_show_uses_extracted_price_range():
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    event = EtixScraper(_club())._extract_funny_bone_events(_shows_html())[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.tickets[0].price == 60.0


def test_missing_price_remains_null_instead_of_free():
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    event = EtixScraper(_club())._extract_funny_bone_events(
        _shows_html(include_price=False)
    )[0]

    show = event.to_show(_club())

    assert event.ticket_price is None
    assert show is not None
    assert show.tickets[0].price is None
