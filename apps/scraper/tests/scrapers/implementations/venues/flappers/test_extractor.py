"""
Unit tests for FlappersEventExtractor — calendar HTML parsing and detail page extraction.
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.event.flappers import FlappersEvent, FlappersTicketTier
from laughtrack.scrapers.implementations.venues.flappers.extractor import (
    FlappersEventExtractor,
    ShowDetails,
    _normalize_room,
)

CALENDAR_URL = "https://www.flapperscomedy.com/site/shows.php?month=6&year=2099"
TZ = "America/Los_Angeles"


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _form_html(
    event_id: str = "1234",
    title: str = "Friday Headliner",
    time: str = "8:00 PM",
    data_type: str = "main room",
) -> str:
    return (
        f'<form><input name="event_id" value="{event_id}">'
        f'<button class="event-btn" data-type="{data_type}">'
        f"<b>{title}</b>\n{time}</button></form>"
    )


def _day_html(day: int, forms: list[str]) -> str:
    forms_str = "\n".join(forms)
    return f"<td><strong>{day}</strong>{forms_str}</td>"


def _calendar_html(days: list[str]) -> str:
    return f"<html><body><table>{''.join(days)}</table></body></html>"


def _detail_html(
    lineup: list[str] | None = None,
    tiers: list[dict] | None = None,
    description: str = "",
) -> str:
    lineup_html = ""
    if lineup:
        links = "".join(f'<a href="#">{n}</a>' for n in lineup)
        lineup_html = f'<div class="also-starring">{links}</div>'

    tiers_html = ""
    if tiers:
        lis = ""
        for t in tiers:
            sold_class = "ticket-card is-soldout" if t.get("sold_out") else "ticket-card"
            remaining = t.get("remaining", "")
            desc = t.get("desc", "General Admission")
            price = t.get("price", "0.00")
            lis += (
                f'<li><label class="{sold_class}">'
                f'<input class="ticket-radio" data-left="{remaining}" data-description="{desc}">'
                f'<div class="ticket-price">${price}</div>'
                f"</label></li>"
            )
        tiers_html = f'<ul id="ticket_choices">{lis}</ul>'

    desc_html = ""
    if description:
        desc_html = f'<span id="showDesc" data-full="{description}">truncated...</span>'

    return f"<html><body>{lineup_html}{tiers_html}{desc_html}</body></html>"


# ---------------------------------------------------------------------------
# extract_shows — calendar parsing
# ---------------------------------------------------------------------------


class TestExtractShows:
    def test_single_show(self):
        html = _calendar_html([_day_html(15, [_form_html()])])
        events = FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ)

        assert len(events) == 1
        e = events[0]
        assert e.title == "Friday Headliner"
        assert e.event_id == "1234"
        assert e.year == 2099
        assert e.month == 6
        assert e.day == 15
        assert e.time_str == "8:00 PM"
        assert e.room == "Main Room"
        assert e.timezone == TZ

    def test_multiple_shows_same_day(self):
        forms = [
            _form_html(event_id="100", title="Early Show", time="7 PM"),
            _form_html(event_id="101", title="Late Show", time="10:00 PM"),
        ]
        html = _calendar_html([_day_html(20, forms)])
        events = FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ)

        assert len(events) == 2
        assert events[0].title == "Early Show"
        assert events[0].time_str == "7 PM"
        assert events[1].title == "Late Show"
        assert events[1].time_str == "10:00 PM"

    def test_multiple_days(self):
        html = _calendar_html([
            _day_html(1, [_form_html(event_id="10", title="Show A")]),
            _day_html(2, [_form_html(event_id="11", title="Show B")]),
        ])
        events = FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ)

        assert len(events) == 2
        assert events[0].day == 1
        assert events[1].day == 2

    def test_empty_html_returns_empty(self):
        assert FlappersEventExtractor.extract_shows("", CALENDAR_URL, TZ) == []

    def test_no_forms_in_day_returns_empty(self):
        html = _calendar_html(["<td><strong>5</strong></td>"])
        events = FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ)
        assert events == []

    def test_missing_event_id_skipped(self):
        bad_form = '<form><button class="event-btn" data-type="main room"><b>No ID</b>\n8:00 PM</button></form>'
        html = _calendar_html([_day_html(10, [bad_form])])
        assert FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ) == []

    def test_missing_title_skipped(self):
        bad_form = (
            '<form><input name="event_id" value="999">'
            '<button class="event-btn"><b></b>\n8:00 PM</button></form>'
        )
        html = _calendar_html([_day_html(10, [bad_form])])
        assert FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ) == []

    def test_missing_time_skipped(self):
        bad_form = (
            '<form><input name="event_id" value="999">'
            '<button class="event-btn" data-type="bar"><b>No Time Show</b></button></form>'
        )
        html = _calendar_html([_day_html(10, [bad_form])])
        assert FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ) == []

    def test_room_normalization_yoo_hoo(self):
        html = _calendar_html([_day_html(5, [_form_html(data_type="yoo hoo room")])])
        events = FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ)
        assert events[0].room == "Yoo Hoo Room"

    def test_room_normalization_bar(self):
        html = _calendar_html([_day_html(5, [_form_html(data_type="bar")])])
        events = FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ)
        assert events[0].room == "Bar"

    def test_unknown_room_passthrough(self):
        html = _calendar_html([_day_html(5, [_form_html(data_type="rooftop")])])
        events = FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ)
        assert events[0].room == "rooftop"

    def test_no_url_defaults_month_year_to_zero(self):
        html = _calendar_html([_day_html(1, [_form_html()])])
        events = FlappersEventExtractor.extract_shows(html, "", TZ)
        assert events[0].year == 0
        assert events[0].month == 0

    def test_am_time_parsed(self):
        html = _calendar_html([_day_html(1, [_form_html(time="11:30 AM")])])
        events = FlappersEventExtractor.extract_shows(html, CALENDAR_URL, TZ)
        assert events[0].time_str == "11:30 AM"


# ---------------------------------------------------------------------------
# extract_show_details — detail page parsing
# ---------------------------------------------------------------------------


class TestExtractShowDetails:
    def test_full_detail_page(self):
        html = _detail_html(
            lineup=["John Doe", "Jane Smith"],
            tiers=[
                {"price": "25.00", "desc": "General Admission", "remaining": "50"},
                {"price": "40.00", "desc": "VIP", "remaining": "10"},
            ],
            description="A hilarious night of comedy.",
        )
        details = FlappersEventExtractor.extract_show_details(html)

        assert details is not None
        assert details.lineup_names == ["John Doe", "Jane Smith"]
        assert len(details.ticket_tiers) == 2
        assert details.ticket_tiers[0].price == 25.0
        assert details.ticket_tiers[0].ticket_type == "General Admission"
        assert details.ticket_tiers[0].remaining == 50
        assert details.ticket_tiers[1].price == 40.0
        assert details.ticket_tiers[1].ticket_type == "VIP"
        assert details.description == "A hilarious night of comedy."

    def test_empty_html_returns_none(self):
        assert FlappersEventExtractor.extract_show_details("") is None

    def test_no_lineup_section(self):
        html = _detail_html(lineup=None, tiers=[{"price": "20.00"}])
        details = FlappersEventExtractor.extract_show_details(html)
        assert details.lineup_names == []

    def test_no_ticket_tiers(self):
        html = _detail_html(lineup=["Comedian A"])
        details = FlappersEventExtractor.extract_show_details(html)
        assert details.ticket_tiers == []

    def test_no_description(self):
        html = _detail_html(lineup=["Comedian A"])
        details = FlappersEventExtractor.extract_show_details(html)
        assert details.description is None

    def test_sold_out_tier(self):
        html = _detail_html(tiers=[{"price": "25.00", "sold_out": True, "remaining": "0"}])
        details = FlappersEventExtractor.extract_show_details(html)
        assert details.ticket_tiers[0].sold_out is True
        assert details.ticket_tiers[0].remaining == 0

    def test_missing_price_defaults_to_zero(self):
        html = """<html><body>
        <ul id="ticket_choices"><li>
            <label class="ticket-card">
                <input class="ticket-radio" data-left="10" data-description="Standing Room">
                <div class="ticket-price">Free</div>
            </label>
        </li></ul></body></html>"""
        details = FlappersEventExtractor.extract_show_details(html)
        assert details.ticket_tiers[0].price == 0.0
        assert details.ticket_tiers[0].ticket_type == "Standing Room"

    def test_missing_data_description_defaults_general_admission(self):
        html = """<html><body>
        <ul id="ticket_choices"><li>
            <label class="ticket-card">
                <input class="ticket-radio" data-left="5">
                <div class="ticket-price">$15.00</div>
            </label>
        </li></ul></body></html>"""
        details = FlappersEventExtractor.extract_show_details(html)
        assert details.ticket_tiers[0].ticket_type == "General Admission"

    def test_minimal_html_returns_empty_details(self):
        details = FlappersEventExtractor.extract_show_details("<html><body></body></html>")
        assert details is not None
        assert details.lineup_names == []
        assert details.ticket_tiers == []
        assert details.description is None


# ---------------------------------------------------------------------------
# _normalize_room
# ---------------------------------------------------------------------------


class TestNormalizeRoom:
    def test_main_room_variants(self):
        assert _normalize_room("main room") == "Main Room"
        assert _normalize_room("mainroom") == "Main Room"
        assert _normalize_room("  Main Room  ") == "Main Room"

    def test_yoo_hoo(self):
        assert _normalize_room("yoo hoo room") == "Yoo Hoo Room"

    def test_bar(self):
        assert _normalize_room("bar") == "Bar"

    def test_patio(self):
        assert _normalize_room("patio") == "Patio"

    def test_unknown_passthrough(self):
        assert _normalize_room("basement") == "basement"
