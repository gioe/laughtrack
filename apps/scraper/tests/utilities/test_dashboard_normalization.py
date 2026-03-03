"""Tests for dashboard normalization handling nested schema variants."""
from __future__ import annotations

from datetime import datetime
from laughtrack.core.dashboard.normalization import normalize_metrics


def test_normalize_metrics_nested_schema():
    sample = {
        "session": {"exported_at": "2025-09-08T20:40:53.665234"},
        "shows": {
            "scraped": 378,
            "saved": 374,
            "inserted": 0,
            "updated": 374,
            "failed_save": 0,
            "skipped_dedup": 4,
            "validation_failed": 0,
            "db_errors": 0,
        },
        "clubs": {"processed": 1, "successful": 1, "failed": 0},
        "errors": {"total": 0},
        "success_rate": 98.94,
        "per_club_stats": [
            {"club": "The Broadway Comedy Club", "num_shows": 378, "success": True},
        ],
        "duplicate_show_details": [],
    }
    result = normalize_metrics([sample])
    assert len(result) == 1
    sess = result[0]
    snap = sess["snapshot"]
    assert snap.shows.scraped == 378
    assert snap.shows.saved == 374
    assert snap.shows.updated == 374
    assert snap.shows.skipped_dedup == 4
    assert snap.errors.total == 0
    assert snap.clubs.processed == 1
    assert 98.0 < snap.success_rate < 100.0
    assert snap.per_club_stats[0].club == "The Broadway Comedy Club"
