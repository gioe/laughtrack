"""
Unit tests for ComedyClubHaugExtractor — RSC payload parsing.
"""

import importlib.util
import json

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.scrapers.implementations.venues.comedy_club_haug.extractor import (
    ComedyClubHaugExtractor,
)


# ---------------------------------------------------------------------------
# RSC payload helpers
# ---------------------------------------------------------------------------


def _make_event_obj(
    id_="123",
    title="Best of Stand-Up",
    slug="best-of-stand-up",
    event_title="Best of Stand-Up",
    event_subtitle="MC Hidde van Gestel",
    event_status="active",
    event_program_start="2026-04-09T18:30:00+00:00",
    event_program_end="2026-04-09T20:30:00+00:00",
    event_ticket_link="https://stager.co/events/best-of-stand-up",
    artists=None,
) -> dict:
    return {
        "id": id_,
        "title": title,
        "url": f"https://comedyclubhaug.com/shows/{slug}",
        "slug": slug,
        "eventTitle": event_title,
        "eventSubtitle": event_subtitle,
        "eventStatus": event_status,
        "eventProgramStart": event_program_start,
        "eventProgramEnd": event_program_end,
        "eventTicketLink": event_ticket_link,
        "artists": artists or [{"title": "Theo Maassen"}, {"title": "Hans Teeuwen"}],
        "eventCategories": [{"title": "Stand-Up"}],
    }


def _rsc_html(events: list[dict]) -> str:
    """Build a minimal RSC payload HTML wrapping a shows array."""
    # Extractor regex expects compact JSON (no spaces) for event detection
    shows_json = json.dumps(events, separators=(",", ":"))
    # The extractor looks for "shows":[{ in the decoded chunk
    payload = f'{{"pageData":{{"shows":{shows_json}}}}}'
    # Encode as RSC push — the extractor decodes the escaped string
    escaped = json.dumps(payload)[1:-1]  # strip outer quotes to get escaped form
    return (
        f'<html><body>'
        f'<script>self.__next_f.push([1,"{escaped}"])</script>'
        f'</body></html>'
    )


def _raw_html(events: list[dict]) -> str:
    """Build HTML with event objects directly in the markup (fallback path)."""
    parts = []
    for evt in events:
        parts.append(json.dumps(evt, separators=(",", ":")))
    return "<html><body>" + "\n".join(parts) + "</body></html>"


# ---------------------------------------------------------------------------
# extract_shows — RSC chunks
# ---------------------------------------------------------------------------


class TestExtractShows:
    def test_single_event(self):
        html = _rsc_html([_make_event_obj()])
        events = ComedyClubHaugExtractor.extract_shows(html)

        assert len(events) == 1
        assert events[0]["eventTitle"] == "Best of Stand-Up"
        assert events[0]["eventStatus"] == "active"

    def test_multiple_events(self):
        html = _rsc_html([
            _make_event_obj(id_="1", title="Show A", slug="show-a", event_title="Show A"),
            _make_event_obj(id_="2", title="Show B", slug="show-b", event_title="Show B"),
        ])
        events = ComedyClubHaugExtractor.extract_shows(html)

        assert len(events) == 2
        titles = {e["eventTitle"] for e in events}
        assert "Show A" in titles
        assert "Show B" in titles

    def test_empty_html_returns_empty(self):
        assert ComedyClubHaugExtractor.extract_shows("") == []

    def test_none_html_returns_empty(self):
        assert ComedyClubHaugExtractor.extract_shows(None) == []

    def test_no_rsc_payload_returns_empty(self):
        html = "<html><body><p>No data here</p></body></html>"
        assert ComedyClubHaugExtractor.extract_shows(html) == []

    def test_artists_array_preserved(self):
        html = _rsc_html([_make_event_obj(
            artists=[{"title": "Alice"}, {"title": "Bob"}],
        )])
        events = ComedyClubHaugExtractor.extract_shows(html)

        assert len(events) == 1
        artist_names = [a["title"] for a in events[0]["artists"]]
        assert "Alice" in artist_names
        assert "Bob" in artist_names

    def test_ticket_link_preserved(self):
        html = _rsc_html([_make_event_obj(
            event_ticket_link="https://stager.co/events/comedy-night",
        )])
        events = ComedyClubHaugExtractor.extract_shows(html)

        assert events[0]["eventTicketLink"] == "https://stager.co/events/comedy-night"


# ---------------------------------------------------------------------------
# _extract_from_raw_html — fallback
# ---------------------------------------------------------------------------


class TestExtractFromRawHtml:
    def test_fallback_extracts_events_from_raw_html(self):
        events = ComedyClubHaugExtractor._extract_from_raw_html(
            _raw_html([_make_event_obj()])
        )
        assert len(events) == 1
        assert events[0]["eventTitle"] == "Best of Stand-Up"

    def test_fallback_empty_html(self):
        assert ComedyClubHaugExtractor._extract_from_raw_html("") == []


# ---------------------------------------------------------------------------
# _extract_single_event — balanced JSON extraction
# ---------------------------------------------------------------------------


class TestExtractSingleEvent:
    def test_extracts_valid_json_object(self):
        obj = {"id": "1", "title": "Test", "url": "https://comedyclubhaug.com/shows/test", "slug": "test", "eventTitle": "Test"}
        text = json.dumps(obj)
        result = ComedyClubHaugExtractor._extract_single_event(text, 0)
        assert result is not None
        assert result["eventTitle"] == "Test"

    def test_returns_none_for_unbalanced_braces(self):
        text = '{"id": "1", "title": "Test"'
        result = ComedyClubHaugExtractor._extract_single_event(text, 0)
        assert result is None

    def test_handles_rsc_references(self):
        text = '{"id": "1", "title": "Test", "url": "https://comedyclubhaug.com/shows/test", "slug": "test", "ref": "$L5", "other": "$Sreact.suspense"}'
        result = ComedyClubHaugExtractor._extract_single_event(text, 0)
        assert result is not None
        assert result["ref"] is None
        assert result["other"] is None
