"""
Unit tests for GoofsEventExtractor.extract_shows() and _extract_initial_shows_array().

Covers:
  - JSON-in-JSON RSC payload decoding
  - Bracket-counting array extraction
  - _normalize_time() compact form handling
  - from_dict() field mapping, including priceGaCents=0 and non-numeric id
  - Edge cases: empty HTML, missing initialShows, unmatched brackets, multi-chunk
"""

import json

import pytest

from laughtrack.core.entities.event.goofs import GoofsEvent
from laughtrack.scrapers.implementations.venues.goofs.extractor import GoofsEventExtractor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rsc_html(shows: list) -> str:
    """Embed a shows list in a minimal Next.js RSC __next_f.push payload."""
    inner_obj = {"initialShows": shows}
    inner_json = json.dumps(inner_obj)
    # Double-encode: the RSC payload string is itself JSON-encoded inside the push call
    outer = json.dumps(inner_json)
    # outer is '"<escaped-json>"' — strip surrounding quotes to get the escaped payload
    escaped = outer[1:-1]
    return f'<script>self.__next_f.push([1,"{escaped}"])</script>'


def _show(
    id_=403,
    slug="2026-03-27-2100",
    date="2026-03-27",
    time="9:00 PM",
    title="Friday Night Live",
    headliner="Jane Doe",
    price=2000,
):
    return {
        "id": id_,
        "slug": slug,
        "date": date,
        "time": time,
        "computedDisplayTitle": title,
        "headlinerName": headliner,
        "priceGaCents": price,
    }


# ---------------------------------------------------------------------------
# extract_shows — happy path
# ---------------------------------------------------------------------------


class TestExtractShows:
    def test_single_show_extracted(self):
        html = _make_rsc_html([_show()])
        events = GoofsEventExtractor.extract_shows(html)
        assert len(events) == 1
        e = events[0]
        assert e.display_title == "Friday Night Live"
        assert e.date == "2026-03-27"
        assert e.time == "9:00 PM"

    def test_multiple_shows_extracted(self):
        html = _make_rsc_html([_show(id_=1), _show(id_=2, title="Saturday Show")])
        events = GoofsEventExtractor.extract_shows(html)
        assert len(events) == 2
        titles = {e.display_title for e in events}
        assert "Friday Night Live" in titles
        assert "Saturday Show" in titles

    def test_headliner_populated(self):
        html = _make_rsc_html([_show(headliner="Jane Doe")])
        events = GoofsEventExtractor.extract_shows(html)
        assert events[0].headliner_name == "Jane Doe"

    def test_price_populated(self):
        html = _make_rsc_html([_show(price=2000)])
        events = GoofsEventExtractor.extract_shows(html)
        assert events[0].price_ga_cents == 2000

    def test_price_zero_is_not_coerced_to_none(self):
        """priceGaCents=0 must be stored as 0, not None."""
        html = _make_rsc_html([_show(price=0)])
        events = GoofsEventExtractor.extract_shows(html)
        assert events[0].price_ga_cents == 0

    def test_compact_time_normalised(self):
        """'9PM' compact form must be normalised to '9:00 PM'."""
        html = _make_rsc_html([_show(time="9PM")])
        events = GoofsEventExtractor.extract_shows(html)
        assert events[0].time == "9:00 PM"

    def test_compact_time_11pm_normalised(self):
        html = _make_rsc_html([_show(time="11PM")])
        events = GoofsEventExtractor.extract_shows(html)
        assert events[0].time == "11:00 PM"

    def test_show_without_title_skipped(self):
        show = _show()
        show["computedDisplayTitle"] = ""
        show["title"] = None
        html = _make_rsc_html([show])
        events = GoofsEventExtractor.extract_shows(html)
        assert events == []

    def test_show_without_date_skipped(self):
        show = _show()
        show["date"] = ""
        html = _make_rsc_html([show])
        events = GoofsEventExtractor.extract_shows(html)
        assert events == []

    def test_non_dict_items_skipped(self):
        html = _make_rsc_html(["not-a-dict", 42, None, _show()])
        events = GoofsEventExtractor.extract_shows(html)
        assert len(events) == 1

    def test_non_numeric_id_defaults_to_zero(self):
        show = _show()
        show["id"] = "not-a-number"
        html = _make_rsc_html([show])
        events = GoofsEventExtractor.extract_shows(html)
        assert len(events) == 1
        assert events[0].id == 0


# ---------------------------------------------------------------------------
# extract_shows — edge / error cases
# ---------------------------------------------------------------------------


class TestExtractShowsEdgeCases:
    def test_empty_html_returns_empty(self):
        assert GoofsEventExtractor.extract_shows("") == []

    def test_no_next_f_push_returns_empty(self):
        assert GoofsEventExtractor.extract_shows("<html><body>no payload</body></html>") == []

    def test_no_initial_shows_key_returns_empty(self):
        """A valid RSC push chunk that contains no initialShows is ignored."""
        inner = json.dumps({"otherKey": [1, 2, 3]})
        escaped = json.dumps(inner)[1:-1]
        html = f'<script>self.__next_f.push([1,"{escaped}"])</script>'
        assert GoofsEventExtractor.extract_shows(html) == []

    def test_empty_shows_list_falls_through_to_next_chunk(self):
        """
        When initialShows is present but empty, the extractor should NOT return
        early — it must continue scanning subsequent chunks.
        """
        # First chunk: initialShows = []
        inner1 = json.dumps({"initialShows": []})
        escaped1 = json.dumps(inner1)[1:-1]
        # Second chunk: has real shows
        inner2 = json.dumps({"initialShows": [_show()]})
        escaped2 = json.dumps(inner2)[1:-1]
        html = (
            f'<script>self.__next_f.push([1,"{escaped1}"])</script>'
            f'<script>self.__next_f.push([1,"{escaped2}"])</script>'
        )
        events = GoofsEventExtractor.extract_shows(html)
        assert len(events) == 1

    def test_malformed_push_string_skipped(self):
        """Malformed JSON in a push chunk is skipped; subsequent chunks are tried."""
        good_chunk_inner = json.dumps({"initialShows": [_show()]})
        good_escaped = json.dumps(good_chunk_inner)[1:-1]
        html = (
            '<script>self.__next_f.push([1,"not valid json \\"])</script>'
            f'<script>self.__next_f.push([1,"{good_escaped}"])</script>'
        )
        events = GoofsEventExtractor.extract_shows(html)
        assert len(events) == 1


# ---------------------------------------------------------------------------
# _extract_initial_shows_array — internal bracket-counting logic
# ---------------------------------------------------------------------------


class TestExtractInitialShowsArray:
    def test_extracts_array_correctly(self):
        text = '{"initialShows":[{"id":1},{"id":2}],"other":true}'
        result = GoofsEventExtractor._extract_initial_shows_array(text)
        assert result == [{"id": 1}, {"id": 2}]

    def test_nested_objects_in_shows(self):
        text = '{"initialShows":[{"id":1,"nested":{"a":1}}]}'
        result = GoofsEventExtractor._extract_initial_shows_array(text)
        assert result == [{"id": 1, "nested": {"a": 1}}]

    def test_empty_array(self):
        text = '{"initialShows":[]}'
        result = GoofsEventExtractor._extract_initial_shows_array(text)
        assert result == []

    def test_missing_key_returns_none(self):
        assert GoofsEventExtractor._extract_initial_shows_array('{"other":[1,2]}') is None

    def test_unmatched_bracket_returns_none(self):
        """Text with unclosed bracket should return None, not raise."""
        text = '{"initialShows":[{"id":1}'  # missing closing ]
        assert GoofsEventExtractor._extract_initial_shows_array(text) is None

    def test_no_array_start_returns_none(self):
        text = '{"initialShows": null}'
        result = GoofsEventExtractor._extract_initial_shows_array(text)
        assert result is None
