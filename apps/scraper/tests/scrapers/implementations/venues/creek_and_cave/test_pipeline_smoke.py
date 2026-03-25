"""
Pipeline smoke tests for CreekAndCaveScraper and CreekAndCaveEvent.

Exercises get_data() against mocked S3 monthly JSON responses matching the
actual creekandcaveevents.s3.amazonaws.com structure, and unit-tests the
CreekAndCaveEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.creek_and_cave import CreekAndCaveEvent, _infer_comedian_name
from laughtrack.scrapers.implementations.venues.creek_and_cave.scraper import CreekAndCaveScraper
from laughtrack.scrapers.implementations.venues.creek_and_cave.page_data import CreekAndCavePageData


_S3_URL = "https://creekandcaveevents.s3.amazonaws.com/events/month/2026-04.json"


def _club() -> Club:
    return Club(
        id=999,
        name="The Creek and The Cave",
        address="611 East 7th St",
        website="https://www.creekandcave.com",
        scraping_url="https://www.creekandcave.com/calendar",
        popularity=0,
        zip_code="78701",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _s3_event(
    name="Al Jackson",
    slug="al-jackson",
    shows=None,
) -> dict:
    if shows is None:
        shows = [
            {
                "time": "7:00 pm",
                "listing_url": "https://www.showclix.com/event/al-jacksongtum25a",
                "date": "2026-04-11T00:00:00.000Z",
                "inventory": 198,
            }
        ]
    return {
        "event": {
            "name": name,
            "slug": slug,
            "date": shows[0]["date"] if shows else "2026-04-11T00:00:00.000Z",
            "thumbnail": "https://example.com/thumb.jpg",
            "shows": shows,
        },
        "hours": 19,
        "minutes": 0,
    }


def _monthly_json(events_by_day: dict) -> dict:
    """Wrap events in the S3 monthly structure keyed by day-of-month."""
    return events_by_day


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() parses S3 JSON and returns CreekAndCavePageData with events."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _monthly_json({
            "10": [_s3_event(name="Al Jackson", slug="al-jackson")],
        })

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(_S3_URL)

    assert isinstance(result, CreekAndCavePageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].name == "Al Jackson"
    assert result.event_list[0].slug == "al-jackson"


@pytest.mark.asyncio
async def test_get_data_expands_multi_show_events(monkeypatch):
    """get_data() creates one CreekAndCaveEvent per show slot (7pm and 9pm)."""
    scraper = CreekAndCaveScraper(_club())

    two_show_event = _s3_event(
        name="Beth Stelling",
        slug="beth-stelling",
        shows=[
            {
                "time": "7:00 pm",
                "listing_url": "https://www.showclix.com/event/beth-stellingAAA",
                "date": "2026-05-08T00:00:00.000Z",
                "inventory": 200,
            },
            {
                "time": "9:00 pm",
                "listing_url": "https://www.showclix.com/event/beth-stellingBBB",
                "date": "2026-05-08T02:00:00.000Z",
                "inventory": 200,
            },
        ],
    )

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {"8": [two_show_event]}

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(_S3_URL)

    assert isinstance(result, CreekAndCavePageData)
    assert len(result.event_list) == 2
    urls = {e.listing_url for e in result.event_list}
    assert "https://www.showclix.com/event/beth-stellingAAA" in urls
    assert "https://www.showclix.com/event/beth-stellingBBB" in urls


@pytest.mark.asyncio
async def test_get_data_multiple_days(monkeypatch):
    """get_data() aggregates events across multiple days in one monthly file."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {
            "10": [_s3_event(name="Al Jackson", slug="al-jackson")],
            "11": [_s3_event(name="Al Jackson", slug="al-jackson")],
            "12": [_s3_event(name="Off The Cuff", slug="off-the-cuff")],
        }

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(_S3_URL)

    assert isinstance(result, CreekAndCavePageData)
    assert len(result.event_list) == 3


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_response(monkeypatch):
    """get_data() returns None when fetch_json returns falsy."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {}

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(_S3_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_none_response(monkeypatch):
    """get_data() returns None when fetch_json returns None (future month 404)."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs):
        return None

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(_S3_URL)
    assert result is None


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_generates_monthly_urls():
    """collect_scraping_targets() generates 6 monthly S3 URLs."""
    scraper = CreekAndCaveScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 6
    assert all("creekandcaveevents.s3.amazonaws.com/events/month/" in t for t in targets)
    assert all(t.endswith(".json") for t in targets)


# ---------------------------------------------------------------------------
# CreekAndCaveEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    name="Al Jackson",
    slug="al-jackson",
    date_utc="2026-04-11T00:00:00.000Z",
    time_local="7:00 pm",
    listing_url="https://www.showclix.com/event/al-jacksongtum25a",
    inventory=198,
) -> CreekAndCaveEvent:
    return CreekAndCaveEvent(
        slug=slug,
        name=name,
        date_utc=date_utc,
        time_local=time_local,
        listing_url=listing_url,
        inventory=inventory,
    )


def test_to_show_returns_show_with_correct_name_and_date():
    """to_show() produces a Show with the event name and correct date."""
    event = _make_event(name="Al Jackson", date_utc="2026-04-11T00:00:00.000Z")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Al Jackson"
    # 2026-04-11T00:00:00Z = 2026-04-10 19:00 CDT
    assert show.date.year == 2026
    assert show.date.month == 4
    assert show.date.day == 10
    assert show.date.hour == 19


def test_to_show_extracts_comedian_name_for_headliner():
    """to_show() puts the comedian name in show.lineup for headliner events."""
    event = _make_event(name="Al Jackson")
    show = event.to_show(_club())

    assert show is not None
    assert len(show.lineup) == 1
    assert show.lineup[0].name == "Al Jackson"


def test_to_show_strips_live_suffix_from_lineup():
    """to_show() strips the ' Live' suffix when building the lineup entry."""
    event = _make_event(name="Liza Treyger Live", slug="liza-treyger-live")
    show = event.to_show(_club())

    assert show is not None
    # Name on the show keeps the original event name
    assert show.name == "Liza Treyger Live"
    # Lineup has the comedian name without the suffix
    assert len(show.lineup) == 1
    assert show.lineup[0].name == "Liza Treyger"


def test_to_show_no_lineup_for_recurring_show():
    """to_show() returns an empty lineup for recurring show-title events."""
    event = _make_event(name="Off The Cuff", slug="off-the-cuff")
    show = event.to_show(_club())

    assert show is not None
    assert show.lineup == []


def test_to_show_no_lineup_for_open_mic():
    """to_show() returns an empty lineup for open mic events."""
    event = _make_event(name="Bear Arms: Open Mic", slug="bear-arms-open-mic")
    show = event.to_show(_club())

    assert show is not None
    assert show.lineup == []


def test_to_show_creates_ticket_from_listing_url():
    """to_show() creates a ticket using the Showclix listing_url."""
    event = _make_event(listing_url="https://www.showclix.com/event/al-jacksongtum25a")
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://www.showclix.com/event/al-jacksongtum25a"


def test_to_show_returns_none_on_unparseable_date():
    """to_show() returns None when date_utc cannot be parsed."""
    event = _make_event(date_utc="not-a-date")
    show = event.to_show(_club())

    assert show is None


# ---------------------------------------------------------------------------
# _infer_comedian_name() unit tests
# ---------------------------------------------------------------------------


def test_infer_comedian_name_person_name():
    assert _infer_comedian_name("Al Jackson") == "Al Jackson"


def test_infer_comedian_name_strips_live_suffix():
    assert _infer_comedian_name("Liza Treyger Live") == "Liza Treyger"


def test_infer_comedian_name_strips_live_suffix_uppercase():
    assert _infer_comedian_name("Kate Berlant LIVE") == "Kate Berlant"


def test_infer_comedian_name_returns_none_for_open_mic():
    assert _infer_comedian_name("Bear Arms: Open Mic") is None


def test_infer_comedian_name_returns_none_for_roast_battle():
    assert _infer_comedian_name("Roast Battle: Austin") is None


def test_infer_comedian_name_returns_none_for_themed_show():
    assert _infer_comedian_name("King Of The Creek") is None


def test_infer_comedian_name_returns_none_for_single_word():
    """Single-word events like 'FREAKY' are not treated as comedian names."""
    assert _infer_comedian_name("FREAKY") is None


def test_infer_comedian_name_returns_none_for_too_many_words():
    """Five-word event names are not comedian names."""
    assert _infer_comedian_name("Standupatodos by Hector Sifuentes Espanol") is None
