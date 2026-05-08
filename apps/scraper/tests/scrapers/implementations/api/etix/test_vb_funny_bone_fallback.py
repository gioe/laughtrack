"""Virginia Beach Funny Bone Etix-block fallback (TASK-2016).

When the generic Etix scrape returns no events for venue_id 31602 — typical
when DataDome blocks the upstream Etix venue page — the scraper falls back
to parsing vb.funnybone.com/shows/, the venue's own Rockhouse-Partners event
widget. The widget structure is identical to Tampa Funny Bone's, so the same
parser handles both venues; this file just exercises the VB-specific
``venue_id -> shows_url`` registry lookup end-to-end and pins the registry
contents.
"""

import pytest


ETIX_URL = "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=31602&orderBy=1&pageNumber=1"
SHOWS_URL = "https://vb.funnybone.com/shows/"
SOLO_TICKET_URL = "https://www.etix.com/ticket/p/12345678/comedian-x-virginia-beach-funny-bone?partner_id=100"
SERIES_TICKET_URL_1 = "https://www.etix.com/ticket/p/23456789/comedian-y-virginia-beach-funny-bone?partner_id=100"
SERIES_TICKET_URL_2 = "https://www.etix.com/ticket/p/34567890/comedian-y-virginia-beach-funny-bone?partner_id=100"
SOLO_EVENT_URL = "https://vb.funnybone.com/event/comedian-x/virginia-beach-funny-bone/"
SERIES_EVENT_URL = "https://vb.funnybone.com/events/category/series/comedian-y/virginia-beach-funny-bone/"


def _club():
    from laughtrack.core.entities.club.model import Club, ScrapingSource

    club = Club(
        id=1033,
        name="Virginia Beach Funny Bone",
        address="217 Central Park Ave",
        website="https://vb.funnybone.com",
        popularity=0,
        zip_code="23462",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=551,
        club_id=club.id,
        platform="etix",
        scraper_key="etix",
        source_url="https://www.etix.com/ticket/v/31602/funny-bone-comedy-club-virginia-beach",
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _shows_html() -> str:
    """Minimal Rockhouse-Partners widget covering: solo, series, and an
    Unavailable date that must be skipped. The May 2026 separator supplies
    year context.
    """
    return f"""
    <html><body>
      <span class="rhp-events-list-separator-month"><span>May 2026</span></span>

      <div class="rhp-event__single-event--list eventWrapper">
        <a class="url" href="{SOLO_EVENT_URL}" title="Comedian X">
          <div class="eventMonth singleEventDate" id="eventDate">Fri, May 08</div>
        </a>
        <h2 class="rhp-event__title--list">Comedian X</h2>
        <span class="rhp-event__time-text--list">Doors: 7 pm // Show: 8 pm</span>
        <a class="btn btn-primary" href="{SOLO_TICKET_URL}" title="BUY TICKETS">BUY TICKETS</a>
      </div>

      <div class="rhp-event__single-series--list eventWrapper">
        <h2 class="rhp-event__title--list rhpEventHeader">
          <a class="url" href="{SERIES_EVENT_URL}" title="Comedian Y">Comedian Y</a>
        </h2>
        <ul class="rhp-event-series-list">
          <li class="rhp-event-series-individual">
            <div class="rhp-event-series-date">May 09</div>
            <div class="rhp-event-series-time">Doors: 5:45 pm // Show: 7 pm</div>
            <span class="rhp-event-cta off-sale">
              <a href="javascript:void(0)" title="Unavailable">Unavailable</a>
            </span>
          </li>
          <li class="rhp-event-series-individual">
            <div class="rhp-event-series-date">May 10</div>
            <div class="rhp-event-series-time">Doors: 6:15 pm // Show: 7:30 pm</div>
            <a class="btn" href="{SERIES_TICKET_URL_1}" title="Tickets">Tickets</a>
          </li>
          <li class="rhp-event-series-individual">
            <div class="rhp-event-series-date">May 11</div>
            <div class="rhp-event-series-time">Doors: 5:15 pm // Show: 6:30 pm</div>
            <a class="btn" href="{SERIES_TICKET_URL_2}" title="Tickets">Tickets</a>
          </li>
        </ul>
      </div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_vb_funny_bone_fallback_uses_public_listing(monkeypatch):
    from laughtrack.scrapers.implementations.api.etix.data import EtixPageData
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    scraper = EtixScraper(_club())
    fetch_html_calls: list[str] = []
    fetch_bare_calls: list[str] = []

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        fetch_html_calls.append(url)
        if url == ETIX_URL:
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
    assert len(result.event_list) == 3

    by_title_date = {(e.title, e.start_date): e for e in result.event_list}

    solo = by_title_date[("Comedian X", "2026-05-08T20:00:00")]
    assert solo.ticket_url == SOLO_TICKET_URL
    assert solo.event_url == SOLO_EVENT_URL

    series_saturday = by_title_date[("Comedian Y", "2026-05-10T19:30:00")]
    assert series_saturday.ticket_url == SERIES_TICKET_URL_1
    assert series_saturday.event_url == SERIES_EVENT_URL

    series_sunday = by_title_date[("Comedian Y", "2026-05-11T18:30:00")]
    assert series_sunday.ticket_url == SERIES_TICKET_URL_2


def test_funny_bone_registry_contains_known_venues():
    """Registry pins both venues so an accidental edit can't silently lose either."""
    from laughtrack.scrapers.implementations.api.etix.scraper import _FUNNY_BONE_FALLBACKS

    assert _FUNNY_BONE_FALLBACKS["31600"] == "https://tampa.funnybone.com/shows/"
    assert _FUNNY_BONE_FALLBACKS["31602"] == "https://vb.funnybone.com/shows/"


def test_vb_funny_bone_predicate_triggers_for_venue_31602():
    from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper

    scraper = EtixScraper(_club())
    assert scraper._uses_funny_bone_fallback(ETIX_URL)
