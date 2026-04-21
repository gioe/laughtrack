"""Unit tests for Show.to_unique_key() date normalization (TASK-821)."""

from datetime import datetime, timezone

import pytz
import pytest

from laughtrack.core.entities.show.model import Show


def _show(date):
    return Show(
        name="Test Show",
        club_id=42,
        date=date,
        show_page_url="https://example.com/show",
        room="Main Room",
    )


def test_naive_date_passes_through_unchanged():
    naive = datetime(2026, 4, 15, 20, 0, 0)
    show = _show(naive)
    key = show.to_unique_key()
    assert key == (42, naive, "Main Room")
    assert key[1].tzinfo is None


def test_aware_utc_date_stripped_to_utc_naive():
    aware_utc = datetime(2026, 4, 15, 20, 0, 0, tzinfo=timezone.utc)
    show = _show(aware_utc)
    key = show.to_unique_key()
    expected_naive = datetime(2026, 4, 15, 20, 0, 0)
    assert key == (42, expected_naive, "Main Room")
    assert key[1].tzinfo is None


def test_aware_non_utc_date_converted_to_utc_naive():
    eastern = pytz.timezone("America/New_York")
    # 8 PM ET = midnight UTC (UTC-4 in summer)
    aware_et = eastern.localize(datetime(2026, 4, 15, 20, 0, 0))
    show = _show(aware_et)
    key = show.to_unique_key()
    expected_utc_naive = datetime(2026, 4, 16, 0, 0, 0)
    assert key == (42, expected_utc_naive, "Main Room")
    assert key[1].tzinfo is None


def test_none_date_produces_none_in_key():
    show = _show(datetime(2026, 4, 15, 20, 0, 0))
    show.date = None  # bypass constructor validation to test None branch
    key = show.to_unique_key()
    assert key == (42, None, "Main Room")


def test_to_tuple_serializes_last_scraped_date_as_utc_timestamp():
    show = _show(datetime(2026, 4, 15, 20, 0, 0, tzinfo=timezone.utc))

    last_scraped_date = show.to_tuple()[5]
    parsed = datetime.fromisoformat(last_scraped_date)

    assert parsed.tzinfo == timezone.utc
