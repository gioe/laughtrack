"""
Unit tests for RodneyEventExtractor._extract_event_from_html_page and _parse_show_date.
"""

from datetime import datetime

import pytest

from laughtrack.scrapers.implementations.venues.rodneys.extractor import RodneyEventExtractor


SOURCE_URL = "https://rodneysnewyorkcomedyclub.com/shows/test-show"


def _page_html(title: str = "Test Show", date_str: str = "Sat | March 21, 2026 - 8:30PM", ticket_url: str = "https://parde.app/attending/events/abc123") -> str:
    """Build minimal show-page HTML matching the current rodneysnewyorkcomedyclub.com structure."""
    ticket_link = f'<a href="{ticket_url}"><button>CHECKOUT</button></a>' if ticket_url else ""
    return f"""<html><body>
<h4 class="padding10 align-center no-margin uppercase">{title}</h4>
<h4 class="fg-red text-bold">Ticket Price</h4>
<h4 class="no-margin-bottom">GENERAL: $</h4>
{ticket_link}
<h4 class="no-margin text-bold mb-5">{date_str}</h4>
<h4 class="no-margin text-bold">{title}</h4>
</body></html>"""


# ---------------------------------------------------------------------------
# _parse_show_date
# ---------------------------------------------------------------------------


class TestParseShowDate:
    def test_canonical_format_with_minutes(self):
        dt = RodneyEventExtractor._parse_show_date("Sat | March 21, 2026 - 8:30PM")
        assert dt == datetime(2026, 3, 21, 20, 30)

    def test_no_minutes(self):
        dt = RodneyEventExtractor._parse_show_date("Sun | March 22, 2026 - 6 PM")
        assert dt == datetime(2026, 3, 22, 18, 0)

    def test_zero_padded_hour(self):
        dt = RodneyEventExtractor._parse_show_date("Mon | March 23, 2026 - 07:00PM")
        assert dt == datetime(2026, 3, 23, 19, 0)

    def test_noon(self):
        dt = RodneyEventExtractor._parse_show_date("Fri | April 1, 2026 - 12:00PM")
        assert dt == datetime(2026, 4, 1, 12, 0)

    def test_midnight(self):
        dt = RodneyEventExtractor._parse_show_date("Sat | April 2, 2026 - 12:00AM")
        assert dt == datetime(2026, 4, 2, 0, 0)

    def test_am_time(self):
        dt = RodneyEventExtractor._parse_show_date("Sun | April 3, 2026 - 11:30AM")
        assert dt == datetime(2026, 4, 3, 11, 30)

    def test_missing_pipe_returns_none(self):
        assert RodneyEventExtractor._parse_show_date("March 21, 2026 - 8:30PM") is None

    def test_empty_string_returns_none(self):
        assert RodneyEventExtractor._parse_show_date("") is None

    def test_garbage_returns_none(self):
        assert RodneyEventExtractor._parse_show_date("not a date at all") is None


# ---------------------------------------------------------------------------
# _extract_event_from_html_page
# ---------------------------------------------------------------------------


class TestExtractEventFromHtmlPage:
    def test_canonical_page(self):
        html = _page_html("Dan Naturman and Friends", "Sat | March 21, 2026 - 8:30PM")
        events = RodneyEventExtractor._extract_event_from_html_page(html, SOURCE_URL)
        assert len(events) == 1
        e = events[0]
        assert e.title == "Dan Naturman and Friends"
        assert e.date_time == datetime(2026, 3, 21, 20, 30)
        assert e.source_url == SOURCE_URL
        assert e.source_type == "html"

    def test_ticket_url_captured(self):
        html = _page_html(ticket_url="https://parde.app/attending/events/abc123")
        events = RodneyEventExtractor._extract_event_from_html_page(html, SOURCE_URL)
        assert events[0].ticket_info == {"purchase_url": "https://parde.app/attending/events/abc123"}

    def test_no_parde_link_yields_no_ticket_info(self):
        html = _page_html(ticket_url="")
        events = RodneyEventExtractor._extract_event_from_html_page(html, SOURCE_URL)
        assert len(events) == 1
        assert events[0].ticket_info is None

    def test_non_https_parde_link_ignored(self):
        """A parde.app link that doesn't start with https:// is not captured."""
        html = _page_html(ticket_url="http://parde.app/attending/events/abc123")
        events = RodneyEventExtractor._extract_event_from_html_page(html, SOURCE_URL)
        assert len(events) == 1
        assert events[0].ticket_info is None

    def test_missing_title_returns_empty(self):
        html = """<html><body>
<h4 class="fg-red text-bold">Ticket Price</h4>
<h4 class="no-margin text-bold mb-5">Sat | March 21, 2026 - 8:30PM</h4>
</body></html>"""
        events = RodneyEventExtractor._extract_event_from_html_page(html, SOURCE_URL)
        assert events == []

    def test_missing_date_returns_empty(self):
        html = """<html><body>
<h4 class="padding10 align-center no-margin uppercase">Test Show</h4>
</body></html>"""
        events = RodneyEventExtractor._extract_event_from_html_page(html, SOURCE_URL)
        assert events == []

    def test_unparseable_date_returns_empty(self):
        html = _page_html(date_str="Sat | not a real date at all")
        events = RodneyEventExtractor._extract_event_from_html_page(html, SOURCE_URL)
        assert events == []

    def test_empty_html_returns_empty(self):
        events = RodneyEventExtractor._extract_event_from_html_page("<html></html>", SOURCE_URL)
        assert events == []
