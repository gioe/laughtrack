"""Explicit dated free admission, never zero placeholders or incidental prose."""

import asyncio
import copy
import html
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.squarespace.extractor import SquarespaceExtractor
from laughtrack.scrapers.implementations.api.squarespace.pricing import explicit_free_admission, product_price
from laughtrack.scrapers.implementations.api.squarespace.scraper import SquarespaceScraper

FIXTURES = Path(__file__).parent / "fixtures"
DETAIL = json.loads((FIXTURES / "chaos_free_detail.json").read_text())
CALENDAR = json.loads((FIXTURES / "chaos_october_calendar.json").read_text())
BASE = "https://chaosbloom.com"


def event():
    return SquarespaceExtractor._parse_event(copy.deepcopy(DETAIL["item"]), BASE)


def product_detail(**changes):
    detail = copy.deepcopy(DETAIL)
    soup = BeautifulSoup(detail["item"]["body"], "html.parser")
    block = soup.select_one(".product-block[data-product]")
    product = json.loads(block["data-product"])
    product.update(changes)
    block["data-product"] = json.dumps(product)
    detail["item"]["body"] = str(soup)
    return detail


def test_captured_free_jam_has_dated_available_usd_admission():
    assert explicit_free_admission(event(), DETAIL)


@pytest.mark.parametrize(
    "field,value",
    [
        ("fullUrl", "/shows-calendar/another-week"),
        ("fullUrl", "https://example.com/same"),
        ("title", "A different FREE Improv Comedy Jam"),
        ("startDate", 1793505600222),
        ("startDate", None),
        ("startDate", True),
        ("startDate", float("nan")),
        ("body", "Free drinks! $0"),
        ("body", "FREE admission"),
    ],
)
def test_detail_identity_and_structured_evidence_required(field, value):
    detail = copy.deepcopy(DETAIL)
    detail["item"][field] = value
    assert not explicit_free_admission(event(), detail)


def test_matching_second_accepts_only_subsecond_formatting_drift():
    e = event()
    e.start_date_ms -= 222
    assert explicit_free_admission(e, DETAIL)
    e.start_date_ms += 1000
    assert not explicit_free_admission(e, DETAIL)


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "Free drinks"},
        {"title": "Halloween Party"},
        {"description": "Free with purchase"},
        {"description": "Coupon discount required"},
        {"description": "Two drink minimum"},
        {"description": "Members only"},
        {"price": {"currency": "CAD", "value": "0.00"}},
        {"price": {"currency": "USD", "value": "8.00"}},
        {"price": {"currency": "USD", "value": None}},
        {"price": {"currency": "USD", "value": "NaN"}},
        {"price": {"currency": "USD", "value": False}},
        {"published": False},
        {"soldOut": True},
        {"onSale": True},
        {"variants": []},
        {"variants": [{}]},
        {"mightHavePaymentPlan": True},
    ],
)
def test_incidental_free_conditional_or_unavailable_product_is_unknown(changes):
    assert not explicit_free_admission(event(), product_detail(**changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"price": {"currency": "USD", "value": "20.00"}},
        {"price": {"currency": "EUR", "value": "0.00"}},
        {"unlimited": False, "qtyInStock": 0},
        {"soldOut": True},
        {"attributes": {"ticket": "Members"}},
    ],
)
def test_zero_parent_cannot_override_variant_evidence(changes):
    block = BeautifulSoup(DETAIL["item"]["body"], "html.parser").select_one("[data-product]")
    p = json.loads(block["data-product"])
    p["variants"][0].update(changes)
    assert not explicit_free_admission(event(), product_detail(variants=p["variants"]))


def test_unrelated_sidebar_products_and_conflicting_price_do_not_prove_free():
    d = copy.deepcopy(DETAIL)
    d["item"]["body"] = "<p>Show details unavailable</p>"
    d["sidebar"] = DETAIL["item"]["body"]
    assert not explicit_free_admission(event(), d)
    e = event()
    e.price = 20
    assert not explicit_free_admission(e, DETAIL)
    d = copy.deepcopy(DETAIL)
    d["item"]["body"] *= 2
    assert not explicit_free_admission(event(), d)


def test_halloween_and_parent_zero_still_unknown():
    captured = json.loads((FIXTURES / "price_products.json").read_text())
    halloween = next(x["product"] for x in captured if "Halloween" in x["product"]["title"])
    assert product_price(halloween)[0] is None
    assert not explicit_free_admission(event(), {"item": halloween})


def test_current_calendar_retains_all_performances_despite_reused_artwork():
    events = SquarespaceExtractor.extract_events(CALENDAR, BASE)
    assert len(events) == 37
    assert len({e.id for e in events}) == 37
    assert len({r["systemDataId"] for r in CALENDAR}) < 37
    assert all(e.start_date_ms == r["structuredContent"]["startDate"] for e, r in zip(events, CALENDAR))


@pytest.mark.parametrize(
    "changes",
    [
        {"fullUrl": "//evil.test/event"},
        {"fullUrl": "https://evil.test/event"},
        {"fullUrl": "/event?date=other"},
        {"fullUrl": "/event#other"},
        {"fullUrl": ""},
        {"recordType": 1},
        {"structuredContent": None},
        {"structuredContent": {"startDate": True}},
        {"structuredContent": {"startDate": float("inf")}},
    ],
)
def test_malformed_nested_calendar_records_do_not_get_synthetic_identity(changes):
    raw = copy.deepcopy(CALENDAR[0])
    raw.update(changes)
    assert SquarespaceExtractor._parse_event(raw, BASE) is None


def venue():
    c = Club(
        id=11295,
        name="Chaos Bloom Theater",
        address="",
        website=BASE,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/Denver",
    )
    source = ScrapingSource(
        id=1,
        club_id=c.id,
        platform="custom",
        scraper_key="squarespace",
        source_url=BASE + "/api/open/GetItemsByMonth?collectionId=test",
        external_id=None,
    )
    c.active_scraping_source = source
    c.scraping_sources = [source]
    return c


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["valid", "mismatch", "failure", "malformed"])
async def test_existing_detail_fetch_enriches_or_preserves_show(monkeypatch, mode):
    c = venue()
    scraper = SquarespaceScraper(c)
    calls = []
    raw = next(x for x in CALENDAR if x["fullUrl"] == DETAIL["item"]["fullUrl"])

    async def fetch_list(url, **kwargs):
        return [raw]

    async def fetch_detail(url, **kwargs):
        calls.append(url)
        if mode == "failure":
            raise RuntimeError("test failure")
        if mode == "malformed":
            return {"item": None}
        detail = copy.deepcopy(DETAIL)
        if mode == "mismatch":
            detail["item"]["startDate"] += 86400000
        return detail

    monkeypatch.setattr(scraper, "fetch_json_list", fetch_list)
    monkeypatch.setattr(scraper, "fetch_json", fetch_detail)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: asyncio.sleep(0))
    data = await scraper.get_data(BASE + "/api/open/GetItemsByMonth?month=10-2026")
    assert data and len(data.event_list) == 1
    show = data.event_list[0].to_show(c, enhanced=False)
    assert show is not None and show.tickets[0].price == (0.0 if mode == "valid" else None)
    assert show.show_page_url == BASE + raw["fullUrl"]
    assert show.date.timestamp() == raw["structuredContent"]["startDate"] / 1000
    assert len(calls) == 1
