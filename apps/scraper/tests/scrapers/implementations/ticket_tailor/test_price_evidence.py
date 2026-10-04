"""Recorded-source recovery and false-match regression coverage."""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.ticket_tailor import TicketTailorEvent
from laughtrack.scrapers.implementations.ticket_tailor import scraper as scraper_mod
from laughtrack.scrapers.implementations.ticket_tailor.pricing import extract_offers
from laughtrack.scrapers.implementations.ticket_tailor.scraper import TicketTailorScraper

AUDIT = Path(__file__).resolve().parents[4] / "docs/audits/2026-09-27-price-extraction/ticketing"
WEST = "https://www.tickettailor.com/events/westrivercomedyclub/2363785"


def event(start="2026-10-04T17:00:00", url=WEST, timezone="America/Denver"):
    return TicketTailorEvent("Damon Sumner", datetime.fromisoformat(start), url, "West River", timezone=timezone)


def source(**changes):
    result = {
        "@type": "Event",
        "startDate": "2026-10-04T17:00:00-06:00",
        "offers": [
            {
                "@type": "Offer",
                "name": "General Admission",
                "price": 15,
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock",
                "url": WEST,
            }
        ],
    }
    result.update(changes)
    return result


def html(data):
    return '<script type="application/ld+json">' + json.dumps(data) + "</script>"


def club():
    return Club(
        id=1059,
        name="West River",
        address="",
        website="https://westrivercomedy.com",
        popularity=0,
        zip_code="57701",
        phone_number="",
        visible=True,
        timezone="America/Denver",
    )


@pytest.mark.parametrize("start", ["2026-10-02T19:30:00", "2026-10-03T19:30:00", "2026-10-04T17:00:00"])
def test_retained_three_date_offers_keep_package_amounts(start):
    ev = event(start)
    ev.offers = extract_offers((AUDIT / "ticket_tailor-1059-native-detail.html").read_text(), ev)
    assert [(o.name, o.amount) for o in ev.offers] == [
        ("Tier 1 (Table for 2)", Decimal("50")),
        ("Tier 2 (Table seating)", Decimal("20")),
        ("General Admisson Row Seating", Decimal("15")),
    ]
    tickets = ev.to_show(club()).tickets
    assert [t.price for t in tickets] == [None, None, 15]
    assert "Table for 2" in tickets[0].type and "USD 50" in tickets[0].type
    assert all(not t.sold_out for t in tickets)


def test_continental_custom_host_named_tiers():
    ev = event(
        "2026-11-05T19:00:00",
        "https://events.oaklandcontinentalclub.com/events/continentalclub/2347556",
        "America/Los_Angeles",
    )
    offers = extract_offers((AUDIT / "ticket_tailor-11123-detail.html").read_text(), ev)
    assert [(o.name, o.to_ticket().price) for o in offers] == [
        ("Early Bird", 24.75),
        ("General Admission", 28),
        ("VIP", 38.75),
    ]


def test_each_date_uses_its_own_offer_not_other_dates_on_same_url():
    first = source()
    second = source(startDate="2026-10-05T17:00:00-06:00")
    second["offers"][0]["price"] = 99
    assert extract_offers(html([second, first]), event())[0].amount == 15
    assert extract_offers(html([second, first]), event("2026-10-05T17:00:00"))[0].amount == 99
    assert extract_offers(html([second, first]), event("2026-10-04T18:00:00")) == []


@pytest.mark.parametrize(
    "changes",
    [
        {"startDate": "2026-10-04T17:00:00"},
        {"startDate": "2026-10-04T17:00:00-05:00"},
        {"startDate": None},
        {"startDate": "invalid"},
        {"url": WEST + "0"},
        {"eventStatus": "https://schema.org/EventCancelled"},
        {"offers": "invalid"},
    ],
)
def test_unmatched_or_malformed_event_stays_unknown(changes):
    assert extract_offers(html(source(**changes)), event()) == []


def test_utc_equivalent_in_graph_and_duplicate_definitions():
    obj = source(startDate="2026-10-04T23:00:00Z")
    assert len(extract_offers(html({"@graph": [obj, obj]}), event())) == 1
    conflict = source()
    conflict["offers"][0]["price"] = 99
    assert extract_offers(html([obj, conflict]), event()) == []


@pytest.mark.parametrize("price", [None, "", "free", 0, -1, "NaN", "Infinity", True, 1e100])
def test_invalid_or_zero_price_never_invents_free_admission(price):
    obj = source()
    obj["offers"][0]["price"] = price
    assert extract_offers(html(obj), event())[0].to_ticket().price is None


@pytest.mark.parametrize("currency", ["CAD", None, ""])
def test_no_implicit_currency_conversion(currency):
    obj = source()
    obj["offers"][0]["priceCurrency"] = currency
    offer = extract_offers(html(obj), event())[0]
    assert offer.amount == 15
    assert offer.to_ticket().price is None
    assert str(currency or "currency unspecified") in offer.to_ticket().type


@pytest.mark.parametrize(
    "availability,sold_out", [("SoldOut", True), ("OutOfStock", True), ("PreOrder", False), (None, False)]
)
def test_unavailable_prices_do_not_become_advertised_minimum(availability, sold_out):
    obj = source()
    obj["offers"][0]["availability"] = availability
    ticket = extract_offers(html(obj), event())[0].to_ticket()
    assert ticket.price is None and ticket.sold_out == sold_out
    assert "USD 15" in ticket.type


@pytest.mark.parametrize("name", ["Table for 2", "Group package", "Pair admission", "Table seating"])
def test_package_only_never_becomes_individual_minimum(name):
    obj = source()
    obj["offers"][0].update(name=name, price=5)
    offer = extract_offers(html(obj), event())[0]
    assert offer.amount == 5 and offer.to_ticket().price is None
    assert name in offer.to_ticket().type and "USD 5" in offer.to_ticket().type


def test_extras_and_foreign_urls_are_not_admission_prices():
    for change in [
        {"url": WEST + "0"},
        {"url": WEST.replace("www.tickettailor.com", "other.test")},
        {"name": "Drink add-on"},
    ]:
        obj = source()
        obj["offers"][0].update(change)
        assert extract_offers(html(obj), event()) == []


def test_declared_canonical_alias_requires_same_account_event_path():
    alias = WEST.replace("www.tickettailor.com", "events.westrivercomedy.com")
    obj = source()
    obj["offers"][0]["url"] = alias
    assert extract_offers(html(obj), event()) == []
    assert len(extract_offers(f'<link rel="canonical" href="{alias}">' + html(obj), event())) == 1
    assert extract_offers(f'<link rel="canonical" href="{alias}0">' + html(obj), event()) == []


def test_missing_timezone_and_bad_json_leave_fallback():
    assert extract_offers(html(source()), event(timezone=None)) == []
    ev = event()
    ev.offers = extract_offers('<script type="application/ld+json">invalid</script>', ev)
    assert ev.to_show(club()).tickets[0].price is None


@pytest.mark.asyncio
async def test_deduplicated_detail_enrichment_uses_native_fetcher():
    scraper = TicketTailorScraper(club())
    scraper._fetch_listing = AsyncMock(return_value=(AUDIT / "ticket_tailor-1059-native-detail.html").read_text())
    events = [event("2026-10-02T19:30:00"), event("2026-10-03T19:30:00"), event()]
    await scraper._enrich_offers(events)
    scraper._fetch_listing.assert_awaited_once_with(WEST)
    assert all(len(ev.offers) == 3 for ev in events)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, RuntimeError("blocked")])
async def test_failed_enrichment_retains_listing_show(failure):
    scraper = TicketTailorScraper(club())
    scraper._fetch_listing = AsyncMock(return_value=None, side_effect=failure)
    ev = event()
    await scraper._enrich_offers([ev])
    assert ev.to_show(club()).tickets[0].price is None


@pytest.mark.asyncio
async def test_detail_concurrency_and_phase_budget(monkeypatch):
    scraper = TicketTailorScraper(club())
    active = peak = 0

    async def hanging_fetch(url):
        nonlocal active, peak
        active += 1
        peak = max(active, peak)
        try:
            await asyncio.sleep(10)
        finally:
            active -= 1

    scraper._fetch_listing = hanging_fetch
    monkeypatch.setattr(scraper_mod, "_DETAIL_BUDGET", 0.03)
    events = [event(url=WEST + str(i)) for i in range(8)]
    await asyncio.wait_for(scraper._enrich_offers(events), 1)
    assert peak == 4 and active == 0
    assert all(not ev.offers for ev in events)


@pytest.mark.asyncio
async def test_individual_timeout_preserves_other_prices(monkeypatch):
    scraper = TicketTailorScraper(club())

    async def fetch(url):
        if url != WEST:
            await asyncio.sleep(10)
        return html(source())

    scraper._fetch_listing = fetch
    monkeypatch.setattr(scraper_mod, "_DETAIL_TIMEOUT", 0.01)
    events = [event(), event(url=WEST + "1")]
    await scraper._enrich_offers(events)
    assert events[0].offers[0].amount == 15 and not events[1].offers


@pytest.mark.asyncio
async def test_full_scrape_enriches_after_filter_before_routing(monkeypatch):
    scraper = TicketTailorScraper(club())
    kept, dropped = event(), event(url=WEST + "1")
    monkeypatch.setattr(scraper_mod, "extract_events", lambda _: [kept, dropped])
    monkeypatch.setattr(scraper, "_listing_url", lambda: "https://www.tickettailor.com/events/westrivercomedyclub/")
    monkeypatch.setattr(scraper, "_filter_events", lambda events: [events[0]])
    monkeypatch.setattr(scraper, "_single_venue_mode", lambda: True)
    scraper._fetch_listing = AsyncMock(return_value=html(source()))
    shows = await scraper.scrape_async()
    assert len(shows) == 1 and shows[0].tickets[0].price == 15
    assert scraper._fetch_listing.await_count == 2
    assert not dropped.offers
