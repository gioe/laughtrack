"""
Pipeline smoke tests for PhillyImprovTheaterScraper and PhillyImprovShow.

Exercises get_data() against mocked Crowdwork API responses matching the
expected crowdwork.com/api/v2/phillyimprovtheater/shows structure, and
unit-tests the PhillyImprovShow.to_show() transformation path.
"""

import pytest

import laughtrack.scrapers.implementations.venues.philly_improv_theater.scraper as _scraper_mod
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.foundation.exceptions import NetworkError
from laughtrack.scrapers.implementations.venues.philly_improv_theater.scraper import PhillyImprovTheaterScraper
from laughtrack.scrapers.implementations.venues.philly_improv_theater.page_data import PhillyImprovPageData


API_URL = "https://crowdwork.com/api/v2/phillyimprovtheater/shows"


def _club() -> Club:
    return Club(
        id=300,
        name="Philly Improv Theater",
        address="62 N 2nd St",
        website="https://www.phillyimprovtheater.com",
        scraping_url=API_URL,
        popularity=0,
        zip_code="19106",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _show_entry(
    name="SPRING PHEST 2026",
    url="https://crowdwork.com/e/spring-phest-2026-friday",
    timezone="America/New_York",
    dates=None,
    cost_formatted="$15",
    spots="",
    description_body="<p>An improv showcase.</p>",
) -> dict:
    return {
        "name": name,
        "url": url,
        "timezone": timezone,
        "dates": dates if dates is not None else ["2026-05-15T19:00:00", "2026-05-16T19:00:00"],
        "next_date": (dates or ["2026-05-15T19:00:00"])[0],
        "cost": {"formatted": cost_formatted},
        "description": {"body": description_body},
        "badges": {"spots": spots},
        "img": {"medium": "", "thumb": "", "large": "", "url": ""},
    }


def _api_response(shows: dict) -> dict:
    """Build a successful Crowdwork API response with shows as a dict."""
    return {"message": "Shows fetched successfully", "status": 200, "type": "success", "data": shows}


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_performances(monkeypatch):
    """get_data() parses the API JSON and returns PhillyImprovPageData."""
    scraper = PhillyImprovTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response({"spring-phest-fri": _show_entry(dates=["2026-05-15T19:00:00"])})

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, PhillyImprovPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].name == "SPRING PHEST 2026"


@pytest.mark.asyncio
async def test_get_data_expands_multi_date_show(monkeypatch):
    """get_data() creates one PhillyImprovShow per date when a show has multiple dates."""
    scraper = PhillyImprovTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response(
            {
                "spring-phest": _show_entry(
                    dates=["2026-05-15T19:00:00", "2026-05-16T19:00:00"]
                )
            }
        )

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, PhillyImprovPageData)
    assert len(result.event_list) == 2
    assert all(e.name == "SPRING PHEST 2026" for e in result.event_list)


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_data(monkeypatch):
    """get_data() returns None when the API returns no shows (empty list)."""
    scraper = PhillyImprovTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {"message": "Shows fetched successfully", "status": 200, "type": "success", "data": []}

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_response(monkeypatch):
    """get_data() returns None when fetch_json returns falsy."""
    scraper = PhillyImprovTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {}

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_handles_sold_out_show(monkeypatch):
    """get_data() marks performances as sold_out when badges.spots contains 'sold'."""
    scraper = PhillyImprovTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response(
            {"spring-phest": _show_entry(spots="Sold Out", dates=["2026-05-15T19:00:00"])}
        )

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert result.event_list[0].sold_out is True


@pytest.mark.asyncio
async def test_get_data_falls_back_to_next_date_when_dates_absent(monkeypatch):
    """get_data() uses next_date when the dates array is absent."""
    scraper = PhillyImprovTheaterScraper(_club())

    entry = _show_entry(dates=[])
    entry["next_date"] = "2026-05-15T19:00:00"

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return _api_response({"spring-phest": entry})

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is not None
    assert len(result.event_list) == 1
    assert result.event_list[0].date_str == "2026-05-15T19:00:00"


@pytest.mark.asyncio
async def test_get_data_handles_list_data_format(monkeypatch):
    """get_data() handles data as a list (forward-compat) as well as a dict."""
    scraper = PhillyImprovTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {
            "status": 200,
            "data": [_show_entry(dates=["2026-05-15T19:00:00"])],
        }

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert isinstance(result, PhillyImprovPageData)
    assert len(result.event_list) == 1


@pytest.mark.asyncio
async def test_get_data_returns_none_on_error_response(monkeypatch):
    """get_data() returns None when the API returns a non-success status or type."""
    scraper = PhillyImprovTheaterScraper(_club())

    async def fake_fetch_json(self, url: str, **kwargs) -> dict:
        return {"status": 404, "type": "error", "data": None}

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(API_URL)
    assert result is None


# ---------------------------------------------------------------------------
# PhillyImprovShow.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_show(
    name="SPRING PHEST 2026",
    date_str="2026-05-15T19:00:00",
    timezone="America/New_York",
    url="https://crowdwork.com/e/spring-phest-2026-friday",
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
    show = _make_show(name="SPRING PHEST 2026", date_str="2026-05-15T19:00:00")
    result = show.to_show(_club())

    assert result is not None
    assert result.name == "SPRING PHEST 2026"
    assert result.date.year == 2026
    assert result.date.month == 5
    assert result.date.day == 15


def test_to_show_creates_ticket_with_price():
    """to_show() creates a ticket with the parsed price."""
    show = _make_show(cost_formatted="$20")
    result = show.to_show(_club())

    assert result is not None
    assert len(result.tickets) == 1
    assert result.tickets[0].price == 20.0


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


def test_to_show_price_range_takes_lower_bound():
    """to_show() extracts the lower bound from a '$10 – $20' cost string."""
    show = _make_show(cost_formatted="$10 – $20")
    result = show.to_show(_club())

    assert result is not None
    assert result.tickets[0].price == 10.0


# ---------------------------------------------------------------------------
# Retry logic tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_retries_on_transient_5xx_then_succeeds(monkeypatch):
    """
    get_data() retries the Crowdwork API fetch on a 5xx NetworkError and
    returns PhillyImprovPageData when the retry succeeds.
    """
    scraper = PhillyImprovTheaterScraper(_club())
    call_count = {"n": 0}

    async def fake_fetch_flaky(self, url: str, **kwargs) -> dict:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise NetworkError("Server error (HTTP 503)", status_code=503)
        return _api_response({"spring-phest": _show_entry(dates=["2026-05-15T19:00:00"])})

    async def _noop_sleep(_delay):
        pass

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_flaky)
    monkeypatch.setattr(_scraper_mod.asyncio, "sleep", _noop_sleep)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, PhillyImprovPageData), "get_data() should succeed after a transient 5xx retry"
    assert len(result.event_list) > 0
    assert call_count["n"] == 2, f"Expected 2 fetch attempts, got {call_count['n']}"


@pytest.mark.asyncio
async def test_get_data_returns_none_after_all_retries_exhausted(monkeypatch):
    """get_data() returns None after all retry attempts fail with 5xx."""
    scraper = PhillyImprovTheaterScraper(_club())
    call_count = {"n": 0}

    async def fake_fetch_always_500(self, url: str, **kwargs) -> dict:
        call_count["n"] += 1
        raise NetworkError("Server error (HTTP 500)", status_code=500)

    async def _noop_sleep(_delay):
        pass

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_always_500)
    monkeypatch.setattr(_scraper_mod.asyncio, "sleep", _noop_sleep)

    result = await scraper.get_data(API_URL)

    assert result is None
    assert call_count["n"] == scraper._RETRY_ATTEMPTS + 1, (
        f"Expected {scraper._RETRY_ATTEMPTS + 1} total attempts, got {call_count['n']}"
    )


@pytest.mark.asyncio
async def test_get_data_does_not_retry_on_4xx(monkeypatch):
    """get_data() returns None immediately without retrying on 4xx NetworkError."""
    scraper = PhillyImprovTheaterScraper(_club())
    call_count = {"n": 0}
    sleep_called = {"n": 0}

    async def fake_fetch_404(self, url: str, **kwargs) -> dict:
        call_count["n"] += 1
        raise NetworkError("Client error (HTTP 404)", status_code=404)

    async def _track_sleep(_delay):
        sleep_called["n"] += 1

    monkeypatch.setattr(PhillyImprovTheaterScraper, "fetch_json", fake_fetch_404)
    monkeypatch.setattr(_scraper_mod.asyncio, "sleep", _track_sleep)

    result = await scraper.get_data(API_URL)

    assert result is None
    assert call_count["n"] == 1, f"Expected 1 attempt (no retry on 4xx), got {call_count['n']}"
    assert sleep_called["n"] == 0, "Should not sleep on 4xx NetworkError"
