"""Unit tests for the Gotham live events feed models.

Covers GothamFeedEvent.from_feed_item / enrich_with_showclix_data and
GothamFeedResponse.from_dict parsing of the worker feed shape.

Fixture dates use far-future years (2099) per project convention so the
extractor's past-event filter never turns these tests into time-bombs.
"""

import json
import pathlib
from unittest.mock import MagicMock

import pytest

from laughtrack.core.clients.gotham.models.models import GothamFeedEvent, GothamFeedResponse

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def _load_feed_fixture() -> dict:
    return json.loads((_FIXTURES_DIR / "worker_feed_page.json").read_text(encoding="utf-8"))


def _feed_item(**field_overrides) -> dict:
    item = {
        "id": "6a286dd29da8c9c14b299e74",
        "isArchived": False,
        "isDraft": False,
        "fieldData": {
            "event-title": "The Gotham All-Stars",
            "event-times": "2099-06-20T20:00:00-04:00",
            "event-id": "10378853",
            "event-url-slug": "the-gotham-all-stars2526rbueuau",
            "event-category": "Stand-up Comedy Shows",
        },
    }
    item["fieldData"].update(field_overrides)
    return item


# ---------------------------------------------------------------------------
# GothamFeedEvent.from_feed_item
# ---------------------------------------------------------------------------


def test_from_feed_item_maps_field_data():
    event = GothamFeedEvent.from_feed_item(_feed_item())
    assert event is not None
    assert event.id == "6a286dd29da8c9c14b299e74"
    assert event.name == "The Gotham All-Stars"
    assert event.start == "2099-06-20T20:00:00-04:00"
    assert event.event_id == "10378853"
    assert event.slug == "the-gotham-all-stars2526rbueuau"
    assert event.category == "Stand-up Comedy Shows"


def test_from_feed_item_skips_draft_items():
    item = _feed_item()
    item["isDraft"] = True
    assert GothamFeedEvent.from_feed_item(item) is None


def test_from_feed_item_skips_archived_items():
    item = _feed_item()
    item["isArchived"] = True
    assert GothamFeedEvent.from_feed_item(item) is None


def test_from_feed_item_skips_missing_title():
    assert GothamFeedEvent.from_feed_item(_feed_item(**{"event-title": ""})) is None


def test_from_feed_item_skips_missing_times():
    assert GothamFeedEvent.from_feed_item(_feed_item(**{"event-times": None})) is None


def test_from_feed_item_skips_missing_field_data():
    assert GothamFeedEvent.from_feed_item({"id": "x", "isArchived": False, "isDraft": False}) is None


def test_from_feed_item_tolerates_missing_event_id():
    event = GothamFeedEvent.from_feed_item(_feed_item(**{"event-id": None}))
    assert event is not None
    assert event.event_id is None


# ---------------------------------------------------------------------------
# GothamFeedEvent.start_datetime / show_page_url
# ---------------------------------------------------------------------------


def test_start_datetime_preserves_feed_offset():
    event = GothamFeedEvent.from_feed_item(_feed_item())
    dt = event.start_datetime
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.utcoffset().total_seconds() == -4 * 3600  # EDT offset preserved
    assert (dt.year, dt.month, dt.day, dt.hour) == (2099, 6, 20, 20)


def test_start_datetime_returns_none_for_malformed_times():
    event = GothamFeedEvent.from_feed_item(_feed_item(**{"event-times": "TBD"}))
    assert event is not None
    assert event.start_datetime is None


def test_show_page_url_uses_showclix_slug():
    event = GothamFeedEvent.from_feed_item(_feed_item())
    assert event.show_page_url == "https://www.showclix.com/event/the-gotham-all-stars2526rbueuau"


def test_show_page_url_falls_back_to_venue_events_page():
    event = GothamFeedEvent.from_feed_item(_feed_item(**{"event-url-slug": None}))
    assert event.show_page_url == "https://www.gothamcomedyclub.com/events"


# ---------------------------------------------------------------------------
# GothamFeedEvent.enrich_with_showclix_data
# ---------------------------------------------------------------------------


def _showclix_data(price="32.00", available=42, sold_out=False) -> MagicMock:
    data = MagicMock()
    data.get_primary_price.return_value = price
    data.get_available_tickets.return_value = available
    data.is_sold_out.return_value = sold_out
    return data


def test_enrich_with_showclix_data_sets_ticket_fields():
    event = GothamFeedEvent.from_feed_item(_feed_item())
    enriched = event.enrich_with_showclix_data(_showclix_data())
    assert enriched is not event
    assert enriched.price == 32.0
    assert enriched.inventory == 42
    assert enriched.sold_out is False
    # Original is untouched
    assert event.price is None
    assert event.inventory is None


def test_enrich_with_showclix_data_marks_sold_out():
    event = GothamFeedEvent.from_feed_item(_feed_item())
    enriched = event.enrich_with_showclix_data(_showclix_data(available=0, sold_out=True))
    assert enriched.sold_out is True
    assert enriched.inventory == 0


def test_enrich_with_showclix_data_tolerates_unparseable_price():
    event = GothamFeedEvent.from_feed_item(_feed_item())
    enriched = event.enrich_with_showclix_data(_showclix_data(price="N/A"))
    assert enriched.price is None
    assert enriched.inventory == 42


# ---------------------------------------------------------------------------
# GothamFeedResponse.from_dict — fixture-based parsing
# ---------------------------------------------------------------------------


def test_from_dict_parses_fixture_pagination():
    feed = GothamFeedResponse.from_dict(_load_feed_fixture())
    assert feed.pagination.limit == 100
    assert feed.pagination.offset == 0
    assert feed.pagination.total == 8


def test_from_dict_skips_draft_archived_and_timeless_items():
    """The 8-item fixture holds 1 draft, 1 archived, and 1 missing-times item.

    from_dict keeps the remaining 5 (the malformed-times and past items
    survive shape parsing — the extractor's upcoming filter drops them).
    """
    feed = GothamFeedResponse.from_dict(_load_feed_fixture())
    names = [e.name for e in feed.events]
    assert len(feed.events) == 5
    assert 'Oz "The Mentalist" Pearlman LIVE!' not in names  # draft
    assert "Archived Showcase" not in names
    assert "Show With No Times" not in names
    assert "Show With Malformed Times" in names
    assert "Long Past Showcase" in names


def test_from_dict_keeps_multiple_showtimes_as_separate_events():
    """Recurring shows appear once per showtime with distinct Showclix ids."""
    feed = GothamFeedResponse.from_dict(_load_feed_fixture())
    all_stars = [e for e in feed.events if e.name == "The Gotham All-Stars"]
    assert len(all_stars) == 2
    assert {e.event_id for e in all_stars} == {"10378853", "10378852"}
    assert {e.start for e in all_stars} == {
        "2099-06-20T20:00:00-04:00",
        "2099-06-20T22:30:00-04:00",
    }


def test_from_dict_raises_for_non_dict_payload():
    with pytest.raises(ValueError):
        GothamFeedResponse.from_dict(["not", "a", "dict"])


def test_from_dict_raises_for_missing_items_list():
    with pytest.raises(ValueError):
        GothamFeedResponse.from_dict({"pagination": {"limit": 100, "offset": 0, "total": 0}})


def test_from_dict_tolerates_malformed_individual_items():
    data = {
        "items": [None, "garbage", {"fieldData": "not a dict"}, _feed_item()],
        "pagination": {"limit": 100, "offset": 0, "total": 4},
    }
    feed = GothamFeedResponse.from_dict(data)
    assert len(feed.events) == 1
    assert feed.events[0].name == "The Gotham All-Stars"
