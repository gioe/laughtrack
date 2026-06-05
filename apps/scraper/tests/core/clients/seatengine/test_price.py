"""Unit tests for the shared SeatEngine inventory price coercion helper.

These guard the regression where a chain-wide sentinel inventory (a
"Closed for 4th of July" placeholder priced at 100_000_000¢ = $1M) overflows
``tickets.price`` Decimal(7,2) and aborts the whole batch insert for the venue.
"""

import pytest

from laughtrack.core.clients.seatengine.price import (
    INVENTORY_PRICE_CEILING_CENTS,
    coerce_inventory_price_cents,
)


class TestCoerceInventoryPriceCents:
    def test_typical_price_returns_dollars_no_reason(self):
        price, reason = coerce_inventory_price_cents(3500)
        assert price == 35.0
        assert reason is None

    def test_numeric_string_parses(self):
        price, reason = coerce_inventory_price_cents("4500")
        assert price == 45.0
        assert reason is None

    def test_none_returns_none_no_reason(self):
        assert coerce_inventory_price_cents(None) == (None, None)

    def test_non_numeric_returns_none_no_reason(self):
        # Extraction-failure path — caller treats these the same as missing.
        assert coerce_inventory_price_cents("free") == (None, None)
        assert coerce_inventory_price_cents({}) == (None, None)

    def test_zero_returns_none_no_reason(self):
        # A zero is the classic-detail-page extraction-failure sentinel —
        # caller persists NULL, not $0.
        assert coerce_inventory_price_cents(0) == (None, None)

    def test_negative_returns_none_no_reason(self):
        assert coerce_inventory_price_cents(-100) == (None, None)

    def test_value_at_ceiling_is_accepted(self):
        price, reason = coerce_inventory_price_cents(INVENTORY_PRICE_CEILING_CENTS)
        assert price == INVENTORY_PRICE_CEILING_CENTS / 100.0
        assert reason is None

    def test_value_just_above_ceiling_is_rejected_with_reason(self):
        price, reason = coerce_inventory_price_cents(INVENTORY_PRICE_CEILING_CENTS + 1)
        assert price is None
        assert reason is not None
        assert "ceiling" in reason
        # Reason should include the raw cents value so callers can log without re-formatting.
        assert str(INVENTORY_PRICE_CEILING_CENTS + 1) in reason

    @pytest.mark.parametrize("sentinel_cents", [10_000_000, 100_000_000])
    def test_chain_sentinel_values_are_dropped(self, sentinel_cents):
        # The actual values observed in the nightly run that motivated this guard:
        # $100,000 and $1,000,000 sentinel placeholders on "Closed for 4th of July"
        # shows at Bricktown OKC, Bricktown Tulsa, Summit City, and Springfield.
        price, reason = coerce_inventory_price_cents(sentinel_cents)
        assert price is None
        assert reason is not None
