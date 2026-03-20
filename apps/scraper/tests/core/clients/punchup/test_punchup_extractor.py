"""
Unit tests for PunchupExtractor parsing methods.

Covers the three internal helpers that convert raw data dicts into PunchupShow objects:
- _build_punchup_show: required-field validation and field mapping
- _parse_items: carousel format ({"type":"show","show":{...}})
- _parse_venue_shows_items: flat venueShows format (direct show dicts)
"""

import pytest

from laughtrack.core.clients.punchup.extractor import PunchupExtractor, PunchupShow


# ---------------------------------------------------------------------------
# _build_punchup_show
# ---------------------------------------------------------------------------


def _valid_data(**overrides) -> dict:
    base = {
        "id": "show-1",
        "title": "Test Show",
        "datetime": "2026-04-01T20:00:00",
        "ticket_link": "https://example.com/tickets",
        "tixologi_event_id": "1234",
        "is_sold_out": False,
        "metadata_text": "Some description",
        "show_comedians": [{"id": "c1", "display_name": "Jane Doe", "ordering": 0}],
    }
    base.update(overrides)
    return base


class TestBuildPunchupShow:
    def test_valid_data_returns_punchup_show(self):
        result = PunchupExtractor._build_punchup_show(_valid_data())
        assert isinstance(result, PunchupShow)
        assert result.id == "show-1"
        assert result.title == "Test Show"
        assert result.datetime_str == "2026-04-01T20:00:00"
        assert result.ticket_link == "https://example.com/tickets"
        assert result.tixologi_event_id == "1234"
        assert result.is_sold_out is False
        assert result.metadata_text == "Some description"
        assert len(result.show_comedians) == 1

    def test_missing_title_returns_none(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(title=""))
        assert result is None

    def test_whitespace_only_title_returns_none(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(title="   "))
        assert result is None

    def test_missing_datetime_returns_none(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(datetime=""))
        assert result is None

    def test_whitespace_only_datetime_returns_none(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(datetime="   "))
        assert result is None

    def test_missing_both_title_and_datetime_returns_none(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(title="", datetime=""))
        assert result is None

    def test_none_title_returns_none(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(title=None))
        assert result is None

    def test_none_datetime_returns_none(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(datetime=None))
        assert result is None

    def test_is_sold_out_true(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(is_sold_out=True))
        assert result is not None
        assert result.is_sold_out is True

    def test_missing_optional_fields_use_defaults(self):
        """ticket_link, tixologi_event_id, metadata_text, show_comedians, and id are optional."""
        data = {"title": "Minimal Show", "datetime": "2026-04-01T20:00:00"}
        result = PunchupExtractor._build_punchup_show(data)
        assert result is not None
        assert result.id == ""
        assert result.ticket_link == ""
        assert result.tixologi_event_id is None
        assert result.metadata_text is None
        assert result.show_comedians == []

    def test_metadata_text_none_stored_as_none(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(metadata_text=None))
        assert result is not None
        assert result.metadata_text is None

    def test_empty_string_metadata_text_stored_as_none(self):
        """Empty string metadata_text is coerced to None via 'or None'."""
        result = PunchupExtractor._build_punchup_show(_valid_data(metadata_text=""))
        assert result is not None
        assert result.metadata_text is None

    def test_title_is_stripped(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(title="  Test Show  "))
        assert result is not None
        assert result.title == "Test Show"

    def test_datetime_is_stripped(self):
        result = PunchupExtractor._build_punchup_show(_valid_data(datetime="  2026-04-01T20:00:00  "))
        assert result is not None
        assert result.datetime_str == "2026-04-01T20:00:00"


# ---------------------------------------------------------------------------
# _parse_items (carousel format)
# ---------------------------------------------------------------------------


def _carousel_item(**show_overrides) -> dict:
    """Build a {"type":"show","show":{...}} carousel item dict."""
    return {
        "type": "show",
        "id": "item-uuid-1",
        "order": 1,
        "show": _valid_data(**show_overrides),
    }


class TestParseItems:
    def test_valid_carousel_item_returned(self):
        items = [_carousel_item()]
        result = PunchupExtractor._parse_items(items)
        assert len(result) == 1
        assert result[0].title == "Test Show"

    def test_multiple_valid_items(self):
        items = [
            _carousel_item(title="Show A", datetime="2026-04-01T20:00:00"),
            _carousel_item(title="Show B", datetime="2026-04-02T20:00:00"),
        ]
        result = PunchupExtractor._parse_items(items)
        assert len(result) == 2
        assert {r.title for r in result} == {"Show A", "Show B"}

    def test_empty_list_returns_empty(self):
        result = PunchupExtractor._parse_items([])
        assert result == []

    def test_wrong_type_item_skipped(self):
        """Items where type != 'show' are not included."""
        items = [
            {"type": "link", "id": "link-1", "url": "https://example.com"},
            _carousel_item(),
        ]
        result = PunchupExtractor._parse_items(items)
        assert len(result) == 1
        assert result[0].title == "Test Show"

    def test_non_dict_item_skipped(self):
        items = ["not-a-dict", 42, None, _carousel_item()]
        result = PunchupExtractor._parse_items(items)
        assert len(result) == 1

    def test_non_dict_show_field_skipped(self):
        """Items where 'show' is not a dict are skipped."""
        items = [
            {"type": "show", "show": "not-a-dict"},
            {"type": "show", "show": None},
            {"type": "show", "show": 42},
            _carousel_item(),
        ]
        result = PunchupExtractor._parse_items(items)
        assert len(result) == 1
        assert result[0].title == "Test Show"

    def test_show_missing_title_skipped(self):
        items = [_carousel_item(title="")]
        result = PunchupExtractor._parse_items(items)
        assert result == []

    def test_show_missing_datetime_skipped(self):
        items = [_carousel_item(datetime="")]
        result = PunchupExtractor._parse_items(items)
        assert result == []

    def test_show_key_absent_skipped(self):
        """Item with type='show' but no 'show' key is skipped (item.get('show') returns None)."""
        items = [{"type": "show"}, _carousel_item()]
        result = PunchupExtractor._parse_items(items)
        assert len(result) == 1
        assert result[0].title == "Test Show"

    def test_empty_dict_item_skipped(self):
        """An empty dict has no 'type' key, so it is skipped."""
        items = [{}, _carousel_item()]
        result = PunchupExtractor._parse_items(items)
        assert len(result) == 1

    def test_mixed_valid_and_invalid_items(self):
        items = [
            _carousel_item(title=""),                              # missing title
            {"type": "link", "url": "https://x.com"},             # wrong type
            {"type": "show", "show": None},                       # non-dict show
            _carousel_item(title="Good Show"),                    # valid
        ]
        result = PunchupExtractor._parse_items(items)
        assert len(result) == 1
        assert result[0].title == "Good Show"


# ---------------------------------------------------------------------------
# _parse_venue_shows_items (flat venueShows format)
# ---------------------------------------------------------------------------


class TestParseVenueShowsItems:
    def test_valid_flat_item_returned(self):
        items = [_valid_data()]
        result = PunchupExtractor._parse_venue_shows_items(items)
        assert len(result) == 1
        assert result[0].title == "Test Show"

    def test_multiple_valid_items(self):
        items = [
            _valid_data(title="Show A", datetime="2026-04-01T20:00:00"),
            _valid_data(title="Show B", datetime="2026-04-02T20:00:00"),
        ]
        result = PunchupExtractor._parse_venue_shows_items(items)
        assert len(result) == 2

    def test_empty_list_returns_empty(self):
        result = PunchupExtractor._parse_venue_shows_items([])
        assert result == []

    def test_non_dict_items_skipped(self):
        items = ["string", 42, None, _valid_data()]
        result = PunchupExtractor._parse_venue_shows_items(items)
        assert len(result) == 1
        assert result[0].title == "Test Show"

    def test_sold_out_show_included(self):
        items = [_valid_data(is_sold_out=True)]
        result = PunchupExtractor._parse_venue_shows_items(items)
        assert len(result) == 1
        assert result[0].is_sold_out is True

    def test_missing_title_skipped(self):
        items = [_valid_data(title="")]
        result = PunchupExtractor._parse_venue_shows_items(items)
        assert result == []

    def test_missing_datetime_skipped(self):
        items = [_valid_data(datetime="")]
        result = PunchupExtractor._parse_venue_shows_items(items)
        assert result == []

    def test_mixed_valid_and_invalid(self):
        items = [
            _valid_data(title=""),                   # missing title
            _valid_data(datetime=""),                # missing datetime
            "not-a-dict",                            # non-dict
            _valid_data(title="Valid Show"),         # valid
        ]
        result = PunchupExtractor._parse_venue_shows_items(items)
        assert len(result) == 1
        assert result[0].title == "Valid Show"

    def test_show_comedians_preserved(self):
        comedians = [
            {"id": "c1", "display_name": "Comic A", "ordering": 0},
            {"id": "c2", "display_name": "Comic B", "ordering": 1},
        ]
        items = [_valid_data(show_comedians=comedians)]
        result = PunchupExtractor._parse_venue_shows_items(items)
        assert len(result) == 1
        assert result[0].show_comedians == comedians
