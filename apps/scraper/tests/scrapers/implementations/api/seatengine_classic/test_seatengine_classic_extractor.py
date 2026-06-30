"""Unit tests for SeatEngineClassicExtractor."""

import json

import pytest

from laughtrack.scrapers.implementations.api.seatengine_classic.extractor import (
    SeatEngineClassicExtractor,
)

BASE_URL = "https://dcimprov-com.seatengine.com"


def _make_json_ld_html(events: list) -> str:
    place = {
        "@context": "http://schema.org",
        "@type": "Place",
        "name": "Test Venue",
        "Events": events,
    }
    return f'<html><head><script type="application/ld+json">{json.dumps(place)}</script></head><body></body></html>'


def _make_event(name: str, start_date: str, url: str) -> dict:
    return {
        "@context": "http://schema.org",
        "@type": "Event",
        "name": name,
        "startDate": start_date,
        "url": url,
    }


class TestJsonLdFallback:
    """JSON-LD extraction used when no event-list-item HTML divs are present."""

    def test_extracts_shows_from_json_ld(self):
        event = _make_event("Sindhu Vee: Swanky", "2026-03-22T19:45:00Z", f"{BASE_URL}/shows/349867")
        html = _make_json_ld_html([event])
        shows = SeatEngineClassicExtractor.extract_shows(html, BASE_URL)
        assert len(shows) == 1
        assert shows[0]["name"] == "Sindhu Vee: Swanky"
        assert shows[0]["date_str"] == "2026-03-22T19:45:00Z"
        assert shows[0]["show_url"] == f"{BASE_URL}/shows/349867"
        assert shows[0]["sold_out"] is False

    def test_extracts_multiple_shows(self):
        events = [
            _make_event("Show A", "2026-04-01T20:00:00Z", f"{BASE_URL}/shows/1"),
            _make_event("Show B", "2026-04-02T20:00:00Z", f"{BASE_URL}/shows/2"),
            _make_event("Show C", "2026-04-03T20:00:00Z", f"{BASE_URL}/shows/3"),
        ]
        html = _make_json_ld_html(events)
        shows = SeatEngineClassicExtractor.extract_shows(html, BASE_URL)
        assert len(shows) == 3
        assert [s["name"] for s in shows] == ["Show A", "Show B", "Show C"]

    def test_empty_events_array_returns_no_shows(self):
        html = _make_json_ld_html([])
        shows = SeatEngineClassicExtractor.extract_shows(html, BASE_URL)
        assert shows == []

    def test_skips_events_missing_name_or_date(self):
        events = [
            {"@type": "Event", "name": "No Date"},
            {"@type": "Event", "startDate": "2026-04-01T20:00:00Z"},  # no name
            _make_event("Valid Show", "2026-04-02T20:00:00Z", f"{BASE_URL}/shows/99"),
        ]
        html = _make_json_ld_html(events)
        shows = SeatEngineClassicExtractor.extract_shows(html, BASE_URL)
        assert len(shows) == 1
        assert shows[0]["name"] == "Valid Show"

class TestMultiShowtimeLayout1:
    """Layout 1 renders one event-times-group div per date.

    A multi-night engagement (e.g. Tacoma Comedy Club /events/137366, a 3-night
    Rick Glassman run with 5 distinct showtimes) must yield one show per distinct
    showtime. Regression for TASK-3488, where .find() captured only the first
    group and dropped the other 4 nights.
    """

    # Mirrors the live Tacoma listing markup: 3 date groups (Thu/Fri/Sat),
    # with Fri and Sat carrying two showtimes each → 5 total. The Sat 8:45 PM
    # slot is sold out to assert per-showtime sold_out is preserved.
    _MULTI_NIGHT_LISTING = """
    <html><body>
    <div class="event-list-item">
      <h3 class="el-header"><a href="/events/137366">Rick Glassman</a></h3>
      <div class="el-showtimes">
        <div class="event-times-group">
          <h6 class="event-date align-right">Thu, Oct 15, 2026</h6>
          <div class="event-list-button-group"><div class="event-divider">
            <a class="event-btn-inline" href="/shows/372794">7:00 PM</a>
          </div></div>
        </div>
        <div class="event-times-group">
          <h6 class="event-date align-right">Fri, Oct 16, 2026</h6>
          <div class="event-list-button-group"><div class="event-divider">
            <a class="event-btn-inline" href="/shows/372795">7:00 PM</a>
            <a class="event-btn-inline" href="/shows/372797">9:45 PM</a>
          </div></div>
        </div>
        <div class="event-times-group">
          <h6 class="event-date align-right">Sat, Oct 17, 2026</h6>
          <div class="event-list-button-group"><div class="event-divider">
            <a class="event-btn-inline" href="/shows/372796">6:00 PM</a>
          </div></div>
          <span class="event-btns">
            <span class="event-btn-soldout">SOLD OUT</span>
            <span class="event-btn-inline inactive">8:45 PM</span>
          </span>
        </div>
      </div>
    </div>
    </body></html>
    """

    def test_captures_every_showtime_across_date_groups(self):
        shows = SeatEngineClassicExtractor.extract_shows(
            self._MULTI_NIGHT_LISTING, BASE_URL
        )
        # All 5 distinct showtimes, one show each (not just the first night).
        urls = [s["show_url"] for s in shows]
        assert urls == [
            f"{BASE_URL}/shows/372794",
            f"{BASE_URL}/shows/372795",
            f"{BASE_URL}/shows/372797",
            f"{BASE_URL}/shows/372796",
            None,  # sold-out Sat 8:45 PM has no buy link
        ]
        assert all(s["name"] == "Rick Glassman" for s in shows)

    def test_per_night_dates_are_distinct(self):
        shows = SeatEngineClassicExtractor.extract_shows(
            self._MULTI_NIGHT_LISTING, BASE_URL
        )
        assert [s["date_str"] for s in shows] == [
            "Thu, Oct 15, 2026 7:00 PM",
            "Fri, Oct 16, 2026 7:00 PM",
            "Fri, Oct 16, 2026 9:45 PM",
            "Sat, Oct 17, 2026 6:00 PM",
            "Sat, Oct 17, 2026 8:45 PM",
        ]

    def test_per_showtime_sold_out_preserved(self):
        shows = SeatEngineClassicExtractor.extract_shows(
            self._MULTI_NIGHT_LISTING, BASE_URL
        )
        sold_out = [s for s in shows if s["sold_out"]]
        assert len(sold_out) == 1
        assert sold_out[0]["date_str"] == "Sat, Oct 17, 2026 8:45 PM"
        assert sold_out[0]["show_url"] is None
        # Every other showtime stays available.
        assert sum(1 for s in shows if not s["sold_out"]) == 4

    def test_single_group_layout1_unaffected(self):
        """A single date group still yields exactly its showtimes (no regression)."""
        html = """
        <html><body>
        <div class="event-list-item">
          <h3 class="el-header"><a href="/events/1">One Night</a></h3>
          <div class="event-times-group">
            <h6 class="event-date align-right">Sun, Mar 22, 2026</h6>
            <a class="event-btn-inline" href="/shows/363997">3:00 PM</a>
            <a class="event-btn-inline" href="/shows/363998">8:00 PM</a>
          </div>
        </div>
        </body></html>
        """
        shows = SeatEngineClassicExtractor.extract_shows(html, BASE_URL)
        assert [s["show_url"] for s in shows] == [
            f"{BASE_URL}/shows/363997",
            f"{BASE_URL}/shows/363998",
        ]


class TestJsonLdFallbackPrecedence:

    def test_html_extraction_takes_precedence_over_json_ld(self):
        """When event-list-item divs are present, JSON-LD should NOT be used."""
        html_with_items = """
        <html><body>
        <div class="event-list-item">
            <h3 class="el-header"><a href="/events/1">HTML Show</a></h3>
            <h6 class="event-date">Thu Mar 26 2026, 7:30 PM</h6>
            <a class="btn btn-primary" href="/shows/1">Buy Tickets</a>
        </div>
        <script type="application/ld+json">{"@type":"Place","Events":[{"@type":"Event","name":"JSON Show","startDate":"2026-04-01T20:00:00Z","url":"/shows/2"}]}</script>
        </body></html>
        """
        shows = SeatEngineClassicExtractor.extract_shows(html_with_items, BASE_URL)
        assert len(shows) == 1
        assert shows[0]["name"] == "HTML Show"
