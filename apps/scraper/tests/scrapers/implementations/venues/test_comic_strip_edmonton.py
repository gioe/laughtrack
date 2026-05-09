"""Tests for The Comic Strip West Edmonton Mall Webflow card scraper."""

from datetime import datetime

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.tixr.webflow_day_card import (
    WebflowDayCardExtractor,
    WebflowDayCardPageData,
)
from laughtrack.scrapers.implementations.venues.comic_strip_edmonton.scraper import (
    ComicStripEdmontonScraper,
)

_SOURCE_URL = "https://wem.thecomicstrip.ca/"
_EVENT_URL = "https://www.tixr.com/groups/comicstripedmonton/events/sean-lecomber-185406"


def _club() -> Club:
    club = Club(
        id=2002,
        name="The Comic Strip West Edmonton Mall",
        address="8882 170 Street NW, Unit 1646, Edmonton, AB T5T 4M2",
        website="https://wem.thecomicstrip.ca/",
        popularity=0,
        zip_code="T5T 4M2",
        phone_number="780-483-5999",
        visible=True,
        timezone="America/Edmonton",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="comic_strip_edmonton",
        source_url=_SOURCE_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _homepage_html() -> str:
    return f"""<html><body>
<a class="day-card w-inline-block" href="{_EVENT_URL}" target="_blank">
  <div class="event-name show">Sean Lecomber</div>
  <div class="when-where">
    <p class="b-venue lrg">Thursday</p>
    <p class="event-name spaced">East Village</p>
    <div class="date">
      <p class="b-venue">May 7, 2026</p>
      <p class="b-venue">7:30 pm</p>
    </div>
  </div>
  <div>BUY TICKETS</div>
</a>
<a class="day-card w-inline-block" href="{_EVENT_URL}" target="_blank">
  <div class="event-name show">Sean Lecomber Duplicate</div>
  <div class="date"><p class="b-venue">May 7, 2026</p><p class="b-venue">7:30 pm</p></div>
</a>
</body></html>"""


def test_extractor_parses_edmonton_comic_strip_webflow_event_cards():
    events = WebflowDayCardExtractor.extract_events(
        _homepage_html(),
        source_url=_SOURCE_URL,
        config=ComicStripEdmontonScraper.config,
    )

    assert len(events) == 1
    assert events[0].title == "Sean Lecomber"
    assert events[0].date == "2026-05-07"
    assert events[0].time == "7:30 PM"
    assert events[0].room == "East Village"
    assert events[0].ticket_url == _EVENT_URL


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_edmonton_comic_strip_events(monkeypatch):
    scraper = ComicStripEdmontonScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _homepage_html()

    monkeypatch.setattr(ComicStripEdmontonScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(_SOURCE_URL)

    assert isinstance(result, WebflowDayCardPageData)
    assert len(result.event_list) == 1


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_edmonton_comic_strip_event_cards(monkeypatch):
    scraper = ComicStripEdmontonScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return "<html><body>No shows scheduled</body></html>"

    monkeypatch.setattr(ComicStripEdmontonScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(_SOURCE_URL)

    assert result is None


def test_transformation_pipeline_produces_edmonton_comic_strip_show():
    scraper = ComicStripEdmontonScraper(_club())
    page_data = WebflowDayCardPageData(
        event_list=WebflowDayCardExtractor.extract_events(
            _homepage_html(),
            source_url=_SOURCE_URL,
            config=ComicStripEdmontonScraper.config,
        )
    )

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert isinstance(shows[0], Show)
    assert shows[0].name == "Sean Lecomber"
    assert shows[0].show_page_url == _EVENT_URL
    assert shows[0].date == datetime(2026, 5, 7, 19, 30, tzinfo=shows[0].date.tzinfo)
