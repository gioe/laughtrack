"""Odoo detached-form association, unit semantics, and fetch integration."""

import asyncio
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.api.odoo_events.pricing import extract_registration_offers
from laughtrack.scrapers.implementations.api.odoo_events.scraper import OdooEventsScraper
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor

URL = "https://www.comedyplex.com/event/comedy-plex-presents-matt-torres-926/register"
AUDIT = Path(__file__).resolve().parents[5] / "docs/audits/2026-09-27-price-extraction/ticketing"
HTML = (AUDIT / "odoo_events-9092-detail.html").read_text()


def club():
    return Club(
        id=9092,
        name="Comedy Plex",
        address="",
        website="https://www.comedyplex.com/",
        popularity=0,
        zip_code="60301",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )


def parsed_event(html=HTML, url=URL):
    return EventExtractor.extract_events(html, base_url=url, same_as_override=url)[0]


def ticket_from(html):
    event = parsed_event(html)
    evidence = extract_registration_offers(html, URL)
    assert evidence.matches(event)
    event.offers = evidence.offers
    return event.to_show(club()).tickets[0]


def altered(prop, value):
    soup = BeautifulSoup(HTML, "html.parser")
    node = soup.select_one(f'form#registration_form [itemprop="{prop}"]')
    node.attrs.pop("content", None)
    node.attrs.pop("href", None)
    node.clear()
    node["content"] = str(value)
    return str(soup)


def test_real_detached_form_reproduces_shared_gap_and_recovers_named_admission():
    event = parsed_event()
    assert event.offers == []  # Shared microdata scope rules remain strict.
    ticket = ticket_from(HTML)
    assert ticket.price == 15 and ticket.type == "Matt Torres"
    assert ticket.purchase_url == URL and not ticket.sold_out
    assert parsed_event().offers == []


@pytest.mark.parametrize(
    "action",
    [
        "/event/wrong-925/registration/new",
        "https://other.test/event/comedy-plex-presents-matt-torres-926/registration/new",
        "/event/comedy-plex-presents-matt-torres-926/register",
        "",
        "/event/other-slug-926/registration/new",
    ],
)
def test_wrong_event_or_origin_form_is_rejected(action):
    soup = BeautifulSoup(HTML, "html.parser")
    soup.select_one("#registration_form")["action"] = action
    assert extract_registration_offers(str(soup), URL) is None


def test_unrelated_modal_offer_cannot_supply_a_price():
    soup = BeautifulSoup(HTML, "html.parser")
    form = soup.select_one("#registration_form")
    form.extract()
    form["id"] = "unrelated_modal"
    soup.append(form)
    assert extract_registration_offers(str(soup), URL) is None


@pytest.mark.parametrize("identity", ["wrong-id", "no-identity", "two-events", "wrong-url"])
def test_event_identity_must_be_unambiguous(identity):
    soup = BeautifulSoup(HTML, "html.parser")
    scope = soup.select_one('[itemtype="http://schema.org/Event"]')
    if identity == "wrong-id":
        scope.select_one("[data-res-id]")["data-res-id"] = "925"
    elif identity == "no-identity":
        for node in scope.select('[data-res-model="event.event"]'):
            del node["data-res-model"]
    elif identity == "two-events":
        soup.append(deepcopy(scope))
    else:
        node = soup.new_tag("link", itemprop="url", href="/event/wrong-925/register")
        scope.append(node)
    assert extract_registration_offers(str(soup), URL) is None


@pytest.mark.parametrize("price", ["0", "-5", "", "NaN", "Infinity", "unknown", "1e100"])
def test_invalid_and_placeholder_prices_stay_unknown(price):
    assert ticket_from(altered("price", price)).price is None


@pytest.mark.parametrize("currency", ["CAD", "EUR", ""])
def test_currency_is_not_assumed_or_converted(currency):
    ticket = ticket_from(altered("priceCurrency", currency))
    assert ticket.price is None
    assert (currency or "currency unspecified") in ticket.type and "15.0" in ticket.type


@pytest.mark.parametrize("availability", ["SoldOut", "OutOfStock", "Discontinued"])
def test_unavailable_tier_preserves_sold_out_without_advertised_minimum(availability):
    ticket = ticket_from(altered("availability", "http://schema.org/" + availability))
    assert ticket.price is None and ticket.sold_out
    assert availability in ticket.type and "15.0" in ticket.type


@pytest.mark.parametrize("change", ["disabled", "only-zero", "disabled-options", "disabled-fieldset"])
def test_quantity_control_must_allow_positive_purchase(change):
    soup = BeautifulSoup(HTML, "html.parser")
    selector = soup.select_one('select[name^="nb_register-"]')
    if change == "disabled":
        selector["disabled"] = ""
    elif change == "only-zero":
        for option in selector.select("option")[1:]:
            option.decompose()
    elif change == "disabled-options":
        for option in selector.select("option")[1:]:
            option["disabled"] = ""
    else:
        fieldset = soup.new_tag("fieldset", disabled="")
        selector.wrap(fieldset)
    assert ticket_from(str(soup)).price is None


def test_selected_quantity_does_not_change_unit_price_or_disabled_submit_mean_sold_out():
    soup = BeautifulSoup(HTML, "html.parser")
    for option in soup.select("select option"):
        option.attrs.pop("selected", None)
        if option.get_text(strip=True) == "9":
            option["selected"] = ""
    assert soup.select_one('#registration_form button[type="submit"]').has_attr("disabled")
    ticket = ticket_from(str(soup))
    assert ticket.price == 15 and not ticket.sold_out


def test_package_amount_is_retained_without_division_or_individual_minimum():
    ticket = ticket_from(altered("name", "Table for 2"))
    assert ticket.price is None and "Table for 2" in ticket.type and "USD 15.0" in ticket.type


def test_multiple_tiers_keep_price_and_quantity_boundaries():
    soup = BeautifulSoup(HTML, "html.parser")
    row = soup.select_one(".o_wevent_registration_single")
    row["class"] = ["o_wevent_ticket_selector"]
    row.select_one('[itemprop="name"]').string = "Advace Tickets"
    row.select_one('[itemprop="price"]').string = "20.0"
    row.select_one('[itemprop="availability"]').decompose()
    second = deepcopy(row)
    second.select_one('[itemprop="name"]').string = "Day Of Tickets"
    second.select_one('[itemprop="price"]').string = "25.0"
    second.select_one("select").decompose()
    row.insert_after(second)
    ev = parsed_event(str(soup))
    ev.offers = extract_registration_offers(str(soup), URL).offers
    tickets = ev.to_show(club()).tickets
    assert [(t.type, t.price) for t in tickets] == [
        ("Advace Tickets", 20),
        ("Day Of Tickets (USD 25.0) [NotOnSale; quantity unavailable]", None),
    ]


@pytest.mark.asyncio
async def test_get_data_fetches_once_and_preserves_utc_normalization():
    scraper = OdooEventsScraper(club())
    scraper.fetch_html = AsyncMock(return_value=HTML)
    data = await scraper.get_data(URL)
    scraper.fetch_html.assert_awaited_once_with(URL)
    event = data.event_list[0]
    assert event.start_date.isoformat() == "2026-10-01T19:30:00-05:00"
    assert event.to_show(club()).tickets[0].price == 15
    assert not scraper._registration_offers


@pytest.mark.asyncio
async def test_existing_scoped_offers_are_not_overwritten():
    soup = BeautifulSoup(HTML, "html.parser")
    scope = soup.select_one('[itemtype="http://schema.org/Event"]')
    offer = BeautifulSoup(
        '<div itemprop="offers" itemscope itemtype="http://schema.org/Offer"><meta itemprop="price" content="30"><meta itemprop="priceCurrency" content="USD"></div>',
        "html.parser",
    )
    scope.append(offer)
    scraper = OdooEventsScraper(club())
    scraper.fetch_html = AsyncMock(return_value=str(soup))
    data = await scraper.get_data(URL)
    assert data.event_list[0].to_show(club()).tickets[0].price == 30


@pytest.mark.asyncio
async def test_concurrent_pages_do_not_exchange_offers():
    scraper = OdooEventsScraper(club())
    other = URL.replace("-926/", "-927/")
    other_html = altered("price", "45").replace("-926/", "-927/").replace('data-res-id="926"', 'data-res-id="927"')

    async def fetch(url):
        await asyncio.sleep(0)
        return HTML if url == URL else other_html

    scraper.fetch_html = fetch
    results = await asyncio.gather(scraper.get_data(URL), scraper.get_data(other))
    assert [data.event_list[0].to_show(club()).tickets[0].price for data in results] == [15, 45]
    assert not scraper._registration_offers


@pytest.mark.asyncio
async def test_missing_form_after_success_does_not_reuse_stale_price():
    scraper = OdooEventsScraper(club())
    soup = BeautifulSoup(HTML, "html.parser")
    soup.select_one("#registration_form").decompose()
    scraper.fetch_html = AsyncMock(side_effect=[HTML, str(soup), RuntimeError("fetch failed")])
    first = await scraper.get_data(URL)
    second = await scraper.get_data(URL)
    third = await scraper.get_data(URL)
    assert first.event_list[0].offers and not second.event_list[0].offers
    assert second.event_list[0].to_show(club()).tickets[0].price is None
    assert third is None and not scraper._registration_offers
