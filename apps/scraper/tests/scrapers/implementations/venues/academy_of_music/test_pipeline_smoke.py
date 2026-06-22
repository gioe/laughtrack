"""Pipeline smoke tests for the Academy of Music (Northampton, MA) scraper.

Covers WP-REST ``aom_event`` parsing (date / price / ticket URL), the skip of
non-standard date formats, and the opt-in comedy_filter that isolates the
venue's A-list stand-up from its mostly-music calendar (TASK-3152).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.academy_of_music.data import (
    AcademyOfMusicPageData,
)
from laughtrack.scrapers.implementations.venues.academy_of_music.extractor import (
    AcademyOfMusicExtractor,
)
from laughtrack.scrapers.implementations.venues.academy_of_music.scraper import (
    AcademyOfMusicScraper,
)

SOURCE_URL = "https://aomtheatre.com/wp-json/wp/v2/aom_event?per_page=100"


def _record(title: str, start_full: str, price_html: str, event_id: int | None = 5000) -> dict:
    buy = f'<a href="/purchase-tickets/?eventId={event_id}">Buy</a>' if event_id else ""
    return {
        "title": {"rendered": title},
        "link": f"https://aomtheatre.com/event/{title.lower().replace(' ', '-')}/",
        "content": {
            "rendered": (
                '<div class="event_info"><div class="event_start_full">'
                f"{start_full}</div></div>"
                '<div class="ticket_purchase_box"><div class="ticket_price">'
                f"{price_html}</div></div>{buy}"
            )
        },
    }


_RECORDS = [
    _record("Stand-Up Comedy Showcase", "Friday, October 9th, 2026 at 8:00pm", "$49.42- $71.43 After Fees", 5125),
    _record("Jazz Tribute Band", "Saturday, October 10th, 2026 at 7:30pm", "$30 After Fees", 5200),
    _record("Free Comedy Open Mic", "Wednesday, November 18th, 2026 at 7:00pm", "This is a FREE EVENT", None),
    _record("Multi Date Special", "11/14 7:30 and 11/20 7:30pm", "$25 After Fees", 5300),
]


def _club(comedy_filter: bool = False) -> Club:
    _c = Club(id=777, name="Academy of Music", address='274 Main Street', website='http://aomtheatre.com/', popularity=0, zip_code='01060', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(
        id=1, club_id=_c.id, platform='custom', scraper_key='academy_of_music',
        source_url=SOURCE_URL, metadata=({"comedy_filter": True} if comedy_filter else {}),
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_extractor_parses_date_price_and_ticket_url():
    events = AcademyOfMusicExtractor.extract_events(_RECORDS)
    # The multi-date special has a non-standard date string → skipped.
    assert len(events) == 3
    showcase = next(e for e in events if e.title == "Stand-Up Comedy Showcase")
    assert showcase.date.year == 2026 and showcase.date.month == 10 and showcase.date.day == 9
    assert showcase.date.hour == 20
    assert showcase.price == 49.42
    assert showcase.ticket_url == "https://aomtheatre.com/purchase-tickets/?eventId=5125"
    free = next(e for e in events if e.title == "Free Comedy Open Mic")
    assert free.price == 0.0
    assert free.ticket_url == ""  # no buy link → falls back to show_page_url in to_show


@pytest.mark.asyncio
async def test_get_data_without_filter_keeps_all_events():
    scraper = AcademyOfMusicScraper(_club(comedy_filter=False))
    assert scraper._comedy_filter is False
    scraper.fetch_json = AsyncMock(return_value=_RECORDS)

    result = await scraper.get_data(SOURCE_URL)

    assert isinstance(result, AcademyOfMusicPageData)
    assert {e.title for e in result.event_list} == {
        "Stand-Up Comedy Showcase",
        "Jazz Tribute Band",
        "Free Comedy Open Mic",
    }


@pytest.mark.asyncio
async def test_get_data_with_filter_drops_non_comedy():
    scraper = AcademyOfMusicScraper(_club(comedy_filter=True))
    # Stub the DB-backed known-comedian fallback so the test stays DB-free; the
    # keyword pass alone keeps the two comedy titles and drops the jazz show.
    scraper._lineup_handler = MagicMock()
    scraper._lineup_handler.get_comedians_from_show_names.return_value = {}
    scraper.fetch_json = AsyncMock(return_value=_RECORDS)

    result = await scraper.get_data(SOURCE_URL)

    assert isinstance(result, AcademyOfMusicPageData)
    titles = sorted(e.title for e in result.event_list)
    assert titles == ["Free Comedy Open Mic", "Stand-Up Comedy Showcase"]


def test_event_to_show_builds_show_with_ticket():
    events = AcademyOfMusicExtractor.extract_events(_RECORDS)
    showcase = next(e for e in events if e.title == "Stand-Up Comedy Showcase")
    show = showcase.to_show(_club())
    assert show is not None
    assert show.name == "Stand-Up Comedy Showcase"
    assert show.show_page_url.startswith("https://aomtheatre.com/event/")
    assert len(show.tickets) == 1
