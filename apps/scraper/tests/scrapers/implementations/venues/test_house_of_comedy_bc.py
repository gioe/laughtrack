"""Tests for House of Comedy British Columbia Webflow card scraper."""

from datetime import datetime

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.tixr.webflow_day_card import (
    WebflowDayCardExtractor,
    WebflowDayCardPageData,
)
from laughtrack.scrapers.implementations.venues.house_of_comedy_bc.scraper import (
    HouseOfComedyBcScraper,
)

_SOURCE_URL = "https://bc.houseofcomedy.net/"
_EVENT_URL = "https://www.tixr.com/groups/comicstripbc/events/rell-battle-174083"


def _club() -> Club:
    club = Club(
        id=2001,
        name="House of Comedy British Columbia",
        address="530 Columbia Street, New Westminster, BC V3L 1B1",
        website="https://bc.houseofcomedy.net/",
        popularity=0,
        zip_code="V3L 1B1",
        phone_number="604-522-4500",
        visible=True,
        timezone="America/Vancouver",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="house_of_comedy_bc",
        source_url=_SOURCE_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _homepage_html() -> str:
    return f"""<html><body>
<a class="day-card w-inline-block" href="{_EVENT_URL}" target="_blank">
  <div class="event-name show">Rell Battle</div>
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
  <div class="event-name show">Rell Battle Duplicate</div>
  <div class="date"><p class="b-venue">May 7, 2026</p><p class="b-venue">7:30 pm</p></div>
</a>
</body></html>"""


def test_extractor_parses_bc_webflow_event_cards():
    events = WebflowDayCardExtractor.extract_events(
        _homepage_html(),
        source_url=_SOURCE_URL,
        config=HouseOfComedyBcScraper.config,
    )

    assert len(events) == 1
    assert events[0].title == "Rell Battle"
    assert events[0].date == "2026-05-07"
    assert events[0].time == "7:30 PM"
    assert events[0].room == "East Village"
    assert events[0].ticket_url == _EVENT_URL


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    scraper = HouseOfComedyBcScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _homepage_html()

    monkeypatch.setattr(HouseOfComedyBcScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(_SOURCE_URL)

    assert isinstance(result, WebflowDayCardPageData)
    assert len(result.event_list) == 1


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_event_cards(monkeypatch):
    scraper = HouseOfComedyBcScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return "<html><body>No shows scheduled</body></html>"

    monkeypatch.setattr(HouseOfComedyBcScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(_SOURCE_URL)

    assert result is None


def test_transformation_pipeline_produces_show():
    scraper = HouseOfComedyBcScraper(_club())
    page_data = WebflowDayCardPageData(
        event_list=WebflowDayCardExtractor.extract_events(
            _homepage_html(),
            source_url=_SOURCE_URL,
            config=HouseOfComedyBcScraper.config,
        )
    )

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert isinstance(shows[0], Show)
    assert shows[0].name == "Rell Battle"
    assert shows[0].show_page_url == _EVENT_URL
    assert shows[0].date == datetime(2026, 5, 7, 19, 30, tzinfo=shows[0].date.tzinfo)
