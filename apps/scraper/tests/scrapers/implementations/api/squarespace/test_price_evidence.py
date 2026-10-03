"""Captured product admission prices and conservative rejection cases (TASK-4089)."""

import asyncio
import copy
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import time_machine

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.squarespace.extractor import SquarespaceExtractor
from laughtrack.scrapers.implementations.api.squarespace.scraper import SquarespaceScraper

CAPTURED = json.loads((Path(__file__).parent / "fixtures/price_products.json").read_text())


def club(cid=9075):
    return Club(
        id=cid,
        name="Test venue",
        address="",
        website="https://westsideimprov.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def product():
    raw = copy.deepcopy(CAPTURED[0]["product"])
    # The API mirrors the same variants at the root. Edge tests alter the
    # canonical representation alone unless specifically exercising conflict.
    raw.pop("variants", None)
    return raw


def ticket(raw):
    with time_machine.travel("2026-09-27T12:00:00Z", tick=False):
        event = SquarespaceExtractor._parse_product(raw, club().website, ZoneInfo(club().timezone))
    assert event is not None
    show = event.to_show(club(), enhanced=False)
    assert show is not None
    assert show.name == raw["title"]
    assert show.show_page_url == club().website + raw["fullUrl"]
    assert len(show.tickets) == 1
    return show.tickets[0]


@pytest.mark.parametrize("index,expected", [(0, 8.0), (1, 35.0), (2, 20.0), (3, 5.0), (4, None)])
def test_captured_products_round_trip(index, expected):
    assert ticket(copy.deepcopy(CAPTURED[index]["product"])).price == expected


def test_decimal_money_and_cents_agree_without_double_division():
    raw = product()
    v = raw["structuredContent"]["variants"][0]
    v["priceMoney"]["value"] = "12.34"
    v["price"] = 1234
    assert ticket(raw).price == 12.34


def test_legacy_cents_require_explicit_currency():
    raw = product()
    v = raw["structuredContent"]["variants"][0]
    del v["priceMoney"]
    v["price"] = 1234
    assert ticket(raw).price is None
    v["currency"] = "USD"
    assert ticket(raw).price == 12.34


def test_only_active_sale_is_selected():
    raw = product()
    v = raw["structuredContent"]["variants"][0]
    v["salePriceMoney"]["value"] = "5.25"
    v["salePrice"] = 525
    assert ticket(raw).price == 8.0
    v["onSale"] = True
    assert ticket(raw).price == 5.25
    v["salePriceMoney"]["value"] = "0.00"
    v["salePrice"] = 0
    assert ticket(raw).price is None


@pytest.mark.parametrize("value", ["0.00", "-1.00", "NaN", "Infinity", "1.001", "100000", "bad", None, True])
def test_invalid_money_does_not_fall_back_to_legacy_or_parent(value):
    raw = product()
    v = raw["structuredContent"]["variants"][0]
    v["priceMoney"]["value"] = value
    assert ticket(raw).price is None


@pytest.mark.parametrize(
    "changes",
    [
        {"priceMoney": {"currency": "CAD", "value": "8.00"}},
        {"priceMoney": {"value": "8.00"}},
        {"currency": "EUR"},
        {"price": 801},
        {"onSale": "true"},
        {"onSale": None},
        {"qtyInStock": None},
        {"qtyInStock": -1},
        {"qtyInStock": True},
        {"qtyInStock": "40"},
        {"unlimited": "true"},
        {"attributes": {"Ticket": "Table for 4"}},
        {"optionValues": ["VIP package"]},
    ],
)
def test_ambiguous_currency_units_or_inventory_remain_unknown(changes):
    raw = product()
    raw["structuredContent"]["variants"][0].update(changes)
    assert ticket(raw).price is None


def test_sold_out_is_not_an_available_price_and_unlimited_overrides_stock():
    raw = product()
    v = raw["structuredContent"]["variants"][0]
    v["qtyInStock"] = 0
    assert ticket(raw).price is None
    assert ticket(raw).sold_out is True
    v["unlimited"] = True
    assert ticket(raw).price == 8.0
    assert ticket(raw).sold_out is False


@pytest.mark.parametrize(
    "copy_text",
    [
        "A table for 4 people",
        "Tickets for 2",
        "VIP package with unclear unit",
        "Buy a 4-pack",
        "The jam is free for audience members",
        "If you are coming to perform, buy this ticket",
    ],
)
def test_non_single_admission_prices_are_not_promoted(copy_text):
    raw = product()
    raw["excerpt"] = copy_text
    assert ticket(raw).price is None


def test_discount_prose_and_parent_zero_do_not_override_variant():
    raw = product()
    raw["excerpt"] = "Save $5! Drinks $3.50. $2 student discount."
    assert ticket(raw).price == 8.0
    raw["structuredContent"]["variants"] = []
    assert ticket(raw).price is None


def test_multiple_variants_or_conflicting_mirror_are_unknown():
    raw = product()
    variants = raw["structuredContent"]["variants"]
    variants.append(copy.deepcopy(variants[0]))
    assert ticket(raw).price is None
    variants.pop()
    raw["variants"] = []
    assert ticket(raw).price is None


def test_sale_currency_conflict_is_unknown():
    raw = product()
    v = raw["structuredContent"]["variants"][0]
    v.update(onSale=True, salePrice=525, salePriceMoney={"currency": "USD", "value": "5.25"})
    v["priceMoney"]["currency"] = "CAD"
    assert ticket(raw).price is None


@pytest.mark.asyncio
async def test_products_fetch_to_show_keeps_verified_price(monkeypatch):
    venue = club()
    source = ScrapingSource(
        id=1,
        club_id=venue.id,
        platform="custom",
        scraper_key="squarespace",
        source_url=venue.website + "/tickets",
        external_id=None,
        metadata={"collection_type": "products"},
    )
    venue.active_scraping_source = source
    venue.scraping_sources = [source]
    scraper = SquarespaceScraper(venue)
    urls = []

    async def fetch(url, **kwargs):
        urls.append(url)
        return {"items": [product()]}

    monkeypatch.setattr(scraper, "fetch_json", fetch)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda url: asyncio.sleep(0))
    data = await scraper.get_data(venue.website + "/tickets?format=json")
    assert data is not None
    show = data.event_list[0].to_show(venue, enhanced=False)
    assert show.tickets[0].price == 8.0
    assert show.tickets[0].purchase_url.endswith("/tickets/p/october-1-2026")
    assert show.date.strftime("%Y-%m-%d %H:%M") == "2026-10-01 19:30"
    assert "Sayard Bass" in show.description
    assert len(urls) == 1
