"""
Unit tests for MadridComedyLabEventExtractor.parse_events().
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.scrapers.implementations.venues.madrid_comedy_lab.extractor import (
    MadridComedyLabEventExtractor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api_response(events: list[dict] | None = None) -> dict:
    """Build a minimal Fienta API response dict."""
    return {
        "success": {},
        "count": len(events) if events else 0,
        "events": events or [],
    }


def _raw_event(
    id_=177670,
    title="Dark Humour Night",
    starts_at="2099-01-01 20:30:00",
    ends_at="2099-01-01 22:00:00",
    url="https://fienta.com/dark-humour-night-lab-177670",
    sale_status="onSale",
    description="<p>Comedy show</p>",
) -> dict:
    return {
        "id": id_,
        "title": title,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "url": url,
        "sale_status": sale_status,
        "description": description,
    }


# ---------------------------------------------------------------------------
# parse_events — valid inputs
# ---------------------------------------------------------------------------


class TestParseEventsValid:
    def test_single_event(self):
        data = _api_response([_raw_event()])
        events = MadridComedyLabEventExtractor.parse_events(data)

        assert len(events) == 1
        assert events[0].title == "Dark Humour Night"
        assert events[0].event_id == 177670
        assert events[0].starts_at == "2099-01-01 20:30:00"
        assert events[0].url == "https://fienta.com/dark-humour-night-lab-177670"

    def test_multiple_events(self):
        data = _api_response([
            _raw_event(id_=1, title="Show A"),
            _raw_event(id_=2, title="Show B"),
        ])
        events = MadridComedyLabEventExtractor.parse_events(data)

        assert len(events) == 2
        titles = {e.title for e in events}
        assert titles == {"Show A", "Show B"}

    def test_preserves_all_fields(self):
        data = _api_response([_raw_event(
            sale_status="soldOut",
            description="<p>Sold out!</p>",
            ends_at="2099-01-01 23:00:00",
        )])
        events = MadridComedyLabEventExtractor.parse_events(data)

        assert events[0].sale_status == "soldOut"
        assert events[0].description == "<p>Sold out!</p>"
        assert events[0].ends_at == "2099-01-01 23:00:00"


# ---------------------------------------------------------------------------
# parse_events — excluded titles (case-insensitive)
# ---------------------------------------------------------------------------


class TestParseEventsExcludedTitles:
    def test_excludes_gift_title(self):
        data = _api_response([_raw_event(title="Gift Card for Comedy")])
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert len(events) == 0

    def test_excludes_gift_case_insensitive(self):
        data = _api_response([_raw_event(title="GIFT VOUCHER")])
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert len(events) == 0

    def test_excludes_valencia_title(self):
        data = _api_response([_raw_event(title="Comedy Night Valencia")])
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert len(events) == 0

    def test_excludes_valencia_case_insensitive(self):
        data = _api_response([_raw_event(title="valencia comedy show")])
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert len(events) == 0

    def test_non_excluded_title_passes(self):
        data = _api_response([_raw_event(title="Stand-Up in English")])
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert len(events) == 1


# ---------------------------------------------------------------------------
# parse_events — missing / invalid fields
# ---------------------------------------------------------------------------


class TestParseEventsMissingFields:
    def test_skips_event_missing_starts_at(self):
        data = _api_response([_raw_event(starts_at="")])
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert len(events) == 0

    def test_skips_event_missing_url(self):
        data = _api_response([_raw_event(url="")])
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert len(events) == 0

    def test_skips_event_with_none_starts_at(self):
        data = _api_response([_raw_event()])
        data["events"][0]["starts_at"] = None
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert len(events) == 0

    def test_skips_non_dict_items(self):
        data = _api_response([])
        data["events"] = ["not-a-dict", 42, None]
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert len(events) == 0

    def test_missing_optional_fields_default_to_empty(self):
        data = _api_response([{
            "id": 1,
            "title": "Minimal Event",
            "starts_at": "2099-01-01 20:30:00",
            "url": "https://fienta.com/minimal",
        }])
        events = MadridComedyLabEventExtractor.parse_events(data)

        assert len(events) == 1
        assert events[0].sale_status == ""
        assert events[0].description == ""
        assert events[0].ends_at == ""


# ---------------------------------------------------------------------------
# parse_events — empty / invalid data
# ---------------------------------------------------------------------------


class TestParseEventsEmpty:
    def test_empty_events_array(self):
        data = _api_response([])
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert events == []

    def test_missing_events_key(self):
        data = {"success": {}, "count": 0}
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert events == []

    def test_non_dict_data_returns_empty(self):
        events = MadridComedyLabEventExtractor.parse_events("not a dict")
        assert events == []

    def test_none_data_returns_empty(self):
        events = MadridComedyLabEventExtractor.parse_events(None)
        assert events == []

    def test_events_key_not_a_list(self):
        data = {"events": "not-a-list"}
        events = MadridComedyLabEventExtractor.parse_events(data)
        assert events == []
