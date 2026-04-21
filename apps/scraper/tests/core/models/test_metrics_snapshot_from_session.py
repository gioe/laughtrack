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


def test_snapshot_roundtrip_preserves_structured_bot_block_fields():
    stats = [
        PerClubStat(
            club="Club A",
            num_shows=0,
            execution_time=1.5,
            success=True,
            bot_block_detected=True,
            bot_block_signature="datadome_captcha",
            bot_block_provider="datadome",
            bot_block_type="captcha",
            bot_block_source="captcha_body",
            bot_block_stage="direct_fetch",
            playwright_fallback_used=False,
        )
    ]
    session = ScrapingSessionResult(shows=[], errors=[], per_club_stats=stats)
    snap = ScrapingMetricsSnapshot.from_session(session, DatabaseOperationResult(), dt=datetime.now(timezone.utc))

    roundtrip = ScrapingMetricsSnapshot.from_dict(snap.to_full_json())

    assert roundtrip is not None
    club_stat = roundtrip.per_club_stats[0]
    assert club_stat.bot_block_provider == "datadome"
    assert club_stat.bot_block_type == "captcha"
    assert club_stat.bot_block_source == "captcha_body"
    assert club_stat.bot_block_stage == "direct_fetch"


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


def test_from_session_db_error_entries_appear_in_error_details():
    """error_entries on DatabaseOperationResult must populate snapshot.error_details."""
    session = ScrapingSessionResult(shows=[], errors=[], per_club_stats=[])
    db_ops = DatabaseOperationResult(
        db_errors=1,
        error_entries=[("Comedy Club", "DB error batch 1/1: connection reset by peer")],
    )

    snap = ScrapingMetricsSnapshot.from_session(session, db_ops, dt=datetime.now(timezone.utc))

    assert len(snap.error_details) == 1
    detail = snap.error_details[0]
    assert detail.club == "Comedy Club"
    assert "DB error" in (detail.error or "")


def test_from_session_scraping_and_db_errors_merged():
    """Scraping-phase errors and DB-persistence errors are both in error_details."""
    session = ScrapingSessionResult(
        shows=[],
        errors=[ErrorDetail(club="Scrape Fail Club", error="timeout", execution_time=5.0)],
        per_club_stats=[],
    )
    db_ops = DatabaseOperationResult(
        validation_errors=2,
        error_entries=[
            ("Persist Club", "Validation error batch 1/2: missing date"),
            ("Persist Club", "Validation error batch 2/2: missing title"),
        ],
    )

    snap = ScrapingMetricsSnapshot.from_session(session, db_ops, dt=datetime.now(timezone.utc))

    assert len(snap.error_details) == 3
    clubs = [d.club for d in snap.error_details]
    assert "Scrape Fail Club" in clubs
    assert clubs.count("Persist Club") == 2


def test_from_session_no_db_errors_leaves_error_details_from_scraping_only():
    """When db_ops has no error_entries, error_details matches scraping errors only."""
    session = ScrapingSessionResult(
        shows=[],
        errors=[ErrorDetail(club="Club X", error="HTTP 503", execution_time=1.2)],
        per_club_stats=[],
    )
    db_ops = DatabaseOperationResult(inserts=5)

    snap = ScrapingMetricsSnapshot.from_session(session, db_ops, dt=datetime.now(timezone.utc))

    assert len(snap.error_details) == 1
    assert snap.error_details[0].club == "Club X"
