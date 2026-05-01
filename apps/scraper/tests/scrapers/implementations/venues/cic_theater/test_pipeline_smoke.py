"""
Smoke tests for CIC Theater's custom recurring-schedule scraper.

CIC's Eventbrite organizer is stale/empty. The current public schedule lives on
the Squarespace-rendered Browse All Shows page as recurring weekly copy, not as
dated Eventbrite or Squarespace API events.
"""

from datetime import date

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.cic_theater import CicTheaterEvent
from laughtrack.scrapers.implementations.venues.cic_theater.data import (
    CicTheaterPageData,
)
from laughtrack.scrapers.implementations.venues.cic_theater.extractor import (
    CicTheaterExtractor,
)
from laughtrack.scrapers.implementations.venues.cic_theater.scraper import (
    CicTheaterScraper,
)


_SOURCE_URL = "https://www.cictheater.com/browse-shows"
_SAMPLE_HTML = """
<html>
  <body>
    <h1>Browse All Shows</h1>
    <p>Shows are currently at Finley Dunnes Tavern at 3458 N Lincoln Ave on Wednesdays and Thursdays at 8pm.</p>
    <h2>BYOT</h2>
    <p>Wednesdays, 8pm Bring Your Own Team! Got an improv team? Want to play? Come play!</p>
    <h2>Open Stage hosted by Da 3 Jokers</h2>
    <p>Thursdays, 8pm Open Stage hosted by Da 3 Jokers. Free for everybody.</p>
  </body>
</html>
"""


def _club() -> Club:
    _c = Club(
        id=190,
        name="CIC Theater",
        address="1422 W Irving Park Rd",
        website="https://www.cictheater.com",
        popularity=0,
        zip_code="60613",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="custom",
        scraper_key="cic_theater",
        source_url=_SOURCE_URL,
        external_id=None,
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_collect_scraping_targets_returns_browse_shows_url():
    scraper = CicTheaterScraper(_club())

    assert scraper.collect_scraping_targets_sync() == [_SOURCE_URL]


def test_extractor_generates_wednesday_and_thursday_instances():
    events = CicTheaterExtractor.extract_events(
        _SAMPLE_HTML,
        source_url=_SOURCE_URL,
        today=date(2026, 5, 1),
        weeks=2,
    )

    assert [(event.title, event.date, event.time) for event in events] == [
        ("BYOT", "2026-05-06", "8:00 PM"),
        ("Open Stage hosted by Da 3 Jokers", "2026-05-07", "8:00 PM"),
        ("BYOT", "2026-05-13", "8:00 PM"),
        ("Open Stage hosted by Da 3 Jokers", "2026-05-14", "8:00 PM"),
    ]


def test_extractor_returns_empty_when_schedule_copy_is_missing():
    events = CicTheaterExtractor.extract_events(
        "<html><body><p>No current public schedule.</p></body></html>",
        source_url=_SOURCE_URL,
        today=date(2026, 5, 1),
    )

    assert events == []


@pytest.mark.asyncio
async def test_get_data_fetches_source_page_and_returns_page_data(monkeypatch):
    scraper = CicTheaterScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        assert url == _SOURCE_URL
        return _SAMPLE_HTML

    monkeypatch.setattr(CicTheaterScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(CicTheaterScraper, "_today", staticmethod(lambda: date(2026, 5, 1)))

    result = await scraper.get_data(_SOURCE_URL)

    assert isinstance(result, CicTheaterPageData)
    assert len(result.event_list) >= 2


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_schedule_found(monkeypatch):
    scraper = CicTheaterScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body><p>No current public schedule.</p></body></html>"

    monkeypatch.setattr(CicTheaterScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(_SOURCE_URL)

    assert result is None


def test_to_show_sets_title_date_room_and_ticket_url():
    event = CicTheaterEvent(
        title="BYOT",
        date="2026-05-06",
        time="8:00 PM",
        source_url=_SOURCE_URL,
        venue_note="Finley Dunnes Tavern 3458 N Lincoln Ave",
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "BYOT"
    assert show.date.year == 2026
    assert show.date.month == 5
    assert show.date.day == 6
    assert show.date.hour == 20
    assert show.room == "Finley Dunnes Tavern"
    assert show.show_page_url == _SOURCE_URL
    assert show.tickets[0].purchase_url == _SOURCE_URL


def test_to_show_sets_western_room_when_source_page_lists_western():
    event = CicTheaterEvent(
        title="BYOT",
        date="2026-05-06",
        time="8:00 PM",
        source_url=_SOURCE_URL,
        venue_note="The Western Bar & Kitchen 4301 N Western Ave",
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.room == "The Western Bar & Kitchen"


def test_to_show_returns_none_for_invalid_date():
    event = CicTheaterEvent(
        title="BYOT",
        date="not-a-date",
        time="8:00 PM",
        source_url=_SOURCE_URL,
        venue_note="Finley Dunnes Tavern 3458 N Lincoln Ave",
    )

    assert event.to_show(_club()) is None
