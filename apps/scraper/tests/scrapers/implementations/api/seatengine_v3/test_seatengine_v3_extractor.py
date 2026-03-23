"""Unit tests for SeatEngineV3Extractor."""

import pytest

from laughtrack.scrapers.implementations.api.seatengine_v3.extractor import (
    SeatEngineV3Extractor,
)

BASE_URL = "https://www.thecomedystudio.com"
VENUE_UUID = "cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3"


def _make_response(events: list) -> dict:
    return {"data": {"eventsList": {"events": events}}}


def _make_event(
    name: str,
    shows: list,
    *,
    uuid: str = "event-uuid-1",
    status: str = "UPCOMING",
    talents: list | None = None,
    page_path: str = "/events/test-show",
) -> dict:
    return {
        "uuid": uuid,
        "name": name,
        "status": status,
        "soldOut": False,
        "page": {"path": page_path},
        "talents": talents or [{"name": name}],
        "shows": shows,
    }


def _make_show(
    start_datetime: str,
    *,
    uuid: str = "show-uuid-1",
    status: str = "UPCOMING",
    sold_out: bool = False,
    inventories: list | None = None,
) -> dict:
    return {
        "uuid": uuid,
        "startDateTime": start_datetime,
        "soldOut": sold_out,
        "status": status,
        "inventories": inventories or [],
    }


class TestFlattenEvents:
    def test_single_event_single_show(self):
        show = _make_show("2026-04-01T20:00:00")
        event = _make_event("Test Show", [show], talents=[{"name": "Comedian A"}])
        records = SeatEngineV3Extractor.flatten_events(_make_response([event]), BASE_URL)
        assert len(records) == 1
        r = records[0]
        assert r["event_name"] == "Test Show"
        assert r["start_datetime"] == "2026-04-01T20:00:00"
        assert r["show_page_url"] == f"{BASE_URL}/events/test-show"
        assert r["talents"] == ["Comedian A"]

    def test_one_event_multiple_shows_flattened(self):
        shows = [
            _make_show("2026-04-01T20:00:00", uuid="s1"),
            _make_show("2026-04-08T20:00:00", uuid="s2"),
            _make_show("2026-04-15T20:00:00", uuid="s3"),
        ]
        event = _make_event("Recurring Show", shows)
        records = SeatEngineV3Extractor.flatten_events(_make_response([event]), BASE_URL)
        assert len(records) == 3
        dates = [r["start_datetime"] for r in records]
        assert "2026-04-01T20:00:00" in dates
        assert "2026-04-15T20:00:00" in dates

    def test_cancelled_events_excluded(self):
        show = _make_show("2026-04-01T20:00:00")
        event = _make_event("Cancelled Show", [show], status="CANCELLED")
        records = SeatEngineV3Extractor.flatten_events(_make_response([event]), BASE_URL)
        assert records == []

    def test_past_events_excluded(self):
        show = _make_show("2025-01-01T20:00:00")
        event = _make_event("Old Show", [show], status="PAST")
        records = SeatEngineV3Extractor.flatten_events(_make_response([event]), BASE_URL)
        assert records == []

    def test_non_upcoming_shows_excluded(self):
        shows = [
            _make_show("2026-04-01T20:00:00", uuid="s1", status="UPCOMING"),
            _make_show("2026-04-08T20:00:00", uuid="s2", status="PAST"),
            _make_show("2026-04-15T20:00:00", uuid="s3", status="CANCELLED"),
        ]
        event = _make_event("Mixed Shows", shows)
        records = SeatEngineV3Extractor.flatten_events(_make_response([event]), BASE_URL)
        assert len(records) == 1
        assert records[0]["start_datetime"] == "2026-04-01T20:00:00"

    def test_on_sale_shows_included(self):
        show = _make_show("2026-04-01T20:00:00", status="ON_SALE")
        event = _make_event("On Sale Show", [show])
        records = SeatEngineV3Extractor.flatten_events(_make_response([event]), BASE_URL)
        assert len(records) == 1

    def test_inventories_included_in_record(self):
        inventories = [
            {"uuid": "inv-1", "title": "General Admission", "name": "GA", "price": 2000, "active": True},
            {"uuid": "inv-2", "title": "VIP", "name": "VIP", "price": 5000, "active": True},
        ]
        show = _make_show("2026-04-01T20:00:00", inventories=inventories)
        event = _make_event("Ticketed Show", [show])
        records = SeatEngineV3Extractor.flatten_events(_make_response([event]), BASE_URL)
        assert len(records[0]["inventories"]) == 2

    def test_show_page_url_built_from_base_url(self):
        show = _make_show("2026-04-01T20:00:00")
        event = _make_event("Comedy Night", [show], page_path="/events/comedy-night-12345")
        records = SeatEngineV3Extractor.flatten_events(_make_response([event]), BASE_URL)
        assert records[0]["show_page_url"] == f"{BASE_URL}/events/comedy-night-12345"

    def test_empty_events_list(self):
        records = SeatEngineV3Extractor.flatten_events(_make_response([]), BASE_URL)
        assert records == []

    def test_base_url_trailing_slash_stripped(self):
        show = _make_show("2026-04-01T20:00:00")
        event = _make_event("Show", [show], page_path="/events/test")
        records = SeatEngineV3Extractor.flatten_events(
            _make_response([event]), BASE_URL + "/"
        )
        assert records[0]["show_page_url"] == f"{BASE_URL}/events/test"

    def test_no_page_field_falls_back_to_base_url(self):
        """Events without a page key should use base_url as the show_page_url."""
        show = _make_show("2026-04-01T20:00:00")
        event = _make_event("Pageless Show", [show])
        event["page"] = None  # no page data returned
        records = SeatEngineV3Extractor.flatten_events(_make_response([event]), BASE_URL)
        assert records[0]["show_page_url"] == BASE_URL

    def test_missing_page_key_falls_back_to_base_url(self):
        show = _make_show("2026-04-01T20:00:00")
        event = _make_event("No Page Key", [show])
        del event["page"]
        records = SeatEngineV3Extractor.flatten_events(_make_response([event]), BASE_URL)
        assert records[0]["show_page_url"] == BASE_URL

    def test_build_query_payload_contains_venue_uuid(self):
        payload = SeatEngineV3Extractor.build_query_payload(VENUE_UUID)
        assert payload["variables"]["venueUuid"] == VENUE_UUID
        assert "eventsList" in payload["query"]
