from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.api.seetickets_whitelabel.extractor import SeeTicketsWhitelabelExtractor

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
RETAINED = ROOT / "docs/audits/2026-09-27-price-extraction/ticketing/seetickets_whitelabel-11482-listing.html"


def extract(html):
    return SeeTicketsWhitelabelExtractor.extract_calendar_events(str(html), "https://portcomedy.com")


@pytest.fixture
def source():
    return BeautifulSoup(RETAINED.read_text(), "html.parser")


def priced_card(source):
    return next(
        c
        for c in source.select(".seetickets-list-event-content-container")
        if "/682818" in c.select_one(".event-title a")["href"]
    )


def ticket(event):
    club = Club(
        id=11479,
        name="The Port Comedy Club",
        address="813 S Broadway, Baltimore, MD 21231",
        website="https://portcomedy.com/",
        popularity=0,
        zip_code="21231",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    return event.to_show(club).tickets[0]


def test_retained_exact_matches_and_unresolved_prices(source):
    events = extract(source)
    assert len(events) == 144
    assert {e.event_id: ticket(e).price for e in events if e.price is not None} == {
        "682818": 29.0,
        "682820": 29.0,
        "682823": 29.0,
    }
    assert sum(ticket(e).price is None for e in events) == 141
    t = ticket(next(e for e in events if e.event_id == "682818"))
    assert "$29.00-$39.00" in t.type
    assert "fees unspecified" in t.type
    assert not t.sold_out


@pytest.mark.parametrize(
    "price",
    [
        "$0.00",
        "$0.00-$39.00",
        "Free",
        "",
        "$NaN",
        "-$29.00",
        "Bar minimum $29.00",
        "$29.00 per table",
        "CAD $29.00",
        "$29.00 + $5.00 fees",
    ],
)
def test_placeholders_and_unrelated_amounts_stay_unknown(source, price):
    priced_card(source).select_one(".price").string = price
    assert ticket(next(e for e in extract(source) if e.event_id == "682818")).price is None


@pytest.mark.parametrize(
    "selector,value",
    [
        (".event-date", "Fri Oct 2"),
        (".event-date", "Fri Oct 1"),
        (".event-date", "Oct 1"),
        (".see-showtime", "7:30PM"),
        ("a.seetickets-buy-btn", "Sold Out"),
    ],
)
def test_date_time_and_availability_must_agree(source, selector, value):
    priced_card(source).select_one(selector).string = value
    assert next(e for e in extract(source) if e.event_id == "682818").price is None


@pytest.mark.parametrize(
    "selector,href",
    [
        (".event-title a", "https://wl.seetickets.us/event/other/999999"),
        (".event-title a", "https://other.example/event/michael/682818"),
        (".event-title a", "https://wl.seetickets.us/event/michael/68281899"),
        ("a.seetickets-buy-btn", "https://wl.seetickets.us/event/other/682820"),
    ],
)
def test_cross_event_and_host_joins_are_rejected(source, selector, href):
    priced_card(source).select_one(selector)["href"] = href
    assert next(e for e in extract(source) if e.event_id == "682818").price is None


@pytest.mark.parametrize("selector", [".price", ".event-date", ".see-showtime", "a.seetickets-buy-btn"])
def test_missing_evidence_leaves_unknown(source, selector):
    priced_card(source).select_one(selector).decompose()
    assert next(e for e in extract(source) if e.event_id == "682818").price is None


@pytest.mark.parametrize("change", ["price", "time", "identical"])
def test_duplicate_evidence_must_be_unanimous(source, change):
    original = priced_card(source)
    duplicate = deepcopy(original)
    if change == "price":
        duplicate.select_one(".price").string = "$19.00"
    elif change == "time":
        duplicate.select_one(".see-showtime").string = "9:00PM"
    original.insert_after(duplicate)
    assert next(e for e in extract(source) if e.event_id == "682818").price == (29.0 if change == "identical" else None)


def test_unrelated_dollars_and_same_title_do_not_supply_price(source):
    c = priced_card(source)
    c.select_one(".price").decompose()
    c.select_one(".subtitle").string = "$500 VIP package"
    assert next(e for e in extract(source) if e.event_id == "682818").price is None
    assert next(e for e in extract(source) if e.event_id == "682820").price == 29.0


def test_calendar_sold_out_overrides_list_buy_button(source):
    c = next(
        c
        for c in source.select(".seetickets-calendar-event-container")
        if "/682818" in c.select_one(".seetickets-calendar-event-title a")["href"]
    )
    c.select_one(".seetickets-buy-btn")["class"].append("button-soldout")
    t = ticket(next(e for e in extract(source) if e.event_id == "682818"))
    assert t.sold_out and t.price is None


def test_calendar_only_source_stays_unknown():
    events = extract((Path(__file__).parent / "fixtures/official_calendar.html").read_text())
    assert events and all(ticket(e).price is None for e in events)
