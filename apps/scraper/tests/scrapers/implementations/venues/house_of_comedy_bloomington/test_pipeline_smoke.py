"""Smoke tests for House of Comedy Bloomington's direct Tixr fallback scraper."""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.tixr.data import TixrPageData
from laughtrack.scrapers.implementations.venues.house_of_comedy_bloomington.scraper import (
    HouseOfComedyBloomingtonScraper,
)

CALENDAR_URL = "https://moa.houseofcomedy.net/"
EVENT_URL = "https://www.tixr.com/groups/houseofcomedymn/events/taylor-baggott-183801"

_ONE_EVENT_HTML = f"""
<div class="event_card">
  <h3>Taylor Baggott</h3>
  <div>Show Starts: May 7, 2026 7:30 PM</div>
  <div>Door Time: May 7, 2026 6:30 PM</div>
  <a href="{EVENT_URL}" class="button-main white w-inline-block">get tickets</a>
</div>
"""

_COMPACT_EVENT_HTML = """
<div class="cal-info-2 w-dyn-item">
  <a href="https://www.tixr.com/groups/houseofcomedymn/events/the-disableds-comedy-show-183793"
     class="day-card w-inline-block">
    The Disableds Comedy Show Sunday East Village May 10, 2026 7:00 pm BUY TICKETS
  </a>
</div>
"""


def _club(*, tixr_group_id: str | None = None) -> Club:
    metadata: dict[str, object] = {}
    if tixr_group_id is not None:
        metadata["tixr_group_id"] = tixr_group_id

    club = Club(
        id=655,
        name="House of Comedy Bloomington",
        address="",
        website="https://moa.houseofcomedy.net",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="tixr",
        scraper_key="house_of_comedy_bloomington",
        source_url=CALENDAR_URL,
        metadata=metadata,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _api_event(event_id: str, tiers: list[dict]) -> dict:
    """Mirror the live /api/groups/<id>/events event shape.

    Captured via ``apps/scraper/bin/probe-tixr <numeric_id> --full`` against
    a known Tixr group (e.g. ``1613`` for Laugh Factory Covina). The fields
    below are the ones ``TixrClient._create_shows_from_data`` consumes; any
    extras Tixr returns are ignored.
    """
    return {
        "id": event_id,
        "name": f"HOC Bloomington Show {event_id}",
        "formattedISOStartDate": "2026-05-07T19:30:00-05:00",
        "url": f"https://www.tixr.com/groups/houseofcomedymn/events/show-{event_id}",
        "description": "Smoke-test event",
        "group": {"subdomain": "houseofcomedymn"},
        "sales": [{"tiers": tiers}],
    }


@pytest.mark.asyncio
async def test_get_data_builds_tixr_events_from_calendar_html(monkeypatch):
    """The scraper builds events directly from venue-page title/date/ticket blocks."""
    scraper = HouseOfComedyBloomingtonScraper(_club())

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=_ONE_EVENT_HTML))

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 1
    event = result.event_list[0]
    assert event.title == "Taylor Baggott"
    assert event.event_id == "183801"
    assert event.source_url == EVENT_URL
    assert event.show.date.year == 2026
    assert event.show.date.month == 5
    assert event.show.date.day == 7
    assert event.show.date.hour == 19
    assert event.show.date.minute == 30
    assert event.show.tickets[0].purchase_url == EVENT_URL


@pytest.mark.asyncio
async def test_get_data_returns_none_when_calendar_has_no_parseable_events(monkeypatch):
    """The scraper returns None rather than falling back to blocked Tixr event pages."""
    scraper = HouseOfComedyBloomingtonScraper(_club())

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value="<html>No events</html>"))

    assert await scraper.get_data(CALENDAR_URL) is None


@pytest.mark.asyncio
async def test_get_data_builds_events_from_compact_calendar_cards(monkeypatch):
    """The scraper handles compact calendar cards that omit the Show Starts label."""
    scraper = HouseOfComedyBloomingtonScraper(_club())

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=_COMPACT_EVENT_HTML))

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    event = result.event_list[0]
    assert event.title == "The Disableds Comedy Show"
    assert event.event_id == "183793"
    assert event.show.date.month == 5
    assert event.show.date.day == 10
    assert event.show.date.hour == 19


@pytest.mark.asyncio
async def test_listing_card_ticket_price_is_none_not_zero(monkeypatch):
    """TASK-2405: listing page exposes no price, so the placeholder ticket must
    report price=None (unknown) rather than 0 (proven-free)."""
    scraper = HouseOfComedyBloomingtonScraper(_club())

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=_ONE_EVENT_HTML))

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    event = result.event_list[0]
    assert len(event.show.tickets) == 1
    assert event.show.tickets[0].price is None


@pytest.mark.asyncio
async def test_get_data_backfills_tier_prices_from_group_events_api(monkeypatch):
    """TASK-2403: with a numeric tixr_group_id on metadata, the scraper must
    overwrite the placeholder Ticket(price=None) with priced tiers fetched
    from /api/groups/<id>/events.

    The lowest non-zero tier price from sales[].tiers[] must appear on the
    resulting show's ticket list for at least one event.
    """
    scraper = HouseOfComedyBloomingtonScraper(_club(tixr_group_id="99999"))

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=_ONE_EVENT_HTML))

    api_payload = {
        "events": [
            _api_event(
                "183801",
                tiers=[
                    {"name": "General Admission", "price": "32.00", "active": True},
                    {"name": "VIP", "price": "55.00", "active": True},
                ],
            )
        ]
    }

    async def fake_direct_fetch(url, logger_context):
        assert url == "https://www.tixr.com/api/groups/99999/events?page=1"
        return api_payload

    monkeypatch.setattr(
        scraper.tixr_client, "_fetch_group_events_json_direct", fake_direct_fetch
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    event = result.event_list[0]
    assert event.event_id == "183801"
    prices = sorted(t.price for t in event.show.tickets if t.price is not None)
    assert prices, "expected at least one priced tier after backfill"
    assert min(prices) == 32.0
    assert prices == [32.0, 55.0]
    # Placeholder must be replaced wholesale — no leftover price=None ticket.
    assert all(t.price is not None for t in event.show.tickets)


@pytest.mark.asyncio
async def test_get_data_keeps_placeholder_when_api_event_id_does_not_match(monkeypatch):
    """Calendar events with no matching event in the API response must keep
    their price=None placeholder — unknown stays distinct from "proven free"."""
    scraper = HouseOfComedyBloomingtonScraper(_club(tixr_group_id="99999"))

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=_ONE_EVENT_HTML))

    # API returns an unrelated event so the join misses the calendar entry.
    async def fake_direct_fetch(url, logger_context):
        return {
            "events": [
                _api_event(
                    "999999",
                    tiers=[{"name": "GA", "price": "20.00", "active": True}],
                )
            ]
        }

    monkeypatch.setattr(
        scraper.tixr_client, "_fetch_group_events_json_direct", fake_direct_fetch
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    event = result.event_list[0]
    assert event.event_id == "183801"
    assert len(event.show.tickets) == 1
    assert event.show.tickets[0].price is None


@pytest.mark.asyncio
async def test_get_data_skips_backfill_when_tixr_group_id_is_missing(monkeypatch):
    """No tixr_group_id metadata → the scraper must not call fetch_group_events."""
    scraper = HouseOfComedyBloomingtonScraper(_club())  # no tixr_group_id

    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(return_value=_ONE_EVENT_HTML))
    fetch_mock = AsyncMock()
    monkeypatch.setattr(scraper.tixr_client, "fetch_group_events", fetch_mock)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    fetch_mock.assert_not_awaited()
    assert result.event_list[0].show.tickets[0].price is None
