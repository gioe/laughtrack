from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "city,business_id,tz,count", [("chicago", 29114, "America/Chicago", 57), ("nyc", 27051, "America/New_York", 75)]
)
def test_verified_reservation_slots(city, business_id, tz, count):
    from laughtrack.scrapers.implementations.tock.availability import extract_reservations

    events = extract_reservations(
        (FIXTURES / f"{city}_public_20261001.html").read_text(),
        (FIXTURES / f"{city}_calendar_20261001.bin").read_bytes(),
        source_url="https://www.exploretock.com/" + ("batsu-chicago" if city == "chicago" else "batsunyc"),
        business_id=business_id,
        timezone=tz,
    )
    assert len(events) == count
    assert len({e.start_date for e in events}) == count
    assert all(e.start_date.tzinfo is not None for e in events)
    assert all("/experience/" in o.url for e in events for o in e.offers)
    assert any(o.availability == "SoldOut" for e in events for o in e.offers)
    assert any(
        e.start_date.month == 11
        and e.start_date.utcoffset().total_seconds() == (-21600 if city == "chicago" else -18000)
        for e in events
    )


def venue(city):
    from laughtrack.core.entities.club.model import Club, ScrapingSource

    chicago = city == "chicago"
    cid = 11073 if chicago else 16048
    c = Club(
        id=cid,
        name="BATSU! Chicago" if chicago else "BATSU!",
        address="",
        popularity=0,
        website="https://batsulive.com/",
        zip_code="60611" if chicago else "10003",
        phone_number="",
        visible=True,
        timezone="America/Chicago" if chicago else "America/New_York",
    )
    c.active_scraping_source = ScrapingSource(
        id=6842 if chicago else 7643,
        club_id=cid,
        platform="custom",
        scraper_key="tock",
        source_url="https://www.exploretock.com/" + ("batsu-chicago" if chicago else "batsunyc"),
    )
    return c


@pytest.mark.asyncio
@pytest.mark.parametrize("city,count", [("chicago", 57), ("nyc", 77)])
async def test_full_pipeline_preserves_ga_and_blocks_cleanup(city, count, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import time_machine
    from laughtrack.scrapers.implementations.tock import scraper as module
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
    )
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    c = venue(city)
    browser = SimpleNamespace(
        fetch_tock_calendar=AsyncMock(
            return_value=(
                (FIXTURES / f"{city}_public_20261001.html").read_text(),
                (FIXTURES / f"{city}_calendar_20261001.bin").read_bytes(),
            )
        )
    )
    monkeypatch.setattr(module, "_get_js_browser", lambda: browser)
    monkeypatch.setattr(module.HttpClient, "resolve_proxy_url", lambda key: None)
    s = module.TockScraper(c)
    s.rate_limiter = SimpleNamespace(await_if_needed=AsyncMock())
    diag = ScrapeDiagnostics()
    token = bind_diagnostics(diag)
    try:
        with time_machine.travel("2026-10-01T16:00:00Z", tick=False):
            shows = await s.scrape_async()
    finally:
        reset_diagnostics(token)
    assert len(shows) == count
    assert not any("PRIX_FIXE" in error for error in diag.scrape_errors)
    assert all(show.lineup == [] for show in shows)
    assert all(show.room in {None, ""} for show in shows)
    assert any(len(show.tickets) == 2 for show in shows)
    assert sum(show.tickets_complete is False for show in shows) == (57 if city == "chicago" else 75)
    assert sum(show.tickets_complete is True for show in shows) == (0 if city == "chicago" else 2)
    assert not ScrapingResultProcessor._is_clean_for_reconciliation(
        SimpleNamespace(
            shows=shows,
            error=None,
            bot_block_detected=diag.bot_block_detected,
            fetches_ok=diag.fetches_ok,
            fetches_failed=diag.fetches_failed,
        )
    )
    browser.fetch_tock_calendar.assert_awaited_once_with(
        c.scraping_url, str(29114 if city == "chicago" else 27051), proxy_url=None
    )


@pytest.mark.parametrize(
    "payload",
    [b"", b"\x00", b"\x0a\xff", b"\x12\x00", b"<html>blocked</html>", b"\x0a\x04\x0a\x02\x08\x01", b"\xff" * 11],
)
def test_malformed_unknown_and_error_envelopes_never_become_empty(payload):
    from laughtrack.scrapers.implementations.tock.availability import decode_calendar

    with pytest.raises(ValueError):
        decode_calendar(payload)


@pytest.mark.parametrize(
    "mutation", ["wrong_date", "wrong_time", "wrong_type", "wrong_price", "counts", "business_day", "tier_price"]
)
def test_inconsistent_dated_evidence_rejected(mutation, monkeypatch):
    from laughtrack.scrapers.implementations.tock import availability as module
    import copy

    payload = (FIXTURES / "chicago_calendar_20261001.bin").read_bytes()
    types, groups = copy.deepcopy(module.decode_calendar(payload))
    if mutation == "wrong_date":
        groups[0]["date"] = "2027-11-07"
    elif mutation == "wrong_time":
        groups[0]["time"] = "22:00"
    elif mutation == "wrong_type":
        groups[0]["prices"] = [(999999, 7000)]
    elif mutation == "wrong_price":
        groups[0]["prices"] = [(351809, 999999999)]
    elif mutation == "counts":
        groups[0]["available"] += 1
    elif mutation == "business_day":
        groups[0]["business_day"] = "2026-11-06"
    elif mutation == "tier_price":
        duplicate = copy.deepcopy(groups[0])
        duplicate["prices"] = [(351809, 7100)]
        groups.append(duplicate)
    monkeypatch.setattr(module, "decode_calendar", lambda payload: (types, groups))
    with pytest.raises(ValueError):
        module.extract_reservations(
            (FIXTURES / "chicago_public_20261001.html").read_text(),
            payload,
            source_url=venue("chicago").scraping_url,
            business_id=29114,
            timezone="America/Chicago",
        )


def test_wrong_business_and_truncated_capture_fail_closed():
    from laughtrack.scrapers.implementations.tock.availability import extract_reservations

    html = (FIXTURES / "chicago_public_20261001.html").read_text()
    payload = (FIXTURES / "chicago_calendar_20261001.bin").read_bytes()
    for altered_html, altered_payload in [(html.replace("29114", "27051"), payload), (html, payload[:-1])]:
        with pytest.raises(ValueError):
            extract_reservations(
                altered_html,
                altered_payload,
                source_url=venue("chicago").scraping_url,
                business_id=29114,
                timezone="America/Chicago",
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("city,expected", [("chicago", 0), ("nyc", 2)])
async def test_missing_reservation_feed_preserves_only_verified_ga(city, expected, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import time_machine
    from laughtrack.scrapers.implementations.tock import scraper as module
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
    )

    browser = SimpleNamespace(fetch_tock_calendar=AsyncMock(side_effect=RuntimeError("unavailable")))
    monkeypatch.setattr(module, "_get_js_browser", lambda: browser)
    monkeypatch.setattr(module.HttpClient, "resolve_proxy_url", lambda key: None)
    s = module.TockScraper(venue(city))
    s.fetch_html = AsyncMock(return_value=(FIXTURES / f"{city}_public_20261001.html").read_text())
    s.rate_limiter = SimpleNamespace(await_if_needed=AsyncMock())
    diag = ScrapeDiagnostics()
    token = bind_diagnostics(diag)
    try:
        with time_machine.travel("2026-10-01T16:00:00Z", tick=False):
            shows = await s.scrape_async()
    finally:
        reset_diagnostics(token)
    assert len(shows) == expected
    assert diag.fetches_failed > 0
    assert all("Laughter Party" in show.name for show in shows)


def test_actual_tiers_prices_and_friday_exception_are_preserved():
    from laughtrack.scrapers.implementations.tock.availability import extract_reservations

    events = extract_reservations(
        (FIXTURES / "chicago_public_20261001.html").read_text(),
        (FIXTURES / "chicago_calendar_20261001.bin").read_bytes(),
        source_url=venue("chicago").scraping_url,
        business_id=29114,
        timezone="America/Chicago",
    )
    friday = next(e for e in events if e.start_date.strftime("%Y-%m-%dT%H:%M") == "2026-10-02T22:00")
    assert {offer.price for offer in friday.offers} == {"40.00", "70.00"}
    assert len(friday.offers) == 2
    assert not any(e.start_date.strftime("%Y-%m-%dT%H:%M") == "2026-10-08T22:00" for e in events)
