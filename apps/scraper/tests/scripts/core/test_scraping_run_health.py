"""Persisted stage evidence must survive partition merging and remain honest."""

from datetime import datetime, timezone

import pytest

from scripts.core.scraping_run_health import classify_run_health


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, "healthy_productive"),
        ({"bot_block_detected": True}, "recovered_productive"),
        ({"bot_block_detected": True, "fetches_failed": 1}, "partial_productive"),
        ({"success": False}, "partial_productive"),
        ({"errors": 2}, "partial_productive"),
        ({"validation_failed": 1}, "partial_productive"),
        ({"failed_save": 1}, "partial_productive"),
        ({"fetches_failed": None}, "unknown"),
        ({"errors": None, "bot_block_detected": True}, "unknown"),
        ({"num_shows": 0, "bot_block_detected": True}, "blocked_empty"),
        ({"num_shows": 0, "success": False}, "failed"),
        ({"num_shows": 0, "fetches_failed": 1}, "failed"),
        ({"num_shows": 0, "http_status": 403}, "failed"),
        ({"num_shows": 0}, "healthy_empty"),
        ({"num_shows": 0, "fetches_ok": None}, "unknown"),
        ({"num_shows": 0, "items_before_filter": 5}, "unknown"),
        ({"num_shows": 0, "items_before_filter": None}, "unknown"),
        ({"num_shows": None}, "unknown"),
        ({"num_shows": "5"}, "unknown"),
        ({"num_shows": -1}, "unknown"),
        ({"fetches_failed": False}, "unknown"),
        ({"fetches_failed": "0"}, "unknown"),
        ({"fetches_failed": 0.5}, "unknown"),
    ],
)
def test_classification(overrides, expected):
    row = dict(
        success=True,
        num_shows=3,
        bot_block_detected=False,
        fetches_ok=1,
        fetches_failed=0,
        errors=0,
        items_before_filter=0,
    )
    row.update(overrides)
    assert classify_run_health(row) == expected


def test_legacy_zero_is_not_proven_empty_calendar():
    assert classify_run_health(dict(success=True, num_shows=0)) == "unknown"


def test_stage_counters_survive_result_snapshot_and_partition_roundtrip():
    from laughtrack.core.models.metrics import ScrapingMetricsSnapshot
    from laughtrack.core.models.results import ClubScrapingResult
    from laughtrack.core.services.metrics.aggregator import MetricsAggregator
    from laughtrack.core.services.metrics.postgres_repository import PostgresMetricsRepository
    from laughtrack.foundation.models.operation_result import DatabaseOperationResult
    import json

    result = ClubScrapingResult(
        club_name="Partial fixture",
        shows=[],
        execution_time=1.0,
        club_id=123,
        targets_collected=4,
        fetches_ok=3,
        fetches_failed=1,
        items_before_filter=5,
    )
    session = MetricsAggregator().aggregate([result])
    snapshot = ScrapingMetricsSnapshot.from_session(session, DatabaseOperationResult(), dt=datetime.now(timezone.utc))
    restored = ScrapingMetricsSnapshot.from_json(snapshot.to_full_json(), snapshot.timestamp, snapshot.datetime)
    stat = restored.per_club_stats[0]
    assert (stat.targets_collected, stat.fetches_ok, stat.fetches_failed) == (4, 3, 1)
    # Exercise the production writer's actual raw_stat payload, not just asdict.
    repository = PostgresMetricsRepository()
    db_row = next(repository._club_rows(1, [(stat, 123)]))
    raw = db_row[-1]
    if hasattr(raw, "adapted"):
        raw = raw.adapted
    if isinstance(raw, str):
        raw = json.loads(raw)
    assert raw["fetches_failed"] == 1
    assert raw["fetches_ok"] == 3
    assert raw["targets_collected"] == 4


def test_legacy_partition_snapshot_preserves_unknown_counters():
    from laughtrack.core.models.metrics import ScrapingMetricsSnapshot

    stat = ScrapingMetricsSnapshot._parse_per_club_stats([{"club": "legacy", "success": True, "num_shows": 0}])[0]
    assert stat.fetches_ok is None
    assert stat.fetches_failed is None
    assert stat.targets_collected is None
