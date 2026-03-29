"""Tests for ShowUtils.update_shows_with_results date-normalization fix.

TASK-797: show.id was left as None when show.date is a naive datetime but
psycopg2 returns the TIMESTAMPTZ column as a UTC-aware datetime.  The key
comparison in show_map then silently failed (naive != aware in Python), so
every downstream ticket insert had show_id=NULL.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytz

from laughtrack.utilities.domain.show.utils import ShowUtils


def _make_show(dt: datetime, club_id: int = 1, room: str = "") -> MagicMock:
    show = MagicMock()
    show.date = dt
    show.club_id = club_id
    show.room = room
    show.id = None
    show.operation_type = None
    return show


def _make_result(dt: datetime, db_id: int = 42, club_id: int = 1, room=None) -> dict:
    """Return a plain dict that mimics a psycopg2 DictRow."""
    return {
        "club_id": club_id,
        "date": dt,
        "room": room,
        "id": db_id,
        "operation_type": "inserted",
    }


class TestUpdateShowsWithResultsDateNormalization:
    """show.id must be populated even when date tzinfo mismatches between
    the in-memory Show and the DB RETURNING row."""

    def test_naive_show_date_matched_by_utc_aware_db_date(self):
        """Naive show.date and UTC-aware result date representing the same
        wall-clock time must produce a successful key match."""
        naive_dt = datetime(2026, 4, 18, 19, 0, 0)
        utc_aware_dt = datetime(2026, 4, 18, 19, 0, 0, tzinfo=timezone.utc)

        show = _make_show(naive_dt)
        result = _make_result(utc_aware_dt, db_id=99)

        updated = ShowUtils.update_shows_with_results([show], [result])
        assert updated[0].id == 99, (
            "show.id should be populated when naive show.date matches UTC-aware DB date"
        )

    def test_aware_show_date_with_offset_matched_by_utc_db_date(self):
        """show.date with a non-UTC offset (e.g. US/Central) must match the
        UTC-normalized DB date."""
        central = pytz.timezone("America/Chicago")
        # April 18 is CDT (UTC-5): 7 PM CDT = midnight UTC next day
        aware_central = central.localize(datetime(2026, 4, 18, 19, 0, 0))
        utc_aware = aware_central.astimezone(timezone.utc)

        show = _make_show(aware_central)
        result = _make_result(utc_aware, db_id=77)

        updated = ShowUtils.update_shows_with_results([show], [result])
        assert updated[0].id == 77, (
            "show.id should be populated when offset-aware show.date matches UTC DB date"
        )

    def test_already_utc_aware_show_date_still_matches(self):
        """A UTC-aware show.date should continue to match as before."""
        utc_dt = datetime(2026, 5, 1, 20, 0, 0, tzinfo=timezone.utc)

        show = _make_show(utc_dt)
        result = _make_result(utc_dt, db_id=55)

        updated = ShowUtils.update_shows_with_results([show], [result])
        assert updated[0].id == 55

    def test_multiple_shows_all_get_ids(self):
        """All shows in a batch get their id populated, not just timezone-matching ones."""
        naive1 = datetime(2026, 4, 18, 19, 0, 0)
        naive2 = datetime(2026, 4, 19, 21, 0, 0)
        utc1 = datetime(2026, 4, 18, 19, 0, 0, tzinfo=timezone.utc)
        utc2 = datetime(2026, 4, 19, 21, 0, 0, tzinfo=timezone.utc)

        shows = [_make_show(naive1, club_id=1), _make_show(naive2, club_id=1)]
        results = [_make_result(utc1, db_id=10), _make_result(utc2, db_id=11)]

        updated = ShowUtils.update_shows_with_results(shows, results)
        assert updated[0].id == 10
        assert updated[1].id == 11
