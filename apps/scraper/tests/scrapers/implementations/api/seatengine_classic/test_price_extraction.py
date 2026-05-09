"""Unit tests for classic SeatEngine price extraction.

Covers the pure HTML/JSON parser (``price_extractor``) plus the transformer's
NULL-fallback behavior so the silent default-to-zero regression cannot return.
"""

import json
from types import SimpleNamespace

import pytest

from laughtrack.scrapers.implementations.api.seatengine_classic.price_extractor import (
    cheapest_price,
    extract_inventories,
)
from laughtrack.scrapers.implementations.api.seatengine_classic.transformer import (
    SeatEngineClassicTransformer,
)


def _make_show_html(config: dict) -> str:
    return (
        "<html><head><script>\n"
        "//<![CDATA[\n"
        f"window.seat_engine_app_config = {json.dumps(config)};\n"
        "//]]>\n"
        "</script></head><body></body></html>"
    )


class TestExtractInventories:

    def test_extracts_active_inventories(self):
        cfg = {
            "showtime": {
                "inventories": [
                    {"id": 1, "name": "Single Ticket", "price": 3500},
                    {"id": 2, "name": "VIP Table of 2", "price": 9000},
                ]
            }
        }
        invs = extract_inventories(_make_show_html(cfg))
        assert [inv["price"] for inv in invs] == [3500, 9000]

    def test_returns_empty_when_config_missing(self):
        assert extract_inventories("<html><body>nothing here</body></html>") == []

    def test_returns_empty_when_inventories_key_missing(self):
        assert extract_inventories(_make_show_html({"showtime": {}})) == []

    def test_returns_empty_when_inventories_is_not_a_list(self):
        assert extract_inventories(_make_show_html({"showtime": {"inventories": {}}})) == []

    def test_returns_empty_on_truncated_json(self):
        truncated = '<html><script>window.seat_engine_app_config = {"showtime":{"inv'
        assert extract_inventories(truncated) == []

    def test_returns_empty_on_unparseable_json(self):
        garbage = '<html><script>window.seat_engine_app_config = {not json};</script></html>'
        assert extract_inventories(garbage) == []

    def test_skips_non_dict_inventory_items(self):
        cfg = {
            "showtime": {
                "inventories": [
                    {"id": 1, "price": 3500},
                    "not a dict",
                    None,
                    {"id": 2, "price": 5000},
                ]
            }
        }
        invs = extract_inventories(_make_show_html(cfg))
        assert [inv["id"] for inv in invs] == [1, 2]

    def test_handles_braces_inside_string_literals(self):
        cfg = {
            "showtime": {
                "inventories": [
                    {"id": 1, "name": "Tier {A} (the } one)", "price": 4500},
                ]
            }
        }
        invs = extract_inventories(_make_show_html(cfg))
        assert len(invs) == 1
        assert invs[0]["price"] == 4500


class TestCheapestPrice:

    def test_returns_min_positive_price_in_dollars(self):
        invs = [{"price": 3500}, {"price": 9000}, {"price": 7000}]
        assert cheapest_price(invs) == 35.0

    def test_returns_none_for_empty_list(self):
        assert cheapest_price([]) is None

    def test_returns_none_when_all_prices_are_zero_or_missing(self):
        assert cheapest_price([{"price": 0}, {"price": None}, {"name": "x"}]) is None

    def test_treats_zero_price_as_extraction_failure(self):
        # An all-zero set is the silent default-to-zero state we are guarding
        # against — callers must persist NULL instead of $0.
        assert cheapest_price([{"price": 0}, {"price": 0}]) is None

    def test_skips_non_numeric_prices(self):
        assert cheapest_price([{"price": "free"}, {"price": 4500}]) == 45.0

    def test_accepts_numeric_strings(self):
        assert cheapest_price([{"price": "3500"}, {"price": 9000}]) == 35.0


class TestTransformerNullFallback:
    """Guard the silent default-to-zero regression at the transformer boundary."""

    @staticmethod
    def _club():
        return SimpleNamespace(id=42, timezone="America/New_York")

    def _transformer(self):
        return SeatEngineClassicTransformer(self._club())

    def test_no_price_field_yields_null_ticket_price(self):
        raw = {
            "name": "Some Comedian",
            "date_str": "Sun, Mar 22, 2026 7:00 PM",
            "show_url": "https://example.com/shows/1",
            "sold_out": False,
        }
        show = self._transformer().transform_to_show(raw)
        assert show is not None
        assert show.tickets[0].price is None

    def test_explicit_none_price_passes_through(self):
        raw = {
            "name": "Some Comedian",
            "date_str": "Sun, Mar 22, 2026 7:00 PM",
            "show_url": "https://example.com/shows/2",
            "sold_out": False,
            "price": None,
        }
        show = self._transformer().transform_to_show(raw)
        assert show is not None
        assert show.tickets[0].price is None

    def test_positive_price_is_preserved(self):
        raw = {
            "name": "Some Comedian",
            "date_str": "Sun, Mar 22, 2026 7:00 PM",
            "show_url": "https://example.com/shows/3",
            "sold_out": False,
            "price": 35.0,
        }
        show = self._transformer().transform_to_show(raw)
        assert show is not None
        assert show.tickets[0].price == 35.0

    def test_zero_price_is_persisted_as_null(self):
        # If a caller hands the transformer a zero (e.g., legacy raw_data dict),
        # treat it the same as a missing price — never write $0 to the catalog
        # for a paid show.
        raw = {
            "name": "Some Comedian",
            "date_str": "Sun, Mar 22, 2026 7:00 PM",
            "show_url": "https://example.com/shows/4",
            "sold_out": False,
            "price": 0,
        }
        show = self._transformer().transform_to_show(raw)
        assert show is not None
        assert show.tickets[0].price is None

    def test_sold_out_with_price_unknown_yields_null(self):
        raw = {
            "name": "Some Comedian",
            "date_str": "Sun, Mar 22, 2026 7:00 PM",
            "show_url": "https://example.com/shows/5",
            "sold_out": True,
        }
        show = self._transformer().transform_to_show(raw)
        assert show is not None
        assert show.tickets[0].sold_out is True
        assert show.tickets[0].price is None
