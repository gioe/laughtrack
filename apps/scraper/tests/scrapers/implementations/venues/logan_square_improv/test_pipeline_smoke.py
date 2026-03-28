"""
Pipeline smoke tests for LoganSquareImprovScraper and LoganSquareImprovPageData.

Exercises get_data() against mocked Crowdwork API responses matching the
expected crowdwork.com/api/v2/lsi/shows structure, and unit-tests the
PhillyImprovShow.to_show() transformation path using Chicago timezone.

LSI's API returns ``data`` as a list of show dicts.  Date strings include a
UTC offset (e.g. ``2026-03-28T20:00:00.000-05:00``).  The ``timezone`` field
uses Rails-style names ("Central Time (US & Canada)") which the scraper
normalises to IANA equivalents before storing.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.scrapers.implementations.venues.logan_square_improv.scraper import LoganSquareImprovScraper
from laughtrack.scrapers.implementations.venues.logan_square_improv.data import LoganSquareImprovPageData


API_URL = "https://crowdwork.com/api/v2/lsi/shows"


def _club() -> Club:
    return Club(
        id=999,
        name="Logan Square Improv",
        address="2825 W Diversey Ave",
        website="https://logansquareimprov.com",
        scraping_url=API_URL,
        popularity=0,
        zip_code="60647",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _show_entry(
    name="The Saturday Show",
    url="https://www.crowdwork.com/e/the-saturday-show",
    timezone="Central Time (US & Canada)",
    dates=None,
    cost_formatted="$6.49 (includes fees)",
    spots="",
    description_body="<p>Long-form improv showcase.</p>",
) -> dict:
    return {
        "id": 11770,
        "name": name,
        "url": url,
        "timezone": timezone,
        "dates": dates if dates is not None else ["2026-03-28T20:00:00.000-05:00"],
        "next_date": dates[0] if dates else None,
        "cost": {"formatted": cost_formatted},
        "description": {"body": description_body},
        "badges": {"spots": spots},
    }


def _api_response(shows: list) -> dict:
    """Build a successful Crowdwork API response with shows as a list."""
    return {"message": "Shows fetched successfully", "status": 200, "type": "success", "data": shows}


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_performances(monkeypatch):
    """get_data() parses the API JSON and returns LoganSquareImprovPageData."""
    scraper = LoganSquareImprovScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_show_entry(dates=["2026-03-28T20:00:00.000-05:00"])])

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, LoganSquareImprovPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].name == "The Saturday Show"


@pytest.mark.asyncio
async def test_get_data_expands_multi_date_show(monkeypatch):
    """get_data() creates one PhillyImprovShow per date when a show has multiple dates."""
    scraper = LoganSquareImprovScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([
            _show_entry(dates=[
                "2026-03-28T20:00:00.000-05:00",
                "2026-04-04T20:00:00.000-05:00",
            ])
        ])

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, LoganSquareImprovPageData)
    assert len(result.event_list) == 2
    assert all(e.name == "The Saturday Show" for e in result.event_list)


@pytest.mark.asyncio
async def test_get_data_normalises_rails_timezone(monkeypatch):
    """get_data() converts 'Central Time (US & Canada)' to 'America/Chicago'."""
    scraper = LoganSquareImprovScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_show_entry(timezone="Central Time (US & Canada)")])

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert result is not None
    assert result.event_list[0].timezone == "America/Chicago"


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_data(monkeypatch):
    """get_data() returns None when the API returns no shows (empty list)."""
    scraper = LoganSquareImprovScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {"message": "Shows fetched successfully", "status": 200, "type": "success", "data": []}

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_response(monkeypatch):
    """get_data() returns None when fetch_json returns an empty dict (no keys)."""
    scraper = LoganSquareImprovScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {}

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_handles_sold_out_show(monkeypatch):
    """get_data() marks performances as sold_out when badges.spots starts with 'Sold Out'."""
    scraper = LoganSquareImprovScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_show_entry(spots="Sold Out")])

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert result.event_list[0].sold_out is True


@pytest.mark.asyncio
async def test_get_data_not_sold_out_when_spots_show_remaining(monkeypatch):
    """get_data() does NOT mark sold_out when badges.spots shows remaining capacity (e.g. 'Only 2 spots left')."""
    scraper = LoganSquareImprovScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_show_entry(spots="Only 2 spots left")])

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert result.event_list[0].sold_out is False


@pytest.mark.asyncio
async def test_get_data_falls_back_to_next_date_when_dates_key_absent(monkeypatch):
    """get_data() uses next_date when the 'dates' key is completely absent from the show dict."""
    scraper = LoganSquareImprovScraper(_club())

    entry = _show_entry()
    del entry["dates"]
    entry["next_date"] = "2026-03-28T20:00:00.000-05:00"

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([entry])

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert len(result.event_list) == 1
    assert result.event_list[0].date_str == "2026-03-28T20:00:00.000-05:00"


@pytest.mark.asyncio
async def test_get_data_passes_unknown_timezone_through(monkeypatch):
    """get_data() passes unrecognised timezone strings through unchanged (no KeyError)."""
    scraper = LoganSquareImprovScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_show_entry(timezone="Bogota Time")])

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert result.event_list[0].timezone == "Bogota Time"


@pytest.mark.asyncio
async def test_get_data_falls_back_to_next_date_when_dates_absent(monkeypatch):
    """get_data() uses next_date when the dates array is empty."""
    scraper = LoganSquareImprovScraper(_club())

    entry = _show_entry(dates=[])
    entry["next_date"] = "2026-03-28T20:00:00.000-05:00"

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([entry])

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert len(result.event_list) == 1
    assert result.event_list[0].date_str == "2026-03-28T20:00:00.000-05:00"


@pytest.mark.asyncio
async def test_get_data_returns_none_on_error_response(monkeypatch):
    """get_data() returns None when the API returns a non-success status or type."""
    scraper = LoganSquareImprovScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {"status": 404, "type": "error", "data": None}

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_handles_dict_data_format(monkeypatch):
    """get_data() handles data as a slug-keyed dict for forward-compatibility."""
    scraper = LoganSquareImprovScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {
            "status": 200,
            "data": {"the-saturday-show": _show_entry(dates=["2026-03-28T20:00:00.000-05:00"])},
        }

    monkeypatch.setattr(LoganSquareImprovScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert isinstance(result, LoganSquareImprovPageData)
    assert len(result.event_list) == 1


# ---------------------------------------------------------------------------
# PhillyImprovShow.to_show() unit tests (Chicago timezone)
# ---------------------------------------------------------------------------


def _make_show(
    name="The Saturday Show",
    date_str="2026-03-28T20:00:00.000-05:00",
    timezone="America/Chicago",
    url="https://www.crowdwork.com/e/the-saturday-show",
    cost_formatted="$6.49 (includes fees)",
    sold_out=False,
) -> PhillyImprovShow:
    return PhillyImprovShow(
        name=name,
        date_str=date_str,
        timezone=timezone,
        url=url,
        cost_formatted=cost_formatted,
        sold_out=sold_out,
    )


def test_to_show_returns_show_with_correct_date_and_name():
    """to_show() produces a Show with the correct date and name."""
    show = _make_show(name="The Saturday Show", date_str="2026-03-28T20:00:00.000-05:00")
    result = show.to_show(_club())

    assert result is not None
    assert result.name == "The Saturday Show"
    assert result.date.year == 2026
    assert result.date.month == 3
    assert result.date.day == 28


def test_to_show_creates_ticket_with_price():
    """to_show() creates a ticket with the parsed price."""
    show = _make_show(cost_formatted="$6.49 (includes fees)")
    result = show.to_show(_club())

    assert result is not None
    assert len(result.tickets) == 1
    assert result.tickets[0].price == 6.49


def test_to_show_free_show_has_zero_price():
    """to_show() creates a ticket with price 0.0 for free shows."""
    show = _make_show(cost_formatted="Free")
    result = show.to_show(_club())

    assert result is not None
    assert result.tickets[0].price == 0.0


def test_to_show_sold_out_ticket():
    """to_show() sets sold_out=True on the ticket when sold_out=True."""
    show = _make_show(sold_out=True)
    result = show.to_show(_club())

    assert result is not None
    assert result.tickets[0].sold_out is True


def test_to_show_returns_none_on_unparseable_date():
    """to_show() returns None when date_str cannot be parsed."""
    show = _make_show(date_str="not-a-date")
    result = show.to_show(_club())

    assert result is None
