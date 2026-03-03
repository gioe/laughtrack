from datetime import datetime, timezone

import pytest

from laughtrack.core.models.metrics import ScrapingMetricsSnapshot, PerClubStat, ErrorDetail
from laughtrack.core.models.results import ScrapingSessionResult
from laughtrack.foundation.models.operation_result import DatabaseOperationResult
from laughtrack.foundation.models.types import DuplicateKeyDetails, DuplicateShowRef
from laughtrack.core.entities.show.model import Show


def make_show(idx: int = 1) -> Show:
    return Show(
        name=f"Show {idx}",
        club_id=1,
        date=datetime.now(timezone.utc),
        show_page_url=f"https://example.com/{idx}",
    )


def test_from_session_empty():
    session = ScrapingSessionResult(shows=[], errors=[], per_club_stats=[])
    db_ops = DatabaseOperationResult()

    snap = ScrapingMetricsSnapshot.from_session(session, db_ops, dt=datetime.now(timezone.utc))

    assert snap.shows.scraped == 0
    assert snap.shows.saved == 0
    assert snap.clubs.processed == 0
    assert snap.errors.total == 0
    assert snap.success_rate == 0.0


def test_from_session_updates_only():
    shows = [make_show(i) for i in range(3)]
    stats = [PerClubStat(club="Club A", num_shows=3, execution_time=1.5, success=True)]
    session = ScrapingSessionResult(shows=shows, errors=[], per_club_stats=stats)

    db_ops = DatabaseOperationResult(inserts=0, updates=3, total=3)

    snap = ScrapingMetricsSnapshot.from_session(session, db_ops, dt=datetime.now(timezone.utc))

    assert snap.shows.scraped == 3
    assert snap.shows.saved == 3
    assert snap.shows.inserted == 0
    assert snap.shows.updated == 3
    assert snap.clubs.processed == 1
    assert snap.clubs.successful == 1
    assert snap.clubs.failed == 0


def test_from_session_with_duplicates():
    shows = [make_show(1)]
    stats = [PerClubStat(club="Club A", num_shows=1, execution_time=2.0, success=True)]
    session = ScrapingSessionResult(shows=shows, errors=[], per_club_stats=stats)

    dup = DuplicateKeyDetails(
        key=(1, datetime.now(timezone.utc).isoformat(), "Main"),
        club_id=1,
        date=datetime.now(timezone.utc).isoformat(),
        room="Main",
        kept=DuplicateShowRef(name="Kept", show_page_url="https://example.com/kept"),
        dropped=[DuplicateShowRef(name="Drop 1", show_page_url=None), DuplicateShowRef(name="Drop 2", show_page_url=None)],
    )
    db_ops = DatabaseOperationResult(total=1, inserts=1, duplicate_details=[dup])

    snap = ScrapingMetricsSnapshot.from_session(session, db_ops, dt=datetime.now(timezone.utc))

    assert snap.shows.scraped == 1
    assert snap.shows.saved == 1
    assert snap.shows.skipped_dedup == 2
    assert len(snap.duplicate_show_details) == 1
    d = snap.duplicate_show_details[0]
    assert d.club_id == 1
    assert d.room == "Main"
    assert d.kept.name == "Kept"
    assert len(d.dropped) == 2
