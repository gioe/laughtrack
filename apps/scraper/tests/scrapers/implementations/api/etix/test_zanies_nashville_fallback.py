"""Zanies Nashville Etix-block fallback (TASK-2017)."""

import pytest

ETIX_URL = "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=21745&orderBy=1&pageNumber=1"
HOME_URL = "https://nashville.zanies.com/"
SOLO_TICKET_URL = "https://www.etix.com/ticket/p/73225030/karen-mills-nashville-the-lab-at-zanies?partner_id=100"
SERIES_TICKET_URL_1 = (
    "https://www.etix.com/ticket/p/84426459/marcus-d-wiley-nashville-zanies-comedy-night-club?partner_id=100"
)
SERIES_TICKET_URL_2 = (
    "https://www.etix.com/ticket/p/55358815/marcus-d-wiley-nashville-zanies-comedy-night-club?partner_id=100"
)
SOLO_EVENT_URL = "https://nashville.zanies.com/show/karen-mills-5/the-lab/"
SERIES_EVENT_URL = (
    "https://nashville.zanies.com/show/category/series/" "2026-marcus-d-wiley/zanies/nashville-tennessee/"
)


def _club():
    from laughtrack.core.entities.club.model import Club, ScrapingSource

    club = Club(
        id=1029,
        name="Zanies Comedy Night Club",
        address="2025 8th Ave S",
        website="https://nashville.zanies.com",
        popularity=0,
        zip_code="37204",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="etix",
        scraper_key="etix",
        source_url="https://www.etix.com/ticket/v/21745/zanies-comedy-night-club",
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _home_html() -> str:
    return f"""
    <html><body>
      <div class="eventWrapper rhpSingleEvent rhp-event__single-event--grid">
        <a class="url" href="{SOLO_EVENT_URL}"></a>
        <div class="eventMonth singleEventDate">Sun, May 10</div>
        <h2 class="rhp-event__title--grid">Karen Mills</h2>
        <div class="rhp-event__time">Doors: 5 pm Show: 6 pm</div>
        <a href="{SOLO_TICKET_URL}">Buy Tickets</a>
      </div>

      <div class="eventWrapper rhpEventSeries rhp-event__single-series--grid">
        <h2 class="rhpEventHeader">
          <a class="url" href="{SERIES_EVENT_URL}">2026 MARCUS D WILEY</a>
        </h2>
        <ul>
          <li class="rhp-event-series-individual">
            <div class="rhp-event-series-date">May 08</div>
            <div class="rhp-event-series-time">Doors: 5:30 pm Show: 7 pm</div>
            <a href="{SERIES_TICKET_URL_1}">Tickets</a>
          </li>
          <li class="rhp-event-series-individual">
            <div class="rhp-event-series-date">May 09</div>
            <div class="rhp-event-series-time">Doors: 5:30 pm Show: 7 pm</div>
            <a href="{SERIES_TICKET_URL_2}">Tickets</a>
          </li>
          <li class="rhp-event-series-individual">
            <div class="rhp-event-series-date">May 10</div>
            <div class="rhp-event-series-time">Doors: 7 pm Show: 7:30 pm</div>
            <a href="javascript:void(0)">Unavailable</a>
          </li>
        </ul>
      </div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_zanies_nashville_fallback_uses_owned_homepage(monkeypatch):
    from laughtrack.scrapers.implementations.api.etix.data import EtixPageData
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    scraper = EtixScraper(_club())
    calls: list[str] = []

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        calls.append(url)
        if url == ETIX_URL:
            return "<html><title>DataDome</title></html>"
        if url == HOME_URL:
            return _home_html()
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(EtixScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(ETIX_URL)

    assert isinstance(result, EtixPageData)
    assert calls == [ETIX_URL, HOME_URL]
    assert len(result.event_list) == 3

    by_title_date = {(e.title, e.start_date): e for e in result.event_list}

    solo = by_title_date[("Karen Mills", "2026-05-10T18:00:00")]
    assert solo.ticket_url == SOLO_TICKET_URL
    assert solo.event_url == SOLO_EVENT_URL

    series_friday = by_title_date[("MARCUS D WILEY", "2026-05-08T19:00:00")]
    assert series_friday.ticket_url == SERIES_TICKET_URL_1
    assert series_friday.event_url == SERIES_EVENT_URL

    series_saturday = by_title_date[("MARCUS D WILEY", "2026-05-09T19:00:00")]
    assert series_saturday.ticket_url == SERIES_TICKET_URL_2


def test_zanies_nashville_fallback_only_triggers_for_venue_21745():
    from laughtrack.core.entities.club.model import Club, ScrapingSource
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    other = Club(
        id=999,
        name="Some Other Etix Venue",
        address="x",
        website="https://example.com",
        popularity=0,
        zip_code="00000",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    other.active_scraping_source = ScrapingSource(
        id=1,
        club_id=other.id,
        platform="etix",
        scraper_key="etix",
        source_url="https://www.etix.com/ticket/v/12345/some-other-venue",
        external_id=None,
    )
    other.scraping_sources = [other.active_scraping_source]
    scraper = EtixScraper(other)

    other_etix = "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=12345&orderBy=1&pageNumber=1"
    assert not scraper._uses_zanies_nashville_fallback(other_etix)
