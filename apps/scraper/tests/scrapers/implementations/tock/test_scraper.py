"""Tests for the Tock rendered-state scraper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.tock.extractor import extract_tock_events
from laughtrack.scrapers.implementations.tock.scraper import TockScraper

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def club() -> Club:
    _c = Club(
        id=999,
        name="My Buddy's",
        address="4416 N Clark St",
        website="https://www.mybuddyschicago.com/",
        popularity=0,
        zip_code="60640",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        city="Chicago",
        state="IL",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="custom",
        scraper_key="tock",
        source_url="https://www.exploretock.com/mybuddys",
        external_id=None,
        metadata={"comedy_filter": True},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _state_html(experiences: list[dict]) -> str:
    payload = json.dumps(
        {
            "calendar": {
                "offerings": {
                    "experience": experiences,
                },
                "experienceDetail": {"offering": None},
            },
            "navigation": {
                "title": "",
                "onClose": None,
            },
        }
    )
    payload = (
        payload.replace(": null", ":undefined", 1)
        .replace('"onClose": null', '"onClose":function noop() {\\n      // No operation performed.\\n    }')
    )
    return f"<html><script>window.$REDUX_STATE = {payload}</script></html>"


def _experience(
    *,
    event_id: int,
    name: str,
    date: str,
    start_time: str,
    price_cents: int,
    slug: str | None = None,
    description: str = "",
    state: str = "AVAILABLE",
) -> dict:
    return {
        "id": event_id,
        "type": "GA_EVENT",
        "state": state,
        "name": name,
        "slug": slug or name.lower().replace(" ", "-"),
        "description": description,
        "eventDetails": {
            "date": date,
            "startTime": start_time,
            "endTime": "23:00",
            "priceCents": price_cents,
            "location": {
                "name": "My Buddy's",
                "address": "4416 North Clark Street",
                "city": "Chicago",
                "state": "IL",
                "country": "US",
                "zipCode": "60640",
            },
        },
    }


def test_extract_tock_events_decodes_redux_state_and_filters_comedy(club):
    html = _state_html(
        [
            _experience(
                event_id=611697,
                name="Wed Nite Comedy Showdown!",
                date="2026-06-24",
                start_time="21:00",
                price_cents=1000,
                slug="wed-nite-comedy-showdown",
                description="A weekly comedy contest.",
            ),
            _experience(
                event_id=607795,
                name="Drag Bingo hosted by Synthetic",
                date="2026-06-25",
                start_time="18:30",
                price_cents=1000,
            ),
        ]
    )

    events = extract_tock_events(
        html,
        source_url="https://www.exploretock.com/mybuddys",
        timezone=club.timezone,
        comedy_filter=True,
    )

    assert len(events) == 1
    event = events[0]
    assert event.name == "Wed Nite Comedy Showdown!"
    assert event.start_date.isoformat() == "2026-06-24T21:00:00-05:00"
    assert event.url == "https://www.exploretock.com/mybuddys/event/611697/wed-nite-comedy-showdown"
    assert event.location.name == "My Buddy's"
    assert event.offers[0].price == "10.00"
    assert event.offers[0].availability == "InStock"


def test_extract_tock_events_rejects_unpaired_recurring_prix_fixe_fixture():
    html = (FIXTURES / "batsu_chicago_recurring.html").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="recurring|PRIX_FIXE"):
        extract_tock_events(html, source_url="https://www.exploretock.com/batsu-chicago", timezone="America/Chicago")


@pytest.mark.asyncio
async def test_scraper_full_pipeline_produces_comedy_shows(monkeypatch, club):
    scraper = TockScraper(club)
    html = _state_html(
        [
            _experience(
                event_id=527735,
                name="Take A Shot Open Mic Comedy FINALS!!",
                date="2026-06-28",
                start_time="21:00",
                price_cents=1000,
                slug="take-a-shot-open-mic-comedy-finals",
            ),
            _experience(
                event_id=612700,
                name="Trivia Wednesday at My Buddy's!!!",
                date="2026-12-30",
                start_time="19:00",
                price_cents=0,
            ),
        ]
    )

    async def fake_js_fetch(url):
        assert url == "https://www.exploretock.com/mybuddys"
        return html

    monkeypatch.setattr(scraper, "fetch_html", fake_js_fetch)

    shows = await scraper.scrape_async()

    assert len(shows) == 1
    assert shows[0].name == "Take A Shot Open Mic Comedy FINALS!!"
    assert shows[0].club_id == club.id
    assert shows[0].show_page_url == "https://www.exploretock.com/mybuddys/event/527735/take-a-shot-open-mic-comedy-finals"
    assert shows[0].tickets[0].price == 10.0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    ["cloudflare", "none", "transport", "missing_redux", "malformed_state", "valid_ga", "empty_experiences", "partial_malformed_ga"],
)
async def test_blocked_recurring_inventory_recovery(monkeypatch, club, case):
    from laughtrack.core.models.results import ClubScrapingResult
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics, bind_diagnostics, reset_diagnostics,
    )
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    valid = _experience(event_id=611697, name="Comedy Show", date="2099-06-24", start_time="21:00", price_cents=1000)
    malformed = _experience(event_id=611698, name="Another Comedy Show", date="2099-06-25", start_time="21:00", price_cents=1000)
    del malformed["eventDetails"]["date"]
    responses = {
        "cloudflare": "<html><title>Just a moment...</title><div>Checking your browser</div><script src='/cdn-cgi/challenge-platform/abc'></script></html>",
        "none": None,
        "missing_redux": "<html><body>Loading calendar</body></html>",
        "malformed_state": "<html><script>window.$REDUX_STATE = {invalid</script></html>",
        "valid_ga": _state_html([valid]),
        "empty_experiences": _state_html([]),
        "partial_malformed_ga": _state_html([valid, malformed]),
    }
    scraper = TockScraper(club)
    calls = []

    async def fetch(url):
        calls.append(url)
        if case == "transport":
            raise RuntimeError("browser transport failed")
        return responses[case]

    async def no_rate_limit(url):
        return None

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", no_rate_limit)
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        results = await scraper._fetch_all_raw_data([club.scraping_url])
    finally:
        reset_diagnostics(token)

    assert len(calls) == 1  # An unverified calendar must not retry the entire browser fetch.
    raw = results[0][0]
    successful = case == "valid_ga"
    assert diagnostics.fetches_failed == (0 if successful else 1)
    assert diagnostics.fetches_ok == (1 if successful else 0)
    shows = scraper.transform_data(raw, club.scraping_url) if raw is not None else []
    if successful:
        assert len(shows) == 1
    else:
        assert raw is None
        assert diagnostics.scrape_errors
    result = ClubScrapingResult(
        club_name=club.name, shows=shows, execution_time=0,
        fetches_ok=diagnostics.fetches_ok, fetches_failed=diagnostics.fetches_failed,
        items_before_filter=diagnostics.items_before_filter,
        bot_block_detected=diagnostics.bot_block_detected,
    )
    assert ScrapingResultProcessor._is_clean_for_reconciliation(result) is successful


def test_ga_missing_price_remains_unknown(club):
    experience = _experience(event_id=611697, name="Comedy Show", date="2099-06-24", start_time="21:00", price_cents=1000)
    del experience["eventDetails"]["priceCents"]
    events = extract_tock_events(_state_html([experience]), source_url=club.scraping_url, timezone=club.timezone)
    assert len(events) == 1
    assert events[0].offers[0].price == ""


@pytest.mark.parametrize("arguments", ["", "..._"])
def test_redux_navigation_noop_function_arguments(club, arguments):
    experience = _experience(
        event_id=611697,
        name="Comedy Show",
        date="2099-06-24",
        start_time="21:00",
        price_cents=1000,
    )
    html = _state_html([experience]).replace("function noop()", f"function noop({arguments})")
    events = extract_tock_events(html, source_url=club.scraping_url, timezone=club.timezone)
    assert len(events) == 1
    assert events[0].name == "Comedy Show"


@pytest.mark.asyncio
async def test_mixed_recurring_inventory_keeps_only_dated_ga_and_blocks_reconciliation(monkeypatch, club):
    from laughtrack.foundation.infrastructure.http.diagnostics import ScrapeDiagnostics, bind_diagnostics, reset_diagnostics
    from laughtrack.core.models.results import ClubScrapingResult
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    ga = _experience(event_id=611697, name="Comedy Show", date="2050-06-24", start_time="21:00", price_cents=1000)
    recurring = {"id": 1, "name": "Comedy Reservation", "type": "PRIX_FIXE", "state": "AVAILABLE", "eventDetails": {}}
    html = _state_html([ga, recurring]).replace('"experience":', '"openDate": ["2050-06-24", "2050-06-25"], "openTime": ["19:00", "22:00"], "experience":')
    scraper = TockScraper(club)
    async def fetch(url):
        return html
    async def no_rate_limit(url):
        return None
    monkeypatch.setattr(scraper, "fetch_html", fetch)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", no_rate_limit)
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        result = await scraper._fetch_all_raw_data([club.scraping_url])
    finally:
        reset_diagnostics(token)
    raw = result[0][0]
    assert raw is not None
    shows = scraper.transform_data(raw, club.scraping_url)
    assert [show.name for show in shows] == ["Comedy Show"]
    assert diagnostics.fetches_failed > 0
    outcome = ClubScrapingResult(club_name=club.name, shows=shows, execution_time=0, fetches_failed=diagnostics.fetches_failed, fetches_ok=diagnostics.fetches_ok)
    assert not ScrapingResultProcessor._is_clean_for_reconciliation(outcome)


def test_explicit_ga_schedule_dates_use_only_their_experience_slots(club):
    first = _experience(event_id=611697, name="Comedy One", date="2050-06-24", start_time="19:00", price_cents=1000)
    first["eventDetails"].update({"schedule": [{"date": [{"date": "2000-06-24"}, {"date": "2050-06-24"}, {"date": "2050-06-25"}]}], "slots": [{"startTime": "19:00"}, {"startTime": "21:00"}]})
    second = _experience(event_id=611698, name="Comedy Two", date="2050-06-26", start_time="18:00", price_cents=1000)
    second["eventDetails"].update({"schedule": [{"date": [{"date": "2050-06-26"}]}], "slots": [{"startTime": "18:00"}]})
    events = extract_tock_events(_state_html([first, second]), source_url=club.scraping_url, timezone=club.timezone)
    assert sorted((event.name, event.start_date.isoformat()) for event in events) == [
        ("Comedy One", "2050-06-24T19:00:00-05:00"),
        ("Comedy One", "2050-06-24T21:00:00-05:00"),
        ("Comedy One", "2050-06-25T19:00:00-05:00"),
        ("Comedy One", "2050-06-25T21:00:00-05:00"),
        ("Comedy Two", "2050-06-26T18:00:00-05:00"),
    ]


@pytest.mark.parametrize("venue,count", [("buddys", 2), ("chicago", 0), ("nyc", 3)])
def test_observed_september_calendars(venue, count):
    import time_machine
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics, bind_diagnostics, reset_diagnostics,
    )

    html = (FIXTURES / f"{venue}_20260926.html").read_text()
    slug = {"buddys": "mybuddys", "chicago": "batsu-chicago", "nyc": "batsunyc"}[venue]
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        with time_machine.travel("2026-09-26T16:00:00Z", tick=False):
            if venue == "chicago":
                with pytest.raises(ValueError, match="PRIX_FIXE"):
                    extract_tock_events(html, source_url=f"https://www.exploretock.com/{slug}", timezone="America/Chicago")
                return
            events = extract_tock_events(
                html, source_url=f"https://www.exploretock.com/{slug}",
                timezone="America/New_York" if venue == "nyc" else "America/Chicago",
                comedy_filter=venue == "buddys",
            )
    finally:
        reset_diagnostics(token)
    assert len(events) == count
    assert all("/event/" in event.url for event in events)
    if venue == "nyc":
        assert diagnostics.fetches_failed == 1
        assert [event.start_date.isoformat() for event in events] == [
            "2026-09-28T19:00:00-04:00", "2026-10-19T19:00:00-04:00", "2026-11-23T19:00:00-05:00",
        ]
        assert all("NOT BATSU! Stand Up" in event.name for event in events)
    else:
        assert diagnostics.fetches_failed == 0
        assert {event.name for event in events} == {
            "Stand up, Strip Down!!! September Edition!!", "Wed Nite Comedy Showdown!",
        }
