"""
Pipeline smoke tests for TheRockwellScraper and RockwellEvent.

Exercises get_data() against mocked Tribe Events REST API responses
matching the actual therockwell.org structure, and unit-tests the
RockwellEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.rockwell import RockwellEvent
from laughtrack.scrapers.implementations.venues.the_rockwell.scraper import TheRockwellScraper
from laughtrack.scrapers.implementations.venues.the_rockwell.data import RockwellPageData


API_URL = "https://therockwell.org/wp-json/tribe/events/v1/events"


def _club() -> Club:
    return Club(
        id=200,
        name="The Rockwell",
        address="255 Elm St",
        website="https://therockwell.org",
        scraping_url=API_URL,
        popularity=0,
        zip_code="02144",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _raw_event(
    id_="therockwell.org?id=1001",
    title="Jack Bensinger",
    start_date="2026-04-01 19:00:00",
    timezone="America/New_York",
    url="https://therockwell.org/calendar/jack-bensinger/",
    cost="$15 – $25",
    cost_values=None,
) -> dict:
    return {
        "global_id": id_,
        "title": title,
        "start_date": start_date,
        "timezone": timezone,
        "url": url,
        "cost": cost,
        "cost_details": {"currency_symbol": "$", "values": cost_values or ["15", "25"]},
        "description": "<p>An hour of comedy.</p>",
    }


def _api_response(events: list, total_pages: int = 1) -> dict:
    return {
        "events": events,
        "total": len(events),
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# get_data tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() parses the API JSON and returns RockwellPageData with events."""
    scraper = TheRockwellScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([
            _raw_event(id_="1", title="Valencia Grace"),
            _raw_event(id_="2", title="Jack Bensinger"),
        ])

    monkeypatch.setattr(TheRockwellScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, RockwellPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Valencia Grace" in titles
    assert "Jack Bensinger" in titles


@pytest.mark.asyncio
async def test_get_data_handles_pagination(monkeypatch):
    """get_data() fetches multiple pages when total_pages > 1."""
    scraper = TheRockwellScraper(_club())
    call_count = 0

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        nonlocal call_count
        call_count += 1
        if "page=1" in url:
            return _api_response(
                [_raw_event(id_="1", title="Show A")],
                total_pages=2,
            )
        return _api_response(
            [_raw_event(id_="2", title="Show B")],
            total_pages=2,
        )

    monkeypatch.setattr(TheRockwellScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, RockwellPageData)
    assert len(result.event_list) == 2
    assert call_count == 2
    titles = {e.title for e in result.event_list}
    assert "Show A" in titles
    assert "Show B" in titles


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_events(monkeypatch):
    """get_data() returns None when the API returns no events."""
    scraper = TheRockwellScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([])

    monkeypatch.setattr(TheRockwellScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_response(monkeypatch):
    """get_data() returns None when fetch_json returns an empty dict."""
    scraper = TheRockwellScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {}

    monkeypatch.setattr(TheRockwellScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_preserves_raw_title_including_sold_out(monkeypatch):
    """get_data() stores the raw title as-is; SOLD OUT stripping happens in to_show()."""
    scraper = TheRockwellScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_raw_event(title="SOLD OUT! Clown Class with Deby Xiadani")])

    monkeypatch.setattr(TheRockwellScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert result is not None
    assert result.event_list[0].title == "SOLD OUT! Clown Class with Deby Xiadani"


@pytest.mark.asyncio
async def test_get_data_includes_cost_values(monkeypatch):
    """get_data() preserves cost_values for ticket price extraction."""
    scraper = TheRockwellScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_raw_event(cost="$20 – $30", cost_values=["20", "30"])])

    monkeypatch.setattr(TheRockwellScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert result.event_list[0].cost_values == ["20", "30"]


# ---------------------------------------------------------------------------
# RockwellEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title="Jack Bensinger",
    start_date="2026-04-01 19:00:00",
    timezone="America/New_York",
    url="https://therockwell.org/calendar/jack-bensinger/",
    cost_values=None,
) -> RockwellEvent:
    return RockwellEvent(
        id="therockwell.org?id=1001",
        title=title,
        start_date=start_date,
        timezone=timezone,
        url=url,
        cost="$15 – $25",
        cost_values=cost_values or ["15", "25"],
        description="An hour of comedy.",
    )


def test_to_show_returns_show_with_correct_date_and_name():
    """to_show() produces a Show with the correct date and name."""
    event = _make_event(title="Valencia Grace", start_date="2026-04-05 20:00:00")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Valencia Grace"
    assert show.date.year == 2026
    assert show.date.month == 4
    assert show.date.day == 5


def test_to_show_strips_sold_out_prefix():
    """to_show() strips the 'SOLD OUT!' prefix from the show name."""
    event = _make_event(title="SOLD OUT! Clown Class with Deby Xiadani")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Clown Class with Deby Xiadani"
    assert "SOLD OUT" not in show.name


def test_to_show_creates_ticket_from_cost_values():
    """to_show() creates a ticket using the lowest cost_value as price."""
    event = _make_event(cost_values=["20", "30"])
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 20.0


def test_to_show_returns_none_on_unparseable_date():
    """to_show() returns None when start_date cannot be parsed."""
    event = _make_event(start_date="not-a-date")
    show = event.to_show(_club())

    assert show is None
