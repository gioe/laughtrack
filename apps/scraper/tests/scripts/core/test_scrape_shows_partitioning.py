"""Deterministic partitioning and completed-run aggregation contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

_scraper_root = Path(__file__).resolve().parents[3]
for path in (str(_scraper_root / "src"), str(_scraper_root)):
    if path not in sys.path:
        sys.path.insert(0, path)

from laughtrack.core.models.metrics import ScrapingMetricsSnapshot  # noqa: E402
from laughtrack.core.models.domain_metrics import ScrapingRunSummary  # noqa: E402
from laughtrack.core.models.metrics_snapshot import (  # noqa: E402
    ClubsBlock,
    ErrorsBlock,
    SessionBlock,
    ShowsBlock,
)
from laughtrack.core.services.scraping.service import (  # noqa: E402
    ScrapingService,
    _scrape_target_partition_key,
    _select_scrape_partition,
)
from laughtrack.core.services.metrics import MetricsService  # noqa: E402
from laughtrack.foundation.models.operation_result import DatabaseOperationResult  # noqa: E402
from scripts.core import scrape_shows as mod  # noqa: E402


def _target(
    target_id: int,
    *,
    source_target_id: int | None = None,
    production_company_id: int | None = None,
):
    source = SimpleNamespace(source_target_id=source_target_id) if source_target_id is not None else None
    return SimpleNamespace(
        id=target_id,
        is_synthetic=source_target_id is not None,
        active_scraping_source=source,
        scraping_source=source,
        production_company_id=production_company_id,
    )


def test_partition_keys_keep_target_namespaces_distinct():
    assert _scrape_target_partition_key(_target(7)) == "club:7"
    assert _scrape_target_partition_key(_target(7, source_target_id=7)) == "source_target:7"
    assert _scrape_target_partition_key(_target(0, production_company_id=7)) == "production_company:7"


def test_partitions_are_deterministic_disjoint_and_exhaustive():
    targets = [_target(i) for i in range(1, 31)]
    targets += [_target(0, source_target_id=91), _target(0, production_company_id=44)]

    partitions = [
        _select_scrape_partition(list(reversed(targets)), index, 3)
        for index in range(3)
    ]
    partition_keys = [
        {_scrape_target_partition_key(target) for target in partition}
        for partition in partitions
    ]
    all_keys = {_scrape_target_partition_key(target) for target in targets}

    assert all(
        left.isdisjoint(right)
        for index, left in enumerate(partition_keys)
        for right in partition_keys[index + 1 :]
    )
    assert set().union(*partition_keys) == all_keys
    for partition, keys in zip(partitions, partition_keys, strict=True):
        assert [_scrape_target_partition_key(target) for target in partition] == sorted(keys)


def test_adding_a_target_does_not_move_existing_partition_assignments():
    targets = [_target(i) for i in range(1, 20)]
    assignments = {
        _scrape_target_partition_key(target): index
        for index in range(3)
        for target in _select_scrape_partition(targets, index, 3)
    }
    with_new_target = targets + [_target(999)]
    new_assignments = {
        _scrape_target_partition_key(target): index
        for index in range(3)
        for target in _select_scrape_partition(with_new_target, index, 3)
    }

    assert all(new_assignments[key] == index for key, index in assignments.items())


def _snapshot(exported_at: str, *, scraped: int, saved: int, clubs: int):
    return ScrapingMetricsSnapshot(
        timestamp=exported_at,
        datetime=mod.dt.datetime.fromisoformat(exported_at),
        session=SessionBlock(duration_seconds=10, exported_at=exported_at),
        shows=ShowsBlock(scraped=scraped, saved=saved, inserted=saved),
        clubs=ClubsBlock(processed=clubs, successful=clubs, failed=0),
        errors=ErrorsBlock(total=0),
        success_rate=100.0,
        run_type="scraper_partition",
    )


def test_merge_requires_every_partition_and_publishes_one_full_snapshot(tmp_path):
    for index, snapshot in enumerate(
        [
            _snapshot("2026-08-04T10:00:00+00:00", scraped=8, saved=7, clubs=3),
            _snapshot("2026-08-04T10:01:00+00:00", scraped=5, saved=5, clubs=2),
        ]
    ):
        directory = tmp_path / f"partition-{index}" / "metrics"
        directory.mkdir(parents=True)
        (directory / f"metrics_{index}.json").write_text(json.dumps(snapshot.to_full_json()), encoding="utf-8")

    merged = mod._merge_partition_snapshots(tmp_path, expected_partitions=2)

    assert merged.run_type == "scraper"
    assert merged.shows.scraped == 13
    assert merged.shows.saved == 12
    assert merged.clubs.processed == 5
    assert merged.success_rate == pytest.approx(12 / 13 * 100)


def test_partition_metrics_defer_email_until_full_snapshot_is_finalized(tmp_path):
    with patch.object(MetricsService, "__init__", lambda self: None):
        metrics_service = MetricsService()
    metrics_service._aggregator = MagicMock()
    metrics_service._generate_and_save_dashboard = MagicMock()
    metrics_service._process_latest_session_and_email = MagicMock()

    metrics_service.end_session(
        [], DatabaseOperationResult(), run_type="scraper_partition"
    )

    metrics_service._process_latest_session_and_email.assert_not_called()

    for index, snapshot in enumerate(
        [
            _snapshot("2026-08-04T10:00:00+00:00", scraped=1, saved=1, clubs=1),
            _snapshot("2026-08-04T10:01:00+00:00", scraped=1, saved=1, clubs=1),
        ]
    ):
        directory = tmp_path / f"partition-{index}" / "metrics"
        directory.mkdir(parents=True)
        (directory / f"metrics_{index}.json").write_text(
            json.dumps(snapshot.to_full_json()), encoding="utf-8"
        )

    metrics_service._render_and_save_dashboard = MagicMock()
    metrics_service._persist_snapshot_json = MagicMock()
    metrics_service._persist_snapshot_postgres = MagicMock(return_value=True)
    club_service = SimpleNamespace(
        club_handler=SimpleNamespace(refresh_club_total_shows=MagicMock())
    )
    with patch.object(mod, "geocode_missing_clubs"):
        mod._finalize_partition_metrics(
            tmp_path,
            expected_partitions=2,
            metrics_service=metrics_service,
            club_service=club_service,
        )

    metrics_service._process_latest_session_and_email.assert_called_once_with()


def test_partition_run_uses_non_health_metrics_and_defers_global_side_effects():
    with patch.object(ScrapingService, "__init__", lambda self: None):
        service = ScrapingService()
    club = _target(10)
    club.club_type = "club"
    service.club_handler = MagicMock()
    service.club_handler.get_all_clubs.return_value = [club]
    service.club_handler.get_all_source_targets.return_value = []
    service._result_processor = MagicMock()

    with (
        patch.object(service, "_try_validate_scraper_keys"),
        patch.object(
            service,
            "_scrape_clubs_with_metrics",
            return_value=([], ScrapingRunSummary(), DatabaseOperationResult()),
        ),
        patch.object(
            service,
            "_scrape_production_companies",
            return_value=([], ScrapingRunSummary(), DatabaseOperationResult()),
        ) as scrape_production_companies,
        patch.object(service, "_emit_summary"),
        patch.object(service, "_check_and_alert") as check_alert,
        patch.object(service, "_send_run_summary") as send_summary,
        patch.object(service, "_geocode_missing_clubs_after_scrape") as geocode,
    ):
        service.scrape_all_clubs(
            partition_index=0,
            partition_count=1,
            include_production_companies=False,
        )

    assert service.result_processor.process_results.call_args.kwargs["run_type"] == "scraper_partition"
    check_alert.assert_not_called()
    send_summary.assert_not_called()
    geocode.assert_not_called()
    scrape_production_companies.assert_not_called()
    service.club_handler.refresh_club_total_shows.assert_not_called()


def test_production_company_phase_runs_after_venues_and_defers_global_side_effects():
    with patch.object(ScrapingService, "__init__", lambda self: None):
        service = ScrapingService()
    club = _target(10)
    club.club_type = "club"
    service.club_handler = MagicMock()
    service.club_handler.get_all_clubs.return_value = [club]
    service._result_processor = MagicMock()

    with (
        patch.object(service, "_filter_off_season_festivals", return_value=[club]),
        patch.object(
            service,
            "_scrape_production_companies",
            return_value=([], ScrapingRunSummary(), DatabaseOperationResult()),
        ) as scrape_production_companies,
        patch.object(service, "_emit_summary"),
        patch.object(service, "_geocode_missing_clubs_after_scrape") as geocode,
    ):
        service.scrape_all_production_companies()

    scrape_production_companies.assert_called_once_with([club])
    assert service.result_processor.process_results.call_args.kwargs["run_type"] == "scraper_partition"
    geocode.assert_not_called()
    service.club_handler.refresh_club_total_shows.assert_not_called()


def test_merge_rejects_missing_or_non_partition_snapshots(tmp_path):
    directory = tmp_path / "partition-0" / "metrics"
    directory.mkdir(parents=True)
    snapshot = _snapshot("2026-08-04T10:00:00+00:00", scraped=1, saved=1, clubs=1)
    (directory / "metrics_0.json").write_text(json.dumps(snapshot.to_full_json()), encoding="utf-8")

    with pytest.raises(ValueError, match="Expected 2"):
        mod._merge_partition_snapshots(tmp_path, expected_partitions=2)

    snapshot.run_type = "scraper"
    (directory / "metrics_0.json").write_text(json.dumps(snapshot.to_full_json()), encoding="utf-8")
    with pytest.raises(ValueError, match="scraper_partition"):
        mod._merge_partition_snapshots(tmp_path, expected_partitions=1)


def test_keyboard_interrupt_exits_nonzero_for_partition_recording(monkeypatch):
    class InterruptedService:
        def scrape_all_clubs(self, **_kwargs):
            raise KeyboardInterrupt

    monkeypatch.setattr(mod, "ScrapingService", InterruptedService)
    monkeypatch.setattr(
        mod,
        "ClubService",
        lambda: SimpleNamespace(club_handler=SimpleNamespace()),
    )
    monkeypatch.setattr(mod, "ScraperService", lambda: SimpleNamespace())
    monkeypatch.setattr(mod, "MetricsService", lambda: SimpleNamespace())
    monkeypatch.setattr(mod, "validate_eventbrite_token", lambda: None)
    monkeypatch.setattr(mod.scraper_proxy_registry, "log_proxy_status", lambda: None)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scrape_shows.py", "--all", "--partition-index", "0", "--partition-count", "2"],
    )

    with pytest.raises(SystemExit) as exc_info:
        mod.main()

    assert exc_info.value.code == 130


def test_workflow_gates_downstream_work_and_records_unique_partitions():
    repo_root = Path(__file__).resolve().parents[5]
    workflow = (repo_root / ".github/workflows/scraper-schedule.yml").read_text()
    action = (repo_root / ".github/actions/record-pipeline-run/action.yml").read_text()

    assert "fail-fast: false" in workflow
    assert "needs: scrape_partition" in workflow
    assert "needs: [scrape_partition, scrape_production_companies]" in workflow
    assert "needs.scrape_production_companies.result == 'success'" in workflow
    assert 'MAX_CONCURRENT_CLUBS: "6"' in workflow
    assert "partition_number: 3" in workflow
    assert "--partition-count 3" in workflow
    assert "--skip-production-companies" in workflow
    assert "--production-companies-only" in workflow
    assert "if-no-files-found: error" in workflow
    assert "pattern: scraper-metrics-${{ github.run_id }}-*" in workflow
    assert "--expected-partitions 4" in workflow
    merge_step = workflow.split("- name: Publish full scraper metrics snapshot", 1)[1]
    assert "EMAIL_SMTP_USERNAME: ${{ secrets.EMAIL_SMTP_USERNAME }}" in merge_step
    assert "ALERT_RECIPIENTS: ${{ secrets.ALERT_RECIPIENTS }}" in merge_step
    assert "github_actions_scraper_pipeline_partition_${{ matrix.partition_index }}_of_3" in workflow
    assert "actions/download-artifact@v8" in workflow
    assert "pipeline-key:" in action
