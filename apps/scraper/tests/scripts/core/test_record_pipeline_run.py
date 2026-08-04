from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from scripts.core import record_pipeline_run as mod


def test_partial_status_is_preserved_in_pipeline_snapshot(monkeypatch):
    captured: dict[str, Any] = {}

    class FakeRepository:
        def persist_pipeline_run(self, record: Any) -> bool:
            captured["record"] = record
            return True

    monkeypatch.setattr(mod, "PostgresMetricsRepository", FakeRepository)
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    monkeypatch.setenv("GITHUB_REPOSITORY", "gioe/laughtrack")
    monkeypatch.setattr(
        sys,
        "argv",
        ["record_pipeline_run", "--pipeline-key", "podcast_episode_sync", "--status", "partial"],
    )

    assert mod.main() == 0

    record = captured["record"]
    assert record.status == "partial"
    assert record.raw_snapshot["status"] == "partial"
    assert record.raw_snapshot["run_url"].endswith("/actions/runs/12345")


def test_podcast_workflow_budgets_both_stages_and_records_partial_progress():
    repo_root = Path(__file__).resolve().parents[5]
    workflow = (repo_root / ".github/workflows/podcast-episode-sync.yml").read_text()

    assert "--max-runtime-seconds 2400" in workflow
    assert "--max-runtime-seconds 600" in workflow
    assert "steps.rss_sync.outputs.completed == 'true'" in workflow
    assert "steps.detect_appearances.outputs.completed == 'true'" in workflow
    assert "'success' || 'partial'" in workflow
