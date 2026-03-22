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
