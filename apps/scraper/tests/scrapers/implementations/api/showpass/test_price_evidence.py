"""Exact Showpass source identity, currency/fee semantics and bounded fetching."""

import asyncio
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import time_machine

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.showpass import ShowpassEvent
from laughtrack.scrapers.implementations.api.showpass import scraper as scraper_mod
from laughtrack.scrapers.implementations.api.showpass.pricing import extract_offers
from laughtrack.scrapers.implementations.api.showpass.scraper import ShowpassScraper

AUDIT = Path(__file__).resolve().parents[5] / "docs/audits/2026-09-27-price-extraction/ticketing"
DETAIL = json.loads((AUDIT / "showpass-event-api.html").read_text())
NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)
CALENDAR = "https://www.showpass.com/api/public/venues/comedy-cave/calendar/"


def event(data=None):
    return ShowpassEvent.from_api_response(data or DETAIL)


def club():
    c = Club(
        id=818,
        name="Comedy Cave",
        address="",
        website="https://comedycave.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/Edmonton",
    )
    c.active_scraping_source = ScrapingSource(id=1, platform="showpass", scraper_key="showpass", source_url=CALENDAR)
    return c


def ticket(data):
    e = event()
    e.offers = extract_offers(data, e, NOW)
    return e.to_show(club()).tickets[0]


def usd():
    d = deepcopy(DETAIL)
    d["currency"] = "USD"
    return d


def test_retained_cad_base_and_fee_quotes_never_become_usd_price():
    offers = extract_offers(DETAIL, event(), NOW)
    assert len(offers) == 2
    ga = offers[0]
    assert ga.amount == 15 and ga.currency == "CAD" and ga.available
    assert str(ga.fee_quotes["2"]["total_price_no_tax"]) == "17.11"
    assert str(ga.fee_quotes["2"]["total_price"]) == "17.97"
    assert ga.source["sale_ends_on"] == "2026-09-29T03:30:00Z"
    assert ga.source["purchase_limit"] == 8
    result = ga.to_ticket("https://www.showpass.com/" + DETAIL["slug"] + "/")
    assert result.price is None and not result.sold_out
    assert "CAD 15.00 base" in result.type and "CAD 17.11 before tax" in result.type
    assert "CAD 17.97 including tax" in result.type
    assert not offers[1].individual_admission
    assert offers[1].amount == 22.5 and offers[1].to_ticket(result.purchase_url).price is None


def test_verified_usd_individual_admission_can_use_numeric_base_price():
    result = ticket(usd())
    assert result.price == 15
    assert "USD 15.00 base" in result.type
    assert "17.11 before tax" in result.type


@pytest.mark.parametrize(
    "changes",
    [
        {"id": 999},
        {"starts_on": "2026-09-29T01:00:00Z"},
        {"starts_on": "2026-09-29T00:00:00"},
        {"starts_on": "bad"},
        {"slug": "unrelated"},
        {"ticket_types": {}},
    ],
)
def test_wrong_identity_or_malformed_detail_does_not_enrich(changes):
    d = deepcopy(DETAIL)
    d.update(changes)
    assert extract_offers(d, event(), NOW) == []


def test_equivalent_instant_is_accepted_but_wrong_tier_event_is_rejected():
    d = deepcopy(DETAIL)
    d["starts_on"] = "2026-09-28T18:00:00-06:00"
    assert len(extract_offers(d, event(), NOW)) == 2
    d["ticket_types"][0]["event"] = 999
    assert len(extract_offers(d, event(), NOW)) == 1


@pytest.mark.parametrize("currency", ["CAD", "EUR", None, ""])
def test_non_usd_and_unknown_currency_have_no_numeric_price(currency):
    d = deepcopy(DETAIL)
    d["currency"] = currency
    assert ticket(d).price is None


@pytest.mark.parametrize("price", ["0", "-1", "NaN", "Infinity", "1e100", "", None, True])
def test_invalid_or_placeholder_price_is_not_free(price):
    d = usd()
    d["ticket_types"][0]["price"] = price
    assert ticket(d).price is None


@pytest.mark.parametrize(
    "name,price",
    [
        ("Monday Workshop – BOGO Half-Price", "22.50"),
        ("Tuesday Half off Special", "24.95"),
        ("Dinner & Show Experience for 2", "39.95"),
        ("Dinner & Show Experience for 4", "59.95"),
    ],
)
def test_packages_preserve_full_amount_and_name_without_individual_minimum(name, price):
    d = usd()
    d["ticket_types"][0].update(name=name, price=price)
    result = ticket(d)
    assert result.price is None
    assert name in result.type and f"USD {price} base" in result.type


@pytest.mark.parametrize(
    "field,value",
    [
        ("sale_starts_on", "2026-10-01T00:00:00Z"),
        ("sale_ends_on", "2026-09-26T00:00:00Z"),
        ("sale_ends_on", None),
        ("sale_starts_on", "bad"),
        ("inventory", 0),
        ("inventory_left", 0),
        ("sold_out", True),
        ("sold_out", None),
        ("is_password_protected", True),
        ("voucher_purchases_only", True),
        ("has_payment_plans", True),
        ("purchase_limit", 0),
    ],
)
def test_tier_availability_and_sale_window_guard(field, value):
    d = usd()
    d["ticket_types"][0][field] = value
    result = ticket(d)
    assert result.price is None and "not currently purchasable" in result.type
    if field == "sold_out" and value is True:
        assert result.sold_out


@pytest.mark.parametrize(
    "field,value",
    [
        ("stats", {"is_available": False}),
        ("stats", None),
        ("sold_out", True),
        ("is_published", False),
        ("is_password_protected", True),
        ("is_protected_by_queue", True),
        ("region_is_allowed", False),
        ("inventory_sold_out", True),
        ("public_inventory_sold_out", True),
        ("status", "cancelled"),
    ],
)
def test_event_availability_guard(field, value):
    d = usd()
    d[field] = value
    assert ticket(d).price is None


def test_minimum_purchase_and_source_flags_are_preserved():
    d = usd()
    d["ticket_types"][0]["minimum_purchase_limit"] = 2
    offer = extract_offers(d, event(), NOW)[0]
    assert offer.source["minimum_purchase_limit"] == 2 and offer.source["purchase_limit"] == 8
    assert not offer.individual_admission
    result = offer.to_ticket("https://www.showpass.com/test/")
    assert result.price is None and "minimum purchase 2" in result.type
    d["ticket_types"][0]["minimum_purchase_limit"] = None
    d["ticket_types"][0]["is_bundle"] = True
    assert ticket(d).price is None


def test_fee_options_remain_distinct_instead_of_assuming_option_two():
    d = deepcopy(DETAIL)
    d["ticket_types"][0]["fees_pricing_info"]["psp_web"]["other"] = {
        "total_price_no_tax": "18.00",
        "total_price": "19.00",
    }
    result = ticket(d)
    assert "web option 2:" in result.type and "web option other:" in result.type
    assert "CAD 18.00 before tax" in result.type and "CAD 19.00 including tax" in result.type


@pytest.mark.asyncio
async def test_calendar_pipeline_enriches_without_altering_dates_or_losing_currency():
    scraper = ShowpassScraper(club())

    async def fetch(url, **kwargs):
        if url == CALENDAR:
            return {"results": [DETAIL]}
        assert kwargs == {"skip_js_fallback": True}
        return DETAIL

    scraper.fetch_json = AsyncMock(side_effect=fetch)
    with time_machine.travel(NOW, tick=False):
        data = await scraper.get_data(CALENDAR)
    e = data.event_list[0]
    assert e.starts_on == DETAIL["starts_on"] and len(e.offers) == 2
    assert all(t.price is None for t in e.to_show(club()).tickets)
    assert scraper.fetch_json.await_count == 2


@pytest.mark.asyncio
async def test_detail_deduplication_still_matches_each_calendar_date():
    scraper = ShowpassScraper(club())
    scraper.fetch_json = AsyncMock(return_value=DETAIL)
    events = [event(), event()]
    events[1].starts_on = "2026-10-01T00:00:00Z"
    await scraper._enrich_offers(events)
    scraper.fetch_json.assert_awaited_once_with(
        "https://www.showpass.com/api/public/events/1540189/", skip_js_fallback=True
    )
    assert events[0].offers and not events[1].offers


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, RuntimeError("blocked")])
async def test_failed_optional_fetch_preserves_calendar_show(failure):
    scraper = ShowpassScraper(club())
    scraper.fetch_json = AsyncMock(return_value=None, side_effect=failure)
    e = event()
    await scraper._enrich_offers([e])
    assert e.to_show(club()).tickets[0].price is None and not e.offers


@pytest.mark.asyncio
async def test_bounded_phase_and_concurrency(monkeypatch):
    scraper = ShowpassScraper(club())
    active = peak = 0

    async def fetch(*args, **kwargs):
        nonlocal active, peak
        active += 1
        peak = max(active, peak)
        try:
            await asyncio.sleep(10)
        finally:
            active -= 1

    scraper.fetch_json = fetch
    monkeypatch.setattr(scraper_mod, "_DETAIL_BUDGET", 0.03)
    events = [event() for _ in range(8)]
    for i, e in enumerate(events):
        e.event_id += i
    await asyncio.wait_for(scraper._enrich_offers(events), 1)
    assert peak == 4 and active == 0 and all(not e.offers for e in events)


@pytest.mark.asyncio
async def test_individual_timeout_keeps_successful_details(monkeypatch):
    scraper = ShowpassScraper(club())

    async def fetch(url, **kwargs):
        if "1540189" not in url:
            await asyncio.sleep(10)
        return DETAIL

    scraper.fetch_json = fetch
    monkeypatch.setattr(scraper_mod, "_DETAIL_TIMEOUT", 0.01)
    events = [event(), event()]
    events[1].event_id += 1
    await scraper._enrich_offers(events)
    assert events[0].offers and not events[1].offers
