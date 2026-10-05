from datetime import timezone
from pathlib import Path

import pytest
import time_machine
from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.zanies.extractor import ZaniesExtractor
from laughtrack.scrapers.implementations.venues.zanies.scraper import ZaniesScraper


AUDIT = Path(__file__).resolve().parents[5] / "docs/audits/2026-09-27-price-extraction/venues"


def club():
    return Club(id=1, name="Zanies", address="1548 N Wells St", website="https://chicago.zanies.com",
                popularity=0, zip_code="60610", phone_number="", visible=True, timezone="America/Chicago")


def captured():
    return (AUDIT / "zanies-1.html").read_text()


def extract(html):
    return ZaniesExtractor.extract_single_show_events(html)[0]


@time_machine.travel("2026-09-27T12:00:00Z", tick=False)
def test_captured_admission_survives_model_despite_structured_zero():
    event = extract(captured())
    show = event.to_show(club())
    assert show.tickets[0].price == 37.95
    assert "/p/75851627/" in show.tickets[0].purchase_url
    assert show.date.astimezone(timezone.utc).isoformat() == "2026-09-28T00:00:00+00:00"
    assert "venue advertised" in show.tickets[0].type


@pytest.mark.asyncio
async def test_scraper_keeps_price_from_existing_detail_fetch(monkeypatch):
    async def fetch(self, url):
        return captured()

    monkeypatch.setattr(ZaniesScraper, "fetch_html", fetch)
    data = await ZaniesScraper(club()).get_data("https://chicago.zanies.com/show/tim-convy-sean-obrien/")
    assert data.event_list[0].to_show(club()).tickets[0].price == 37.95


@pytest.mark.parametrize("amount", ["$0", "$0.00", "$-5", "$26–$40", "$26 to $40",
    "$26 + $5 fees", "CAD $26", "€26", "2 tickets $26", "$10 item minimum", "Free", "", "$NaN"])
def test_ambiguous_or_nonpositive_amount_stays_unknown(amount):
    event = extract(captured().replace("$37.95", amount))
    assert event.ticket_price is None
    assert event.to_show(club()).tickets[0].price is None


def test_minimum_and_unrelated_recommendation_do_not_supply_price():
    soup = BeautifulSoup(captured(), "html.parser")
    soup.select_one(".eventCost").decompose()
    html = str(soup) + '<aside><div class="eventCost">$12</div></aside>'
    assert extract(html).ticket_price is None


@pytest.mark.parametrize("kind", ["date", "time", "ticket", "title", "price"])
def test_conflicting_identity_or_price_in_container_stays_unknown(kind):
    soup = BeautifulSoup(captured(), "html.parser")
    extras = {
        "date": '<span class="eventStDate">Monday, September 28</span>',
        "time": '<div class="eventDoorStartDate">Doors: 8 pm Show: 9 pm</div>',
        "ticket": '<a href="https://www.etix.com/ticket/p/999/other">Tickets</a>',
        "title": '<h1>Other show</h1>',
        "price": '<div class="eventCost">$12</div>',
    }
    soup.select_one(".singleEventDetails").append(BeautifulSoup(extras[kind], "html.parser"))
    assert extract(str(soup)).ticket_price is None


@pytest.mark.parametrize("field,value", [("date_str", "Monday, September 28"),
    ("ticket_url", "https://www.etix.com/ticket/p/999/other"), ("time_str", "Doors: 8 pm Show: 9 pm")])
def test_price_cannot_attach_to_a_different_performance(field, value):
    event = extract(captured().replace("$37.95", ""))
    setattr(event, field, value)
    ZaniesExtractor._attach_single_price(captured(), event)
    assert event.ticket_price is None


def test_duplicate_identical_price_is_allowed():
    soup = BeautifulSoup(captured(), "html.parser")
    soup.select_one(".singleEventDetails").append(BeautifulSoup('<div class="eventCost">$37.95</div>', "html.parser"))
    assert extract(str(soup)).ticket_price == 37.95


def test_series_header_price_never_flows_to_performances():
    html = '<h1>Series</h1><div class="eventCost">$26</div><ul>'
    for n in (27, 28):
        html += f'''<li class="rhp-event-series-individual">
        <div class="rhp-event-series-date">Sunday, September {n}</div>
        <div class="rhp-event-series-time">Doors: 6 pm Show: 7 pm</div>
        <a href="https://www.etix.com/ticket/p/{n}/test">Tickets</a></li>'''
    events = ZaniesExtractor.extract_series_events(html + '</ul><div class="eventCost">$12</div>')
    assert len(events) == 2
    assert all(e.ticket_price is None for e in events)


@pytest.mark.parametrize("number", [2, 3])
def test_retained_homepage_prices_are_not_single_performance_prices(number):
    events = ZaniesExtractor.extract_single_show_events((AUDIT / f"zanies-{number}.html").read_text())
    assert all(e.ticket_price is None for e in events)


@pytest.mark.parametrize("price", [0, -1, float("nan"), float("inf")])
def test_model_rejects_nonpositive_and_nonfinite_price(price):
    event = extract(captured())
    event.ticket_price = price
    assert event.to_show(club()).tickets[0].price is None
