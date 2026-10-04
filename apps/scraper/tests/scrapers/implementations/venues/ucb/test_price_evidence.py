"""Dated source evidence and negative controls for physical UCB admissions."""

import copy
import html as html_module
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from laughtrack.core.entities.event.ucb import UCBEvent
from laughtrack.scrapers.implementations.venues.ucb.pricing import extract_admissions
from laughtrack.scrapers.implementations.venues.ucb.scraper import UCBScraper
from .test_pipeline_smoke import _make_club

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = next(p for p in Path(__file__).parents if (p / "pyproject.toml").exists())
AUDIT = ROOT / "docs/audits/2026-09-27-price-extraction/platforms"


def source_event(document):
    location = document["location"]
    if isinstance(location, list):
        location = next(p for p in location if p["@type"] == "Place")
    name = location["name"]
    slug = {"LA - ANNEX": "la-annex", "LA - FRANKLIN": "la-franklin", "NY - 14TH ST. Mainstage": "nyc-mainstage"}[name]
    club = _make_club(slug)
    club.timezone = "America/New_York" if name.startswith("NY") else "America/Los_Angeles"
    event = UCBEvent(
        title=document["name"],
        date_text=datetime.fromisoformat(document["startDate"]).strftime("%A, %B %d, %Y @ %I:%M %p"),
        show_page_url=document["url"],
        ticket_url=document["url"],
        location_slug=slug,
        location_name=name,
    )
    return event, club


def replay(document, paragraphs=(), extra=""):
    """Reconstructed DOM for retained JSON audit data, not an original HTML capture."""
    return (
        '<script type="application/ld+json">'
        + json.dumps(document)
        + '</script><div class="ucb-event-description">'
        + "".join("<p>" + html_module.escape(text) + "</p>" for text in paragraphs)
        + "</div>"
        + extra
    )


def audit(key):
    data = json.loads((AUDIT / (key + "-evidence.json")).read_text())
    return data, next(d for d in data["jsonld"] if d.get("@type") == "ComedyEvent")


def convert(document, page=None):
    event, club = source_event(document)
    event.admissions = extract_admissions(page or replay(document), event, club)
    return event.to_show(club, enhanced=False)


@pytest.mark.parametrize("key", ["future8823", "future8834", "future16055"])
def test_three_retained_explicit_physical_free_admissions(key):
    _, document = audit(key)
    show = convert(document)
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 0
    assert show.tickets[0].sold_out is False
    assert "stream" not in show.tickets[0].type.lower()


def test_real_twenty_dollar_in_person_price_plus_unknown_fees():
    evidence, document = audit("16055")
    sentence = "In-person tickets are $20 plus fees."
    assert sentence in evidence["visible_text"]
    ticket = convert(document, replay(document, [sentence])).tickets[0]
    assert ticket.price == 20
    assert ticket.type == "General Admission (plus fees)"


def test_advance_and_door_prices_are_separate_from_livestream():
    evidence, document = audit("8834")
    sentence = "Tickets: $20 in advance, $25 on the day of the show"
    assert sentence in evidence["visible_text"]
    tickets = convert(document, replay(document, [sentence, "Livestream Tickets: $10"])).tickets
    assert [(t.type, t.price) for t in tickets] == [("Advance (fees unspecified)", 20), ("Door (fees unspecified)", 25)]


@pytest.mark.parametrize("key,expected", [("currentpaid", 7), ("currentmixed", 29.95), ("currentfree", 0)])
def test_live_captured_fragments_prefer_physical_offers_and_do_not_add_fees_twice(key, expected):
    page = (FIXTURES / (key + ".html")).read_text()
    document = next(
        json.loads(s.get_text())
        for s in BeautifulSoup(page, "html.parser").select('script[type="application/ld+json"]')
        if json.loads(s.get_text()).get("@type") == "ComedyEvent"
    )
    tickets = convert(document, page).tickets
    assert len(tickets) == 1
    assert tickets[0].price == expected
    if expected:
        assert tickets[0].type == "General Admission (fees included)"


@pytest.mark.parametrize("mutation", ["url", "date", "room", "country", "online", "cancelled", "offer_url"])
def test_reject_mismatched_event_identity(mutation):
    _, original = audit("future8823")
    changed = copy.deepcopy(original)
    if mutation == "url":
        changed["url"] = changed["url"].replace("09-27", "09-28")
    elif mutation == "date":
        changed["startDate"] = changed["startDate"].replace("19:00", "20:00")
    elif mutation == "room":
        changed["location"]["name"] = "LA - FRANKLIN"
    elif mutation == "country":
        changed["location"]["address"]["addressCountry"] = "CA"
    elif mutation == "online":
        changed["eventAttendanceMode"] = "https://schema.org/OnlineEventAttendanceMode"
    elif mutation == "cancelled":
        changed["eventStatus"] = "https://schema.org/EventCancelled"
    else:
        changed["offers"][0]["url"] = "https://ucbcomedy.com/show/different-show/"
    event, club = source_event(original)
    assert extract_admissions(replay(changed), event, club) == []


@pytest.mark.parametrize("price", [None, "", "NaN", "Infinity", "1e1000", -10, True, "USD 20"])
def test_invalid_amounts_stay_unknown(price):
    _, document = audit("future8823")
    document["offers"][0]["price"] = price
    assert convert(document).tickets[0].price is None


@pytest.mark.parametrize("mutation", ["currency", "availability", "soldout", "zero_without_proof"])
def test_unpriced_or_soldout_physical_offer_cannot_fall_back_to_marketing_text(mutation):
    _, document = audit("future8823")
    offer = document["offers"][0]
    offer.update(name="General Admission", price="20.00")
    if mutation == "currency":
        offer["priceCurrency"] = "CAD"
    elif mutation == "availability":
        offer.pop("availability")
    elif mutation == "soldout":
        offer["availability"] = "https://schema.org/SoldOut"
    else:
        offer["price"] = "0"
        document.pop("isAccessibleForFree")
    ticket = convert(document, replay(document, ["In-person tickets are $20 plus fees."])).tickets[0]
    assert ticket.price is None
    assert ticket.sold_out is (mutation == "soldout")


def test_livestream_only_and_generic_free_text_do_not_price_physical_admission():
    _, document = audit("8834")
    ticket = convert(
        document,
        replay(document, ["Livestream Tickets: $10", "Register for Free", "Free parking", "Tickets from $20 to $100"]),
    ).tickets[0]
    assert ticket.price is None


def test_free_livestream_does_not_make_physical_show_free():
    _, document = audit("future16055")
    document["offers"] = [document["offers"][1]]
    assert convert(document).tickets[0].price is None


def test_marketing_sold_out_audiences_does_not_override_instock():
    _, document = audit("future16055")
    ticket = convert(
        document, replay(document, ["ASSSSCAT has played to sold out audiences across the country."])
    ).tickets[0]
    assert (ticket.price, ticket.sold_out) == (0, False)


@pytest.mark.parametrize("offers", ["bad", [None], [{"name": "Table for four", "price": 20}], []])
def test_malformed_or_package_offers_are_not_individual_admission(offers):
    _, document = audit("future8823")
    document["offers"] = offers
    assert convert(document).tickets[0].price is None


async def test_pipeline_enriches_listed_event_and_retains_event_when_detail_fetch_fails():
    _, document = audit("future8834")
    event, club = source_event(document)
    listing = f"""<article class="wpgb-card la-franklin">
      <div class="event-post-date">{event.date_text}</div>
      <h3 class="ucb-event-post-title"><a href="{event.show_page_url}">{event.title}</a></h3>
      <div class="ucb-event-post-location"><span class="wpgb-block-term">{event.location_name}</span></div>
      </article>"""
    scraper = UCBScraper(club)
    scraper.fetch_html = AsyncMock(side_effect=[listing, replay(document)])
    page = await scraper.get_data("https://ucbcomedy.com/shows/")
    assert page.event_list[0].to_show(club, enhanced=False).tickets[0].price == 0
    assert scraper.fetch_html.call_args.kwargs["skip_js_fallback"] is True
    scraper.fetch_html = AsyncMock(side_effect=[listing, RuntimeError("blocked")])
    page = await scraper.get_data("https://ucbcomedy.com/shows/")
    assert len(page.event_list) == 1
    assert page.event_list[0].to_show(club, enhanced=False).tickets[0].price is None
