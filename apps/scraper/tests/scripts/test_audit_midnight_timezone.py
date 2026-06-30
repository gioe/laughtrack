"""Regression guard for the audit's midnight-rate queries (TASK-3516).

``shows.date`` is a UTC ``timestamptz``. Bucketing midnight by a bare
``date::time = '00:00:00'`` reads the time-of-day in UTC, which mislabels every
evening show west of UTC as "midnight" (e.g. 7pm Central == 00:00 UTC) and
produced false time-parse alarms for zanies / esthers_follies / fareharbor.

The Section 7 queries must convert to club-local wall-clock via
``AT TIME ZONE`` before the midnight comparison. These tests pin that at the
source level so a future edit can't silently revert to UTC bucketing.
"""

import re
from pathlib import Path

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "core"
    / "audit_scraping_data.py"
)
_SOURCE = _SCRIPT_PATH.read_text()


def test_audit_script_exists():
    assert _SCRIPT_PATH.is_file()


def test_midnight_checks_use_timezone_conversion():
    """Every ``= '00:00:00'`` midnight comparison must be timezone-converted."""
    # The fully-converted pattern: the show's date is shifted into the club's
    # wall-clock via AT TIME ZONE before the time-of-day cast.
    converted = re.findall(
        r"AT TIME ZONE COALESCE\(c\.timezone, 'UTC'\)\)::time = '00:00:00'",
        _SOURCE,
    )
    # Two midnight queries: the implausible-dates query references it once
    # (midnight_upcoming); the per-scraper-rate query references it three times
    # (SELECT midnight, pct_midnight numerator, HAVING). Expect at least 4.
    assert len(converted) >= 4, (
        "midnight comparisons should be wrapped in AT TIME ZONE conversions; "
        f"found {len(converted)}"
    )


def test_no_bare_utc_midnight_comparison_remains():
    """The buggy ``date::time = '00:00:00'`` (no tz conversion) must be gone.

    Every midnight comparison must be immediately preceded by an
    ``AT TIME ZONE`` expression; a bare UTC ``date::time`` is the original bug.
    """
    for m in re.finditer(r"date::time = '00:00:00'", _SOURCE):
        prefix = _SOURCE[max(0, m.start() - 80) : m.start()]
        assert "AT TIME ZONE" in prefix, (
            "found a midnight comparison not preceded by AT TIME ZONE: "
            f"...{_SOURCE[max(0, m.start() - 40):m.start() + 20]}..."
        )


def test_midnight_queries_join_clubs_for_timezone():
    """The midnight queries must join clubs to resolve each show's timezone."""
    assert "LEFT JOIN clubs c ON c.id = s.club_id" in _SOURCE
    assert "COALESCE(c.timezone, 'UTC')" in _SOURCE
