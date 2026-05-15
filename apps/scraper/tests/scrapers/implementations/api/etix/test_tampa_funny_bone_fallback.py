"""Tampa Funny Bone Etix-block fallback (TASK-2008).

When the generic Etix scrape returns no events for venue_id 31600 — typical
when DataDome blocks the upstream Etix venue page — the scraper falls back
to parsing tampa.funnybone.com/shows/, the venue's own Rockhouse-Partners
event widget. It exposes title, date, show time, ticket URL, and event URL
on a single listing.
"""

import pytest


ETIX_URL = "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=31600&orderBy=1&pageNumber=1"
SHOWS_URL = "https://tampa.funnybone.com/shows/"
SOLO_TICKET_URL = "https://www.etix.com/ticket/p/42669966/mic-nite-tampa-funny-bone-comedy-club-tampa?partner_id=100"
SERIES_TICKET_URL_1 = "https://www.etix.com/ticket/p/60545297/damn-gina-tampa-funny-bone-comedy-club-tampa?partner_id=100"
SERIES_TICKET_URL_2 = "https://www.etix.com/ticket/p/62353810/damn-gina-tampa-funny-bone-comedy-club-tampa?partner_id=100"
SOLO_EVENT_URL = "https://tampa.funnybone.com/event/mic-nite-114/tampa-funny-bone/"
SERIES_EVENT_URL = "https://tampa.funnybone.com/events/category/series/damn-gina/tampa-funny-bone/"


def _club():
    from laughtrack.core.entities.club.model import Club, ScrapingSource

    club = Club(
        id=1053,
        name="Tampa Funny Bone",
        address="1600 E 8th Ave C-112",
        website="https://tampa.funnybone.com",
        popularity=0,
        zip_code="33605",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=550,
        club_id=club.id,
        platform="etix",
        scraper_key="etix",
        source_url="https://www.etix.com/ticket/v/31600/funny-bone-comedy-club-tampa",
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _shows_html() -> str:
    """Minimal Rockhouse-Partners widget covering: solo, series, and an
    Unavailable date that must be skipped. The May 2026 separator is
    consumed for year context.
    """
    return f"""
    <html><body>
      <span class="rhp-events-list-separator-month"><span>May 2026</span></span>

      <div class="rhp-event__single-event--list eventWrapper">
        <a class="url" href="{SOLO_EVENT_URL}" title="Mic Nite">
          <div class="eventMonth singleEventDate" id="eventDate">Thu, May 07</div>
        </a>
        <h2 class="rhp-event__title--list">Mic Nite</h2>
        <span class="rhp-event__time-text--list">Doors: 7 pm // Show: 8 pm</span>
        <a class="btn btn-primary" href="{SOLO_TICKET_URL}" title="BUY TICKETS">BUY TICKETS</a>
      </div>

      <div class="rhp-event__single-series--list eventWrapper">
        <h2 class="rhp-event__title--list rhpEventHeader">
          <a class="url" href="{SERIES_EVENT_URL}" title="Damn Gina">Damn Gina</a>
        </h2>
        <ul class="rhp-event-series-list">
          <li class="rhp-event-series-individual">
            <div class="rhp-event-series-date">May 07</div>
            <div class="rhp-event-series-time">Doors: 5:45 pm // Show: 7 pm</div>
            <span class="rhp-event-cta off-sale">
              <a href="javascript:void(0)" title="Unavailable">Unavailable</a>
            </span>
          </li>
          <li class="rhp-event-series-individual">
            <div class="rhp-event-series-date">May 08</div>
            <div class="rhp-event-series-time">Doors: 6:15 pm // Show: 7:30 pm</div>
            <a class="btn" href="{SERIES_TICKET_URL_1}" title="Tickets">Tickets</a>
          </li>
          <li class="rhp-event-series-individual">
            <div class="rhp-event-series-date">May 09</div>
            <div class="rhp-event-series-time">Doors: 5:15 pm // Show: 6:30 pm</div>
            <a class="btn" href="{SERIES_TICKET_URL_2}" title="Tickets">Tickets</a>
          </li>
        </ul>
      </div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_tampa_funny_bone_fallback_uses_public_listing(monkeypatch):
    from laughtrack.scrapers.implementations.api.etix.data import EtixPageData
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    scraper = EtixScraper(_club())
    fetch_html_calls: list[str] = []
    fetch_bare_calls: list[str] = []

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        fetch_html_calls.append(url)
        if url == ETIX_URL:
            # DataDome interstitial — Etix returns no events.
            return "<html><title>DataDome</title></html>"
        raise AssertionError(f"unexpected fetch_html: {url}")

    async def fake_fetch_html_bare(self, url: str) -> str:
        fetch_bare_calls.append(url)
        if url == SHOWS_URL:
            return _shows_html()
        raise AssertionError(f"unexpected fetch_html_bare: {url}")

    monkeypatch.setattr(EtixScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(EtixScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data(ETIX_URL)

    assert isinstance(result, EtixPageData)
    assert fetch_bare_calls == [SHOWS_URL]

    # Three rows: 1 solo + 2 in-stock series dates. The "Unavailable" row is skipped.
    assert len(result.event_list) == 3

    by_title_date = {(e.title, e.start_date): e for e in result.event_list}

    solo = by_title_date[("Mic Nite", "2026-05-07T20:00:00")]
    assert solo.ticket_url == SOLO_TICKET_URL
    assert solo.event_url == SOLO_EVENT_URL

    series_friday = by_title_date[("Damn Gina", "2026-05-08T19:30:00")]
    assert series_friday.ticket_url == SERIES_TICKET_URL_1
    assert series_friday.event_url == SERIES_EVENT_URL

    series_saturday = by_title_date[("Damn Gina", "2026-05-09T18:30:00")]
    assert series_saturday.ticket_url == SERIES_TICKET_URL_2


@pytest.mark.asyncio
async def test_tampa_funny_bone_fallback_returns_none_when_listing_empty(monkeypatch):
    """When the venue page is unreachable, the fallback returns None and the
    primary 'no events found' path runs."""
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    scraper = EtixScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><title>DataDome</title></html>"

    async def fake_fetch_html_bare(self, url: str) -> str:
        raise RuntimeError("403")

    monkeypatch.setattr(EtixScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(EtixScraper, "fetch_html_bare", fake_fetch_html_bare)

    result = await scraper.get_data(ETIX_URL)

    assert result is None


def test_tampa_funny_bone_fallback_only_triggers_for_venue_31600():
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
    assert not scraper._uses_funny_bone_fallback(other_etix)


@pytest.mark.asyncio
async def test_funny_bone_public_source_is_scrape_target(monkeypatch):
    from laughtrack.core.entities.club.model import Club, ScrapingSource
    from laughtrack.scrapers.implementations.api.etix.data import EtixPageData
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    club = Club(
        id=2462,
        name="Funny Bone Comedy Club (formerly Kansas City Improv)",
        address="Kansas City, MO",
        website="https://kc.funnybone.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    club.active_scraping_source = ScrapingSource(
        id=1471,
        club_id=club.id,
        platform="etix",
        scraper_key="etix",
        source_url="https://kc.funnybone.com/",
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    scraper = EtixScraper(club)
    fetch_bare_calls: list[str] = []

    async def fake_fetch_html_bare(self, url: str) -> str:
        fetch_bare_calls.append(url)
        if url == "https://kc.funnybone.com/":
            return _shows_html()
        raise AssertionError(f"unexpected fetch_html_bare: {url}")

    monkeypatch.setattr(EtixScraper, "fetch_html_bare", fake_fetch_html_bare)

    targets = await scraper.collect_scraping_targets()
    result = await scraper.get_data(targets[0])

    assert targets == ["https://kc.funnybone.com/"]
    assert isinstance(result, EtixPageData)
    assert fetch_bare_calls == ["https://kc.funnybone.com/"]
    assert len(result.event_list) == 3
