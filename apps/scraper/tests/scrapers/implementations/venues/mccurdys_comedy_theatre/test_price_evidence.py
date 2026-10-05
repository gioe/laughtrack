"""McCurdys admission prices must stay bound to their performance row."""

from pathlib import Path
from datetime import timezone

import pytest
import time_machine

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.mccurdys_comedy_theatre.extractor import McCurdysExtractor

AUDIT = Path(__file__).resolve().parents[5] / "docs/audits/2026-09-27-price-extraction/venues"


def club():
    return Club(
        id=1,
        name="McCurdys",
        address="",
        website="https://www.mccurdyscomedy.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


@pytest.mark.parametrize("i,ticket_id,hour,minute", [(0, "53957625", 0, 0), (1, "55715949", 21, 30)])
def test_retained_ticket_price_survives_extraction_and_show_conversion(i, ticket_id, hour, minute):
    content = (AUDIT / f"mccurdys-detail-{i}.html").read_text()
    events = McCurdysExtractor.extract_events(content)
    assert len(events) == 1
    with time_machine.travel("2026-09-27T12:00:00Z", tick=False):
        show = events[0].to_show(club())
    assert show.tickets[0].purchase_url.endswith("/" + ticket_id)
    assert show.tickets[0].price == 26
    utc_date = show.date.astimezone(timezone.utc)
    assert utc_date.hour == hour and utc_date.minute == minute


def row(ticket_id="123", day="27", price=""):
    return (
        f"<li><p>Sunday, September {day} at 5:30 PM</p>"
        f'<a href="/shows/buy.cfm?timTicketID={ticket_id}">BUY</a>{price}</li>'
    )


def page(rows=None, desktop="Tickets $26", mobile="Tickets $26", extra=""):
    return (
        f'<div class="content vevent"><h1 class="summary">Test</h1>'
        f'<div class="col-md-3 hidden-xs pull-right text-right"><em>{desktop}</em></div>'
        f'<div class="col-md-3 visible-xs"><em>{mobile}</em></div>'
        f'<div class="upcoming-shows-sidebar"><ul>{row() if rows is None else rows}</ul></div>'
        f"{extra}</div>"
    )


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Tickets $0",
        "Tickets $-26",
        "Tickets TBD",
        "Tickets Free",
        "Tickets CAD $26",
        "Tickets €26",
        "Tickets $26–$40",
        "Tickets $26/$40",
        "Tickets GA $26 VIP $40",
        "Tickets $26 plus $5 fee",
        "Tickets $1000001",
    ],
)
def test_absent_invalid_variable_or_non_usd_prices_stay_unknown(text):
    e = McCurdysExtractor.extract_events(page(desktop=text, mobile=text))[0]
    assert e.ticket_price is None
    if text:
        assert e.price_text == text


def test_conflicting_responsive_prices_remain_unknown():
    e = McCurdysExtractor.extract_events(page(mobile="Tickets $35"))[0]
    assert e.ticket_price is None and "$26" in e.price_text and "$35" in e.price_text


def test_page_price_does_not_fan_out_across_dates():
    events = McCurdysExtractor.extract_events(page(rows=row() + row("456", "28")))
    assert len(events) == 2
    assert all(e.ticket_price is None and not e.price_text for e in events)


def test_row_price_belongs_only_to_its_ticket_and_date():
    events = McCurdysExtractor.extract_events(page(rows=row(price="<em>Tickets $35</em>") + row("456", "28")))
    assert [(e.ticket_url.rsplit("/", 1)[-1], e.ticket_price) for e in events] == [("123", 35), ("456", None)]
    assert events[0].date_str == "Sunday, September 27 at 5:30 PM"
    assert events[1].date_str == "Sunday, September 28 at 5:30 PM"


def test_row_variable_price_overrides_single_header_amount():
    e = McCurdysExtractor.extract_events(page(rows=row(price="<em>Tickets $26-$40</em>")))[0]
    assert e.ticket_price is None and e.price_text == "Tickets $26-$40"
    with time_machine.travel("2026-09-27T12:00:00Z", tick=False):
        t = e.to_show(club()).tickets[0]
    assert t.price is None and "$26-$40" in t.type


def test_description_fees_food_and_unrelated_event_prices_do_not_leak():
    unrelated = page(rows=row("999"), desktop="Tickets $1", mobile="Tickets $1")
    content = page(
        desktop="", mobile="", extra='<p class="description">Tickets $99; $2 fee; 18% gratuity</p>' + unrelated
    )
    events = McCurdysExtractor.extract_events(content)
    assert len(events) == 1 and events[0].ticket_url.endswith("/123") and events[0].ticket_price is None


def test_incomplete_row_cannot_borrow_next_rows_buy_link():
    missing = "<li><p>Sunday, September 27 at 4:00 PM</p></li>"
    events = McCurdysExtractor.extract_events(page(rows=missing + row("456", "28")))
    assert len(events) == 1 and events[0].ticket_url.endswith("/456")
    assert events[0].date_str == "Sunday, September 28 at 5:30 PM"
    assert events[0].ticket_price is None


def test_conflicting_links_in_one_row_are_not_a_performance():
    content = page(rows=row().replace("</li>", '<a href="/shows/buy.cfm?timTicketID=456">BUY</a></li>'))
    assert McCurdysExtractor.extract_events(content) == []


def test_missing_price_still_yields_unknown_ticket():
    e = McCurdysExtractor.extract_events(page(desktop="", mobile=""))[0]
    with time_machine.travel("2026-09-27T12:00:00Z", tick=False):
        show = e.to_show(club())
    assert len(show.tickets) == 1 and show.tickets[0].price is None


def test_current_native_page_retains_price_without_etix_request():
    # Minimal equivalent of the live October 7 venue row; no checkout fixtures.
    content = page(rows=row("85920037").replace("Sunday, September 27 at 5:30 PM", "Wednesday, October 07 at 7:00 PM"))
    e = McCurdysExtractor.extract_events(content)[0]
    with time_machine.travel("2026-10-05T12:00:00Z", tick=False):
        show = e.to_show(club())
    assert show.tickets[0].price == 26 and show.tickets[0].purchase_url.endswith("/85920037")
    assert "venue advertised" in show.tickets[0].type
