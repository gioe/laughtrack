"""Retained Leap checkout evidence and optional Comix enrichment boundaries."""

import asyncio
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import time_machine
from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comix_roadhouse import ComixRoadhouseEvent
from laughtrack.scrapers.implementations.venues.comix_roadhouse import scraper as scraper_mod
from laughtrack.scrapers.implementations.venues.comix_roadhouse.pricing import checkout_url, extract_checkout
from laughtrack.scrapers.implementations.venues.comix_roadhouse.scraper import ComixRoadhouseScraper

AUDIT = Path(__file__).resolve().parents[5] / "docs/audits/2026-09-27-price-extraction/venues"
HTML = [(AUDIT / f"comix-checkout-{i}.html").read_text() for i in range(2)]
DATA = [
    json.loads(BeautifulSoup(h, "html.parser").select_one('script[type="application/ld+json"]').get_text())
    for h in HTML
]
NOW = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)


def club():
    return Club(
        id=1,
        name="Comix",
        address="",
        website="https://www.comixroadhouse.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def event(i=0):
    d = DATA[i]
    return ComixRoadhouseEvent(d["name"], d["startDate"], "https://www.comixroadhouse.com/comics/test", d["url"])


def html(data):
    return '<script type="application/ld+json">' + json.dumps(data) + "</script>"


def parse(data):
    return extract_checkout(html(data), event(), "America/New_York", NOW)[0]


@pytest.mark.parametrize("i,prices", [(0, [35, 25, 15]), (1, [25, 15])])
def test_retained_named_admission_and_separate_fee_food_policies(i, prices):
    e = event(i)
    e.tickets, e.checkout_policies = extract_checkout(HTML[i], e, "America/New_York", NOW)
    show = e.to_show(club())
    assert [t.price for t in show.tickets] == prices
    assert "General Admission" in show.tickets[-1].type
    assert all(t.purchase_url == e.ticket_url and not t.sold_out for t in show.tickets)
    assert "15.00% SERVICE FEE" in show.description and "$10 FOOD-BEV MIN" in show.description
    assert all(t.price != 10 for t in show.tickets)


def test_venue_naive_local_date_matches_offset_checkout():
    e = event()
    e.start_date = "2026-09-27 17:00:00"
    tickets, _ = extract_checkout(HTML[0], e, "America/New_York", NOW)
    assert min(t.price for t in tickets) == 15


@pytest.mark.parametrize(
    "field,value",
    [
        ("url", "https://events.leapevents.com/event/other"),
        ("startDate", "2026-09-27T18:00:00-0400"),
        ("startDate", "2026-09-27T17:00:00"),
        ("startDate", "bad"),
        ("eventStatus", "https://schema.org/EventCancelled"),
        ("offers", None),
    ],
)
def test_unrelated_malformed_or_cancelled_event_cannot_supply_price(field, value):
    d = deepcopy(DATA[0])
    d[field] = value
    assert parse(d) == []


def test_graph_recommendation_does_not_leak_and_conflicting_identity_is_rejected():
    other = deepcopy(DATA[0])
    other["url"] += "-other"
    other["offers"][0]["price"] = "1"
    assert [t.price for t in parse({"@graph": [other, DATA[0]]})] == [35, 25, 15]
    other["url"] = DATA[0]["url"]
    assert parse([other, DATA[0]]) == []


def test_canonical_redirect_and_wrong_offer_url_are_rejected():
    content = '<link rel="canonical" href="https://events.leapevents.com/event/other">' + HTML[0]
    assert extract_checkout(content, event(), "America/New_York", NOW) == ([], [])
    d = deepcopy(DATA[0])
    d["offers"][0]["url"] += "-other"
    assert [t.price for t in parse(d)] == [25, 15]


@pytest.mark.parametrize(
    "url",
    [
        "http://events.leapevents.com/event/test",
        "https://evil.test/event/test",
        "https://events.leapevents.com.evil.test/event/test",
        "https://events.leapevents.com/admin/test",
        "https://user@events.leapevents.com/event/test",
        "https://events.leapevents.com:444/event/test",
        "",
        None,
    ],
)
def test_only_public_https_checkout_urls_are_fetchable(url):
    assert checkout_url(url) == ""


def test_tracking_and_trailing_slash_do_not_break_identity():
    e = event()
    e.ticket_url += "/?utm_source=comix#tickets"
    tickets, _ = extract_checkout(HTML[0], e, "America/New_York", NOW)
    assert [t.price for t in tickets] == [35, 25, 15]


@pytest.mark.parametrize(
    "field,value",
    [
        ("price", "0"),
        ("price", "-1"),
        ("price", "NaN"),
        ("price", "Infinity"),
        ("price", "1e100"),
        ("price", None),
        ("price", True),
        ("priceCurrency", "CAD"),
        ("priceCurrency", None),
        ("availability", "SoldOut"),
        ("availability", "PreOrder"),
        ("availability", None),
        ("validFrom", "2026-10-01T00:00:00Z"),
        ("validFrom", None),
        ("validThrough", "2026-09-26T00:00:00Z"),
        ("validThrough", "bad"),
        ("name", "VIP dinner package"),
        ("name", "Food and Beverage Minimum"),
        ("eligibleQuantity", {"minValue": 2}),
    ],
)
def test_unverified_or_non_individual_prices_stay_unknown(field, value):
    d = deepcopy(DATA[0])
    d["offers"][0][field] = value
    tickets = parse(d)
    assert tickets[0].price is None
    assert [t.price for t in tickets[1:]] == [25, 15]
    if value == "SoldOut":
        assert tickets[0].sold_out


def test_past_checkout_instock_does_not_override_expired_sale_window():
    tickets, _ = extract_checkout(HTML[0], event(), "America/New_York", datetime(2026, 10, 5, tzinfo=timezone.utc))
    assert all(t.price is None and "not currently purchasable" in t.type for t in tickets)


@pytest.mark.asyncio
async def test_enrichment_deduplicates_fetch_but_matches_each_performance():
    s = ComixRoadhouseScraper(club())
    s.fetch_html = AsyncMock(return_value=HTML[0])
    events = [event(), event()]
    events[1].start_date = "2026-09-28 17:00:00"
    with time_machine.travel(NOW, tick=False):
        await s._enrich_checkouts(events)
    s.fetch_html.assert_awaited_once_with(DATA[0]["url"], skip_js_fallback=True)
    assert [t.price for t in events[0].tickets] == [35, 25, 15]
    assert events[1].to_show(club()).tickets[0].price is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, RuntimeError("blocked")])
async def test_optional_failure_preserves_venue_performance(failure):
    s = ComixRoadhouseScraper(club())
    s.fetch_html = AsyncMock(return_value=None, side_effect=failure)
    e = event()
    await s._enrich_checkouts([e])
    show = e.to_show(club())
    assert show.name == e.name and show.tickets[0].price is None


@pytest.mark.asyncio
async def test_total_budget_cancels_pending_requests_with_four_active_max(monkeypatch):
    s = ComixRoadhouseScraper(club())
    active = peak = 0

    async def fetch(*args, **kwargs):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(10)
        finally:
            active -= 1

    s.fetch_html = fetch
    monkeypatch.setattr(scraper_mod, "_CHECKOUT_BUDGET", 0.03)
    events = [event() for _ in range(8)]
    for i, e in enumerate(events):
        e.ticket_url += str(i)
    await asyncio.wait_for(s._enrich_checkouts(events), 1)
    assert peak == 4 and active == 0 and all(not e.tickets for e in events)


@pytest.mark.asyncio
async def test_individual_timeout_retains_other_successful_checkout(monkeypatch):
    s = ComixRoadhouseScraper(club())

    async def fetch(url, **kwargs):
        if url != DATA[0]["url"]:
            await asyncio.sleep(10)
        return HTML[0]

    s.fetch_html = fetch
    monkeypatch.setattr(scraper_mod, "_CHECKOUT_TIMEOUT", 0.01)
    events = [event(), event(1)]
    await s._enrich_checkouts(events)
    assert events[0].tickets and not events[1].tickets
