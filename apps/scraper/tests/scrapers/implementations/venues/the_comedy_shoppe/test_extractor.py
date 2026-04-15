"""
Unit tests for ShowSlingerExtractor (event card parsing, date formats,
price extraction, sold-out detection, and multi-showtime expansion).
"""

from datetime import datetime
from unittest.mock import patch

from laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor import (
    ShowSlingerExtractor,
)


# ---------------------------------------------------------------------------
# Helper: build minimal ShowSlinger widget HTML
# ---------------------------------------------------------------------------

def _event_card(
    title: str = "Test Show",
    ticket_id: str = "12345",
    time_spans: str = "",
    date_badge: str = "",
    price_html: str = "",
    sold_out: bool = False,
    image_src: str | None = "https://img.example.com/show.jpg",
) -> str:
    """Build a single ShowSlinger event card."""
    img_html = f'<img class="grid-img" src="{image_src}"/>' if image_src else ""
    sold_out_html = '<span class="badge">Sold Out</span>' if sold_out else ""
    badge_html = f'<div class="widget-date-month">{date_badge}</div>' if date_badge else ""
    return f"""
    <div class="signUP-admin">
      {img_html}
      <h4 class="widget-name">{title}</h4>
      {badge_html}
      {time_spans}
      {price_html}
      {sold_out_html}
      <a class="mrk_ticket_event_url" href="/ticket_payment/{ticket_id}/checkout_ticket">Buy</a>
    </div>
    """


def _time_span(text: str) -> str:
    return f'<span class="widget-time">{text}</span>'


def _price_el(text: str) -> str:
    return f'<span class="widget-price">{text}</span>'


def _widget_page(cards_html: str) -> str:
    return f"<html><body>{cards_html}</body></html>"


# ---------------------------------------------------------------------------
# extract_events — basic extraction
# ---------------------------------------------------------------------------

class TestExtractEventsBasic:
    def test_extracts_single_event(self):
        html = _widget_page(
            _event_card(
                title="Friday Funny",
                ticket_id="100",
                time_spans=_time_span("Sat, May 2, 3:00 pm"),
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert len(events) == 1
        assert events[0].name == "Friday Funny"
        assert events[0].ticket_id == "100"
        assert events[0].ticket_url == "https://app.showslinger.com/ticket_payment/100/checkout_ticket"

    def test_extracts_multiple_cards(self):
        html = _widget_page(
            _event_card(title="Show A", ticket_id="1", time_spans=_time_span("Sat, May 2, 3:00 pm"))
            + _event_card(title="Show B", ticket_id="2", time_spans=_time_span("Sat, June 4, 7:00 pm"))
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert len(events) == 2
        assert events[0].name == "Show A"
        assert events[1].name == "Show B"

    def test_empty_html_returns_empty(self):
        events = ShowSlingerExtractor.extract_events("")
        assert events == []

    def test_no_event_cards_returns_empty(self):
        html = "<html><body><p>No events</p></body></html>"
        events = ShowSlingerExtractor.extract_events(html)
        assert events == []

    def test_card_missing_title_skipped(self):
        html = _widget_page("""
        <div class="signUP-admin">
          <span class="widget-time">Sat, May 2, 3:00 pm</span>
          <a class="mrk_ticket_event_url" href="/ticket_payment/99/checkout_ticket">Buy</a>
        </div>
        """)
        events = ShowSlingerExtractor.extract_events(html)
        assert events == []

    def test_card_missing_ticket_link_skipped(self):
        html = _widget_page("""
        <div class="signUP-admin">
          <h4 class="widget-name">No Ticket</h4>
          <span class="widget-time">Sat, May 2, 3:00 pm</span>
        </div>
        """)
        events = ShowSlingerExtractor.extract_events(html)
        assert events == []

    def test_card_invalid_ticket_href_skipped(self):
        html = _widget_page("""
        <div class="signUP-admin">
          <h4 class="widget-name">Bad Link</h4>
          <span class="widget-time">Sat, May 2, 3:00 pm</span>
          <a class="mrk_ticket_event_url" href="/some/other/path">Buy</a>
        </div>
        """)
        events = ShowSlingerExtractor.extract_events(html)
        assert events == []

    def test_card_no_showtimes_skipped(self):
        html = _widget_page(
            _event_card(title="No Times", ticket_id="50", time_spans="")
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events == []

    def test_image_url_extracted(self):
        html = _widget_page(
            _event_card(
                time_spans=_time_span("Sat, May 2, 3:00 pm"),
                image_src="https://cdn.example.com/poster.jpg",
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].image_url == "https://cdn.example.com/poster.jpg"

    def test_no_image_returns_none(self):
        html = _widget_page(
            _event_card(
                time_spans=_time_span("Sat, May 2, 3:00 pm"),
                image_src=None,
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].image_url is None


# ---------------------------------------------------------------------------
# Full-date parsing: "Sat, May 2, 3:00 pm"
# ---------------------------------------------------------------------------

class TestFullDateParsing:
    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_parses_abbreviated_month(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 1)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(time_spans=_time_span("Sat, May 2, 3:00 pm"))
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert len(events) == 1
        assert events[0].date_time == datetime(2026, 5, 2, 15, 0)

    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_parses_full_month_name(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 1)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(time_spans=_time_span("Thu, August 14, 8:00 pm"))
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert len(events) == 1
        assert events[0].date_time == datetime(2026, 8, 14, 20, 0)

    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_parses_uppercase_am_pm(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 1)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(time_spans=_time_span("Fri, Jun 6, 10:30 PM"))
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].date_time == datetime(2026, 6, 6, 22, 30)


# ---------------------------------------------------------------------------
# Time-only parsing with date badge: "7:30 PM" + badge "Apr 27"
# ---------------------------------------------------------------------------

class TestTimeWithBadgeParsing:
    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_parses_time_with_badge(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 1)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(
                time_spans=_time_span("7:30 PM"),
                date_badge="Apr 27",
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert len(events) == 1
        assert events[0].date_time == datetime(2026, 4, 27, 19, 30)

    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_parses_badge_with_full_month(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 1)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(
                time_spans=_time_span("4:00 PM"),
                date_badge="June 14",
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].date_time == datetime(2026, 6, 14, 16, 0)

    def test_time_only_without_badge_skipped(self):
        html = _widget_page(
            _event_card(
                time_spans=_time_span("7:30 PM"),
                date_badge="",
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events == []

    def test_invalid_time_text_skipped(self):
        html = _widget_page(
            _event_card(
                time_spans=_time_span("TBD"),
                date_badge="Apr 27",
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events == []

    def test_invalid_badge_text_skipped(self):
        html = _widget_page(
            _event_card(
                time_spans=_time_span("7:30 PM"),
                date_badge="Coming Soon",
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events == []


# ---------------------------------------------------------------------------
# Year rollover
# ---------------------------------------------------------------------------

class TestYearRollover:
    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_past_date_bumps_to_next_year(self, mock_dt):
        # Pretend "now" is Dec 2026 — a Jan 15 date is >30 days in the past
        mock_dt.now.return_value = datetime(2026, 12, 15)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(time_spans=_time_span("Wed, Jan 15, 8:00 pm"))
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert len(events) == 1
        assert events[0].date_time.year == 2027

    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_recent_past_date_stays_current_year(self, mock_dt):
        # "now" is May 10 — a May 1 date is only 9 days ago (≤30)
        mock_dt.now.return_value = datetime(2026, 5, 10)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(time_spans=_time_span("Fri, May 1, 9:00 pm"))
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].date_time.year == 2026


# ---------------------------------------------------------------------------
# Multi-showtime expansion
# ---------------------------------------------------------------------------

class TestMultiShowtimeExpansion:
    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_multiple_full_date_spans_expand(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 1)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(
                title="Double Header",
                ticket_id="200",
                time_spans=(
                    _time_span("Sat, May 2, 3:00 pm")
                    + _time_span("Sat, May 2, 7:00 pm")
                ),
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert len(events) == 2
        assert events[0].name == "Double Header"
        assert events[1].name == "Double Header"
        assert events[0].date_time == datetime(2026, 5, 2, 15, 0)
        assert events[1].date_time == datetime(2026, 5, 2, 19, 0)
        # Both share the same ticket info
        assert events[0].ticket_id == events[1].ticket_id == "200"

    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_multiple_time_only_spans_with_badge(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 1)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(
                title="Triple Show",
                ticket_id="300",
                time_spans=(
                    _time_span("4:00 PM")
                    + _time_span("7:00 PM")
                    + _time_span("9:30 PM")
                ),
                date_badge="Jun 20",
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert len(events) == 3
        assert events[0].date_time == datetime(2026, 6, 20, 16, 0)
        assert events[1].date_time == datetime(2026, 6, 20, 19, 0)
        assert events[2].date_time == datetime(2026, 6, 20, 21, 30)


# ---------------------------------------------------------------------------
# Price extraction
# ---------------------------------------------------------------------------

class TestPriceExtraction:
    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_extracts_integer_price(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 1)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(
                time_spans=_time_span("Sat, May 2, 3:00 pm"),
                price_html=_price_el("$25"),
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].price == 25.0

    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_extracts_decimal_price(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 1)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(
                time_spans=_time_span("Sat, May 2, 3:00 pm"),
                price_html=_price_el("$54.99"),
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].price == 54.99

    @patch(
        "laughtrack.scrapers.implementations.venues.the_comedy_shoppe.extractor.datetime",
    )
    def test_extracts_price_with_commas(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 1)
        mock_dt.strptime = datetime.strptime
        html = _widget_page(
            _event_card(
                time_spans=_time_span("Sat, May 2, 3:00 pm"),
                price_html=_price_el("$1,200"),
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].price == 1200.0

    def test_no_price_returns_none(self):
        html = _widget_page(
            _event_card(
                time_spans=_time_span("Sat, May 2, 3:00 pm"),
                price_html="",
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].price is None


# ---------------------------------------------------------------------------
# Sold-out detection
# ---------------------------------------------------------------------------

class TestSoldOutDetection:
    def test_sold_out_detected(self):
        html = _widget_page(
            _event_card(
                time_spans=_time_span("Sat, May 2, 3:00 pm"),
                sold_out=True,
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].sold_out is True

    def test_not_sold_out_by_default(self):
        html = _widget_page(
            _event_card(
                time_spans=_time_span("Sat, May 2, 3:00 pm"),
                sold_out=False,
            )
        )
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].sold_out is False

    def test_sold_out_case_insensitive(self):
        html = _widget_page("""
        <div class="signUP-admin">
          <h4 class="widget-name">Show</h4>
          <span class="widget-time">Sat, May 2, 3:00 pm</span>
          <span>SOLD OUT</span>
          <a class="mrk_ticket_event_url" href="/ticket_payment/77/checkout_ticket">Buy</a>
        </div>
        """)
        events = ShowSlingerExtractor.extract_events(html)
        assert events[0].sold_out is True
