"""Pipeline smoke tests for TK's static Spothopper events page scraper."""

import pytest

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.tks_comedy.data import (
    TksComedyPageData,
)
from laughtrack.scrapers.implementations.venues.tks_comedy.extractor import (
    TksComedyExtractor,
)
from laughtrack.scrapers.implementations.venues.tks_comedy.scraper import (
    TksComedyScraper,
)

EVENTS_URL = "https://www.tkscomedy.com/dallas-addison-tk-s-comedy-events"


def _club() -> Club:
    club = Club(
        id=63,
        name="TK's",
        address="14854 Montfort Dr, Dallas, TX",
        website="https://www.tkscomedy.com",
        popularity=0,
        zip_code="75254",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="tks_comedy",
        source_url=EVENTS_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _events_page() -> str:
    return """
<html><body>
<div class="events-custom-page-content text-center">
  <h2>MUSIC UNDERGROUND / LIVE MUSIC SESSION / SPEAKEASY</h2>
  <p>Email <a href="mailto:events@tkscomedy.com">events@tkscomedy.com</a> to RSVP</p>
  <img alt="Music Underground Live Music in Speakeasy Saturday August 15 at 7pm free 2/ticket" />

  <h2>MOTHER'S DAY SOIREE'<br>BRUNCH PARTY &amp; LIVE STAND-UP COMEDY SHOW</h2>
  <div class="btn-holder">
    <a class="custom-temp-btn hvr-fade" href="https://square.link/u/gydh1Vft?src=sheet" target="_blank">
      Buy tickets<span class="visuallyhidden">for the MOTHER'S DAY SOIREE' BRUNCH PARTY &amp; LIVE STAND-UP COMEDY SHOW event</span>
    </a>
  </div>
  <p>Sunday, May 10th / Doors Open 10 am- 3 pm/ Live Stand-up Comedy show 1 pm / Live DJ / Photo Booth</p>
  <p>Epic Mother's Day Brunch Buffet + show $85 / seating from 10-12:30 pm / Live Comedy Show at 1 pm</p>

  <h2>Brunch Only - NO Show</h2>
  <div class="btn-holder">
    <a class="custom-temp-btn hvr-fade" href="https://square.link/u/CSB3Blyg?src=sheet" target="_blank">Buy tickets</a>
  </div>
  <p>$60 / seating begins 12:20 pm- last seating 2 pm</p>
</div>
</body></html>
"""


def test_extractor_returns_comedy_events_only():
    events = TksComedyExtractor.extract_events(_events_page())

    assert len(events) == 1
    assert events[0].title == "MOTHER'S DAY SOIREE' BRUNCH PARTY & LIVE STAND-UP COMEDY SHOW"
    assert events[0].date_label == "May 10"
    assert events[0].time_label == "1 pm"
    assert events[0].ticket_url == "https://square.link/u/gydh1Vft?src=sheet"


def test_to_show_creates_ticketed_show():
    event = TksComedyExtractor.extract_events(_events_page())[0]
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "MOTHER'S DAY SOIREE' BRUNCH PARTY & LIVE STAND-UP COMEDY SHOW"
    assert show.club_id == 63
    assert show.date.month == 5
    assert show.date.day == 10
    assert show.date.hour == 13
    assert show.date.minute == 0
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://square.link/u/gydh1Vft?src=sheet"


@pytest.mark.asyncio
async def test_get_data_parses_events_page(monkeypatch):
    scraper = TksComedyScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return _events_page()

    monkeypatch.setattr(TksComedyScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(EVENTS_URL)

    assert isinstance(result, TksComedyPageData)
    assert len(result.event_list) == 1


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_comedy_events(monkeypatch):
    scraper = TksComedyScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body><h2>MUSIC UNDERGROUND</h2><p>Live music at 7 pm</p></body></html>"

    monkeypatch.setattr(TksComedyScraper, "fetch_html", fake_fetch_html)

    assert await scraper.get_data(EVENTS_URL) is None


@pytest.mark.asyncio
async def test_collect_targets_uses_configured_events_page():
    scraper = TksComedyScraper(_club())

    assert await scraper.collect_scraping_targets() == [EVENTS_URL]


def test_transformation_pipeline_produces_shows():
    club = _club()
    scraper = TksComedyScraper(club)
    page_data = TksComedyPageData(event_list=TksComedyExtractor.extract_events(_events_page()))

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert all(isinstance(show, Show) for show in shows)


def test_scraper_key_is_discoverable():
    assert ScraperResolver().get("tks_comedy") is TksComedyScraper
