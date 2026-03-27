"""
Pipeline smoke tests for IOTheaterScraper and IOTheaterPageData.

Exercises get_data() against mocked Crowdwork API responses matching the
expected crowdwork.com/api/v2/iotheater/shows structure, and unit-tests
the PhillyImprovShow.to_show() transformation path using Chicago timezone.

iO Theater's API returns ``data`` as a list of show dicts (unlike PHIT,
which returns a slug-keyed dict).  Date strings include a UTC offset
(e.g. ``2026-03-21T19:00:00.000-05:00``).  The ``timezone`` field uses
Rails-style names ("Central Time (US & Canada)") which the scraper
normalises to IANA equivalents before storing.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.scrapers.implementations.venues.io_theater.scraper import IOTheaterScraper
from laughtrack.scrapers.implementations.venues.io_theater.data import IOTheaterPageData


API_URL = "https://crowdwork.com/api/v2/iotheater/shows"


def _club() -> Club:
    return Club(
        id=999,
        name="iO Theater",
        address="1501 N Kingsbury St",
        website="https://ioimprov.com",
        scraping_url=API_URL,
        popularity=0,
        zip_code="60642",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def _show_entry(
    name="Harold Night",
    url="https://www.crowdwork.com/e/harold-night",
    timezone="Central Time (US & Canada)",
    dates=None,
    cost_formatted="$15",
    spots="",
    description_body="<p>Long-form improv.</p>",
) -> dict:
    return {
        "id": 12345,
        "name": name,
        "url": url,
        "timezone": timezone,
        "dates": dates if dates is not None else ["2026-04-10T19:00:00.000-05:00"],
        # next_date mirrors the first date when present; None when dates is empty
        # (the scraper falls back to next_date only when dates is absent/empty)
        "next_date": dates[0] if dates else None,
        "cost": {"formatted": cost_formatted},
        "description": {"body": description_body},
        "badges": {"spots": spots},
    }


def _api_response(shows: list) -> dict:
    """Build a successful Crowdwork API response with shows as a list (iO Theater format)."""
    return {"message": "Shows fetched successfully", "status": 200, "type": "success", "data": shows}


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_performances(monkeypatch):
    """get_data() parses the API JSON and returns IOTheaterPageData."""
    scraper = IOTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_show_entry(dates=["2026-04-10T19:00:00.000-05:00"])])

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, IOTheaterPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].name == "Harold Night"


@pytest.mark.asyncio
async def test_get_data_expands_multi_date_show(monkeypatch):
    """get_data() creates one PhillyImprovShow per date when a show has multiple dates."""
    scraper = IOTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([
            _show_entry(dates=[
                "2026-04-10T19:00:00.000-05:00",
                "2026-04-11T19:00:00.000-05:00",
            ])
        ])

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, IOTheaterPageData)
    assert len(result.event_list) == 2
    assert all(e.name == "Harold Night" for e in result.event_list)


@pytest.mark.asyncio
async def test_get_data_normalises_rails_timezone(monkeypatch):
    """get_data() converts 'Central Time (US & Canada)' to 'America/Chicago'."""
    scraper = IOTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_show_entry(timezone="Central Time (US & Canada)")])

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert result is not None
    assert result.event_list[0].timezone == "America/Chicago"


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_data(monkeypatch):
    """get_data() returns None when the API returns no shows (empty list)."""
    scraper = IOTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {"message": "Shows fetched successfully", "status": 200, "type": "success", "data": []}

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_response(monkeypatch):
    """get_data() returns None when fetch_json returns falsy."""
    scraper = IOTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {}

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_handles_sold_out_show(monkeypatch):
    """get_data() marks performances as sold_out when badges.spots contains 'sold'."""
    scraper = IOTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_show_entry(spots="Sold Out")])

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert result.event_list[0].sold_out is True


@pytest.mark.asyncio
async def test_get_data_falls_back_to_next_date_when_dates_absent(monkeypatch):
    """get_data() uses next_date when the dates array is absent."""
    scraper = IOTheaterScraper(_club())

    entry = _show_entry(dates=[])
    entry["next_date"] = "2026-04-10T19:00:00.000-05:00"

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([entry])

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert len(result.event_list) == 1
    assert result.event_list[0].date_str == "2026-04-10T19:00:00.000-05:00"


@pytest.mark.asyncio
async def test_get_data_falls_back_to_next_date_when_dates_key_absent(monkeypatch):
    """get_data() uses next_date when the 'dates' key is completely absent from the show dict."""
    scraper = IOTheaterScraper(_club())

    entry = _show_entry()
    del entry["dates"]
    entry["next_date"] = "2026-04-10T19:00:00.000-05:00"

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([entry])

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert len(result.event_list) == 1
    assert result.event_list[0].date_str == "2026-04-10T19:00:00.000-05:00"


@pytest.mark.asyncio
async def test_get_data_handles_dict_data_format(monkeypatch):
    """get_data() handles data as a slug-keyed dict for forward-compatibility."""
    scraper = IOTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {
            "status": 200,
            "data": {"harold-night": _show_entry(dates=["2026-04-10T19:00:00.000-05:00"])},
        }

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert isinstance(result, IOTheaterPageData)
    assert len(result.event_list) == 1


@pytest.mark.asyncio
async def test_get_data_returns_none_on_error_response(monkeypatch):
    """get_data() returns None when the API returns a non-success status or type."""
    scraper = IOTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {"status": 404, "type": "error", "data": None}

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_passes_unknown_timezone_through(monkeypatch):
    """get_data() passes unrecognised timezone strings through unchanged (no KeyError)."""
    scraper = IOTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response([_show_entry(timezone="Bogota Time")])

    monkeypatch.setattr(IOTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    # Unknown timezone string passes through _RAILS_TO_IANA.get() unchanged
    assert result.event_list[0].timezone == "Bogota Time"


# ---------------------------------------------------------------------------
# PhillyImprovShow.to_show() unit tests (Chicago timezone)
# ---------------------------------------------------------------------------


def _make_show(
    name="Harold Night",
    date_str="2026-04-10T19:00:00.000-05:00",
    timezone="America/Chicago",
    url="https://www.crowdwork.com/e/harold-night",
    cost_formatted="$15",
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
    show = _make_show(name="Harold Night", date_str="2026-04-10T19:00:00.000-05:00")
    result = show.to_show(_club())

    assert result is not None
    assert result.name == "Harold Night"
    assert result.date.year == 2026
    assert result.date.month == 4
    assert result.date.day == 10


def test_to_show_creates_ticket_with_price():
    """to_show() creates a ticket with the parsed price."""
    show = _make_show(cost_formatted="$23.40 (includes fees)")
    result = show.to_show(_club())

    assert result is not None
    assert len(result.tickets) == 1
    assert result.tickets[0].price == 23.40


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
