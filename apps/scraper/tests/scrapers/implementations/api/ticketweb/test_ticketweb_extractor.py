"""Unit tests for TicketWebExtractor.

Covers all four static extraction methods:
- extract_calendar_events (JS var all_events parsing)
- extract_html_calendar_events (HTML fallback parsing)
- extract_ticket_info (buy button / sold-out detection)
- extract_next_page_url (pagination)
"""

import importlib.util
from datetime import datetime

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.scrapers.implementations.api.ticketweb.extractor import TicketWebExtractor


# ---------------------------------------------------------------------------
# extract_calendar_events — JS var all_events parsing
# ---------------------------------------------------------------------------


class TestExtractCalendarEvents:
    def test_parses_single_event(self):
        html = """
        <script>
        var all_events = [
            { title: 'Comedy Night', start: new Date('2099-04-15 20:00:00'), url: '/event/comedy-night' }
        ];
        </script>
        """
        events = TicketWebExtractor.extract_calendar_events(html)

        assert len(events) == 1
        assert events[0]["title"] == "Comedy Night"
        assert events[0]["start_date"] == datetime(2099, 4, 15, 20, 0, 0)
        assert events[0]["url"] == "/event/comedy-night"

    def test_parses_multiple_events(self):
        html = """
        <script>
        var all_events = [
            { title: 'Show A', start: new Date('2099-04-15 20:00:00'), url: '/event/show-a' },
            { title: 'Show B', start: new Date('2099-04-22 21:30:00'), url: '/event/show-b' }
        ];
        </script>
        """
        events = TicketWebExtractor.extract_calendar_events(html)

        assert len(events) == 2
        assert events[0]["title"] == "Show A"
        assert events[1]["title"] == "Show B"
        assert events[1]["start_date"] == datetime(2099, 4, 22, 21, 30, 0)

    def test_handles_escaped_quotes_in_title(self):
        html = """
        <script>
        var all_events = [
            { title: 'Mike\\'s Comedy Hour', start: new Date('2099-05-01 19:00:00'), url: '/event/mikes-hour' }
        ];
        </script>
        """
        events = TicketWebExtractor.extract_calendar_events(html)

        assert len(events) == 1
        assert events[0]["title"] == "Mike's Comedy Hour"

    def test_returns_empty_when_no_js_array(self):
        html = "<html><body><p>No calendar here</p></body></html>"
        events = TicketWebExtractor.extract_calendar_events(html)
        assert events == []

    def test_skips_events_missing_required_fields(self):
        html = """
        <script>
        var all_events = [
            { title: 'Good Event', start: new Date('2099-06-01 20:00:00'), url: '/event/good' },
            { title: 'No URL Event', start: new Date('2099-06-02 20:00:00') },
            { start: new Date('2099-06-03 20:00:00'), url: '/event/no-title' }
        ];
        </script>
        """
        events = TicketWebExtractor.extract_calendar_events(html)

        assert len(events) == 1
        assert events[0]["title"] == "Good Event"

    def test_skips_event_with_unparseable_date(self):
        html = """
        <script>
        var all_events = [
            { title: 'Bad Date', start: new Date('not-a-date'), url: '/event/bad' },
            { title: 'Good Date', start: new Date('2099-07-01 20:00:00'), url: '/event/good' }
        ];
        </script>
        """
        events = TicketWebExtractor.extract_calendar_events(html)

        assert len(events) == 1
        assert events[0]["title"] == "Good Date"


# ---------------------------------------------------------------------------
# extract_html_calendar_events — HTML fallback parsing
# ---------------------------------------------------------------------------


class TestExtractHtmlCalendarEvents:
    def _make_event_block(self, name="Comedy Night", date="Jan 1 -",
                          time="8:00 PM", url="/event/comedy"):
        return f"""
        <div class="five columns">
            <div class="tw-name"><a href="{url}">{name}</a></div>
            <span class="tw-event-date">{date}</span>
            <span class="tw-event-time">{time}</span>
        </div>
        """

    def test_parses_single_html_event(self):
        html = "<div>header</div>" + self._make_event_block(
            name="Open Mic", date="Jan 15 -", time="9:00 PM",
            url="/event/open-mic",
        )
        events = TicketWebExtractor.extract_html_calendar_events(html)

        assert len(events) == 1
        assert events[0]["title"] == "Open Mic"
        assert events[0]["url"] == "/event/open-mic"
        assert events[0]["start_date"].month == 1
        assert events[0]["start_date"].day == 15
        assert events[0]["start_date"].hour == 21

    def test_parses_multiple_html_events(self):
        html = (
            "<div>header</div>"
            + self._make_event_block(name="Show A", date="Feb 10 -", time="7:00 PM", url="/a")
            + self._make_event_block(name="Show B", date="Feb 11 -", time="8:00 PM", url="/b")
        )
        events = TicketWebExtractor.extract_html_calendar_events(html)

        assert len(events) == 2
        assert events[0]["title"] == "Show A"
        assert events[1]["title"] == "Show B"

    def test_deduplicates_by_url(self):
        html = (
            "<div>header</div>"
            + self._make_event_block(name="Show A", date="Mar 1 -", time="8:00 PM", url="/same")
            + self._make_event_block(name="Show A (dup)", date="Mar 1 -", time="8:00 PM", url="/same")
        )
        events = TicketWebExtractor.extract_html_calendar_events(html)

        assert len(events) == 1

    def test_strips_show_prefix_from_time(self):
        html = "<div>header</div>" + self._make_event_block(
            name="Late Show", date="Apr 5 -", time="Show: 10:30 PM", url="/late",
        )
        events = TicketWebExtractor.extract_html_calendar_events(html)

        assert len(events) == 1
        assert events[0]["start_date"].hour == 22
        assert events[0]["start_date"].minute == 30

    def test_strips_html_tags_from_name(self):
        html = """
        <div>header</div>
        <div class="five columns">
            <div class="tw-name"><a href="/event/tagged"><strong>Bold Show</strong></a></div>
            <span class="tw-event-date">May 1 -</span>
            <span class="tw-event-time">8:00 PM</span>
        </div>
        """
        events = TicketWebExtractor.extract_html_calendar_events(html)

        assert len(events) == 1
        assert events[0]["title"] == "Bold Show"

    def test_skips_block_missing_name(self):
        html = """
        <div>header</div>
        <div class="five columns">
            <span class="tw-event-date">Jun 1 -</span>
            <span class="tw-event-time">8:00 PM</span>
        </div>
        """
        events = TicketWebExtractor.extract_html_calendar_events(html)
        assert events == []

    def test_skips_block_missing_date(self):
        html = """
        <div>header</div>
        <div class="five columns">
            <div class="tw-name"><a href="/e">Show</a></div>
            <span class="tw-event-time">8:00 PM</span>
        </div>
        """
        events = TicketWebExtractor.extract_html_calendar_events(html)
        assert events == []

    def test_returns_empty_for_no_event_blocks(self):
        html = "<html><body><p>Empty page</p></body></html>"
        events = TicketWebExtractor.extract_html_calendar_events(html)
        assert events == []

    def test_event_without_time_still_parsed(self):
        """Time element is optional — date alone should still parse."""
        html = """
        <div>header</div>
        <div class="five columns">
            <div class="tw-name"><a href="/no-time">Daytime Show</a></div>
            <span class="tw-event-date">Jul 4 -</span>
        </div>
        """
        events = TicketWebExtractor.extract_html_calendar_events(html)

        assert len(events) == 1
        assert events[0]["title"] == "Daytime Show"
        assert events[0]["start_date"].month == 7
        assert events[0]["start_date"].day == 4


# ---------------------------------------------------------------------------
# extract_ticket_info — buy button and sold-out detection
# ---------------------------------------------------------------------------


class TestExtractTicketInfo:
    def test_extracts_onsale_buy_button(self):
        html = """
        <a href="https://www.ticketweb.com/event/comedy-night-abc123"
           class="tw-buy-tix-btn tw_onsale">Buy Tickets</a>
        """
        ticket_url, sold_out = TicketWebExtractor.extract_ticket_info(html)

        assert ticket_url == "https://www.ticketweb.com/event/comedy-night-abc123"
        assert sold_out is False

    def test_detects_sold_out_status(self):
        html = """
        <a href="https://www.ticketweb.com/event/sold-show-xyz789"
           class="tw-buy-tix-btn tw_ticketssold">Sold Out</a>
        """
        ticket_url, sold_out = TicketWebExtractor.extract_ticket_info(html)

        assert ticket_url == "https://www.ticketweb.com/event/sold-show-xyz789"
        assert sold_out is True

    def test_falls_back_to_tw_link_pattern(self):
        """When no buy button exists, falls back to broader tw_ link pattern."""
        html = """
        <a href="https://www.ticketweb.com/event/fallback-show-111"
           class="tw_onsale">Get Tickets</a>
        """
        ticket_url, sold_out = TicketWebExtractor.extract_ticket_info(html)

        assert ticket_url == "https://www.ticketweb.com/event/fallback-show-111"
        assert sold_out is False

    def test_fallback_detects_sold_out(self):
        html = """
        <a href="https://www.ticketweb.com/event/fallback-sold-222"
           class="tw_ticketssold">Sold Out</a>
        """
        ticket_url, sold_out = TicketWebExtractor.extract_ticket_info(html)

        assert ticket_url == "https://www.ticketweb.com/event/fallback-sold-222"
        assert sold_out is True

    def test_returns_none_when_no_ticket_link(self):
        html = "<html><body><p>No ticket links here</p></body></html>"
        ticket_url, sold_out = TicketWebExtractor.extract_ticket_info(html)

        assert ticket_url is None
        assert sold_out is False

    def test_prefers_buy_button_over_fallback(self):
        """When both patterns match, the buy button should be returned."""
        html = """
        <a href="https://www.ticketweb.com/event/buy-btn-aaa"
           class="tw-buy-tix-btn tw_onsale">Buy Tickets</a>
        <a href="https://www.ticketweb.com/event/fallback-bbb"
           class="tw_onsale">View Event</a>
        """
        ticket_url, sold_out = TicketWebExtractor.extract_ticket_info(html)

        assert ticket_url == "https://www.ticketweb.com/event/buy-btn-aaa"


# ---------------------------------------------------------------------------
# extract_next_page_url — pagination
# ---------------------------------------------------------------------------


class TestExtractNextPageUrl:
    def test_extracts_next_page_link(self):
        html = """
        <nav>
            <a class="prev" href="/events?page=1">Previous</a>
            <a class="next" href="/events?page=3">Next</a>
        </nav>
        """
        url = TicketWebExtractor.extract_next_page_url(html)
        assert url == "/events?page=3"

    def test_returns_none_when_no_next_link(self):
        html = """
        <nav>
            <a class="prev" href="/events?page=1">Previous</a>
        </nav>
        """
        url = TicketWebExtractor.extract_next_page_url(html)
        assert url is None

    def test_matches_next_class_with_additional_classes(self):
        html = """
        <a class="pagination-link next disabled" href="/events?page=4">Next</a>
        """
        url = TicketWebExtractor.extract_next_page_url(html)
        assert url == "/events?page=4"

    def test_returns_none_for_empty_html(self):
        url = TicketWebExtractor.extract_next_page_url("")
        assert url is None
