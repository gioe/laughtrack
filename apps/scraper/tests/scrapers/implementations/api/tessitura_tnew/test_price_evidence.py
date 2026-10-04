import asyncio
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import time_machine
from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.tessitura_tnew import TessituraTNEWEvent
from laughtrack.scrapers.implementations.api.tessitura_tnew.pricing import best_available_url, extract_admissions
from laughtrack.scrapers.implementations.api.tessitura_tnew.scraper import TessituraTNEWScraper

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
AUDIT = ROOT / "docs/audits/2026-09-27-price-extraction/ticketing"
GA = (AUDIT / "tessitura_tnew-8836-detail.html").read_text()
SEATED = (Path(__file__).parent / "gallo_available.html").read_text()
GALLO_CONFIG = (AUDIT / "tessitura_tnew-11138-detail.html").read_text()
EVENT = TessituraTNEWEvent(
    "Sunday Company",
    "2026-09-28T02:30:00+00:00",
    "https://purchase.groundlings.com/17753/18662",
    production_id="17753",
    performance_id="18662",
)
GALLO = TessituraTNEWEvent("Comedy", "2026-10-17T02:30:00+00:00", "https://tickets.galloarts.org/11397/11398")


def parse(html=GA, event=EVENT):
    return extract_admissions(str(html), event, "America/Los_Angeles")


def club():
    return Club(
        id=8836,
        name="Groundlings",
        address="7307 Melrose Ave",
        website="https://groundlings.com",
        popularity=0,
        zip_code="90046",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def test_retained_ga_offer_and_fee_semantics_survive_conversion():
    offers = parse()
    assert len(offers) == 1
    assert (offers[0].price, offers[0].base_price, offers[0].fees, offers[0].currency) == (27, 25, 2, "USD")
    assert offers[0].name == "General Admission — Adult Ticket"
    with time_machine.travel("2026-09-26T12:00:00Z", tick=False):
        ticket = replace(EVENT, admissions=offers).to_show(club()).tickets[0]
    assert ticket.price == 27
    assert "25.00 ticket + 2.00 fees" in ticket.type


def test_current_gallo_available_tier_excludes_cheaper_unavailable_seats():
    offers = parse(SEATED, GALLO)
    assert [(o.name, o.price, o.base_price, o.fees) for o in offers] == [("Parterre — Regular", 68, 59, 9)]
    assert not parse(GALLO_CONFIG, GALLO)
    assert best_available_url(GALLO_CONFIG, GALLO) == GALLO.show_page_url + "?z=0"


@pytest.mark.parametrize(
    "change",
    [
        {"performance_id": "999"},
        {"production_id": "999"},
        {"start_date_str": "2026-09-28T03:30:00Z"},
        {"show_page_url": "https://other.example/17753/18662"},
        {"is_on_sale": False},
        {"title": "Comedy Meet-and-Greet Add-on"},
        {"title": "Post-show Talkback"},
    ],
)
def test_listing_identity_date_and_addons_fail_closed(change):
    assert not parse(event=replace(EVENT, **change))


@pytest.mark.parametrize(
    "old,new",
    [
        ('"performanceId":18662', '"performanceId":999'),
        ('"productionSeasonId":17753', '"productionSeasonId":999'),
        ('"iso4217CurrencyCode":"USD"', '"iso4217CurrencyCode":"CAD"'),
        ("September 27, 2026 7:30PM", "September 28, 2026 7:30PM"),
    ],
)
def test_detail_identity_currency_date_must_agree(old, new):
    assert old in GA
    assert not parse(GA.replace(old, new))


@pytest.mark.parametrize(
    "case",
    [
        "zero",
        "missing",
        "disabled",
        "quantity-disabled",
        "option-disabled",
        "only-zero",
        "wrong-form",
        "wrong-hidden",
        "wrong-zone",
        "wrong-tier",
        "missing-date",
        "addon-tier",
        "addon-zone",
        "zero-price",
        "bad-fee",
        "multiple-dates",
    ],
)
def test_unavailable_malformed_and_addon_offers_stay_unknown(case):
    s = BeautifulSoup(GA, "html.parser")
    zone = s.select_one(".tn-ticket-selector__input-zone")
    tier = s.select_one('.tn-ticket-selector__pricetype-container[data-zone-id="37"]')
    selector = tier.select_one("select")
    if case == "zero":
        zone["data-tn-zone-available-count"] = "0"
    elif case == "missing":
        del zone["data-tn-zone-available-count"]
    elif case == "disabled":
        zone["disabled"] = ""
    elif case == "quantity-disabled":
        selector["disabled"] = ""
    elif case == "option-disabled":
        for option in selector.select("option"):
            option["disabled"] = ""
    elif case == "only-zero":
        for option in selector.select("option")[1:]:
            option.decompose()
    elif case == "wrong-form":
        s.select_one("form#tn-events-detail-best-available-form")["action"] = "/17753/999"
    elif case == "wrong-hidden":
        s.select_one('input[name="PerformanceId"]')["value"] = "999"
    elif case == "wrong-zone":
        selector["data-zone-id"] = "999"
    elif case == "wrong-tier":
        selector["data-pricetype-id"] = "999"
    elif case == "missing-date":
        s.select_one(".tn-event-detail__display-time").decompose()
    elif case == "addon-tier":
        tier.select_one(".tn-ticket-selector__pricetype-name").string = "Adult Meet-and-Greet $27.00"
    elif case == "addon-zone":
        tier.select_one("h3").string = "Quantity for Talkback"
    elif case == "zero-price":
        tier.select_one(".tn-ticket-selector__pricetype-name").string = "Adult Ticket $0.00"
    elif case == "bad-fee":
        tier.select_one(".tn-ticket-selector__pricetype-fee-breakdown").string = "$25.00 ticket + $5.00 fees"
    elif case == "multiple-dates":
        s.append(BeautifulSoup('<p class="tn-event-detail__display-time">September 27, 2026 7:30PM</p>', "html.parser"))
    assert not parse(s)


def test_missing_fee_breakdown_does_not_invent_fee_inclusion():
    s = BeautifulSoup(GA, "html.parser")
    s.select_one(".tn-ticket-selector__pricetype-fee-breakdown").decompose()
    offer = parse(s)[0]
    assert offer.price == 27 and offer.fees is None and offer.base_price is None


@pytest.mark.parametrize("target", ["https://other.example/11397/11398?z=0", "/11397/999?z=0", "/11397/11398?z=3"])
def test_best_available_link_cannot_change_identity(target):
    s = BeautifulSoup(GALLO_CONFIG, "html.parser")
    s.select_one(".tn-ticketing-mode-change__anchor")["href"] = target
    assert best_available_url(str(s), GALLO) is None


async def test_enrichment_follows_verified_selector_without_browser(monkeypatch):
    scraper = TessituraTNEWScraper(club())
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())
    fetch = AsyncMock(side_effect=[GALLO_CONFIG, SEATED])
    monkeypatch.setattr(scraper, "fetch_html", fetch)
    event = replace(GALLO, admissions=[])
    await scraper._attach_admissions([event], "https://tickets.galloarts.org/events")
    assert event.admissions[0].price == 68
    assert [c.args[0] for c in fetch.call_args_list] == [GALLO.show_page_url, GALLO.show_page_url + "?z=0"]
    assert all(c.kwargs == {"skip_js_fallback": True} for c in fetch.call_args_list)


async def test_failed_enrichment_preserves_listing_fallback(monkeypatch):
    scraper = TessituraTNEWScraper(club())
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())
    monkeypatch.setattr(scraper, "fetch_html", AsyncMock(side_effect=RuntimeError("offline")))
    event = replace(EVENT, admissions=[])
    await scraper._attach_admissions([event], "https://purchase.groundlings.com/events")
    with time_machine.travel("2026-09-26T12:00:00Z", tick=False):
        show = event.to_show(club())
    assert show and show.tickets[0].price is None


async def test_concurrency_is_bounded_and_cross_host_is_not_fetched(monkeypatch):
    scraper = TessituraTNEWScraper(club())
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())
    active = maximum = calls = 0

    async def fetch(url, **kwargs):
        nonlocal active, maximum, calls
        calls += 1
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0)
        active -= 1
        return GA

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    events = [replace(EVENT, admissions=[]) for _ in range(10)]
    await scraper._attach_admissions(events + [GALLO], "https://purchase.groundlings.com/events")
    assert calls == 10 and maximum == 4 and all(e.admissions for e in events)


async def test_phase_deadline_drains_cancelled_fetches(monkeypatch):
    scraper = TessituraTNEWScraper(club())
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())
    drained = []

    async def fetch(*args, **kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            drained.append(True)

    real_wait = asyncio.wait

    async def short_wait(tasks, timeout):
        assert timeout == 30
        return await real_wait(tasks, timeout=0.01)

    monkeypatch.setattr(scraper, "fetch_html", fetch)
    monkeypatch.setattr(asyncio, "wait", short_wait)
    event = replace(EVENT, admissions=[])
    await scraper._attach_admissions([event], "https://purchase.groundlings.com/events")
    assert drained == [True] and event.admissions == []
