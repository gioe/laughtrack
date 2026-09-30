"""Retained finalizer evidence survives zero results, backoff and failures."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import yaml

from laughtrack.utilities.domain.club.coordinates import ClubGeocodingResult
from scripts.core import scrape_shows as mod


@pytest.fixture
def finalize(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "_merge_partition_snapshots", MagicMock(return_value=object()))
    monkeypatch.setattr(mod, "Logger", MagicMock())
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    metrics = MagicMock()
    clubs = SimpleNamespace(club_handler=MagicMock())

    def run():
        mod._finalize_partition_metrics(tmp_path, 4, metrics, clubs, artifact_dir=tmp_path / "evidence")

    def read(name):
        return json.loads((tmp_path / "evidence" / f"{name}.json").read_text())

    return SimpleNamespace(run=run, read=read, metrics=metrics, clubs=clubs, path=tmp_path / "evidence")


@pytest.mark.parametrize(
    "result",
    [
        ClubGeocodingResult(10, 4, 3, 2, 6, 1),
        ClubGeocodingResult(reason="no_candidates"),
        ClubGeocodingResult(reason="provider_backoff"),
        ClubGeocodingResult(reason="lock_unavailable"),
        ClubGeocodingResult(2, 0, 1, 1, 1, 0, "provider_blocked"),
    ],
)
def test_all_counts_and_stop_reasons_are_downloadable(finalize, monkeypatch, result):
    monkeypatch.setattr(mod, "geocode_missing_clubs", lambda: result)
    finalize.run()
    report = finalize.read("coordinate-enrichment")
    assert report["counts"] == {
        key: getattr(result, key) for key in ("attempted", "resolved", "unresolved", "failed", "retried", "skipped")
    }
    assert report["reason"] == result.reason
    assert report["status"] == "completed"
    assert (report["run_id"], report["run_attempt"]) == ("12345", "2")
    diagnostics = finalize.read("finalizer-diagnostics")
    assert diagnostics["status"] == "completed"
    assert diagnostics["stages"][-1] == {"stage": "coordinate_enrichment", "status": "completed"}


def test_geocoding_failure_is_not_misreported_as_zero_and_secrets_are_omitted(finalize, monkeypatch):
    secret = "https://user:secret-password@provider.invalid/?key=secret-token"
    monkeypatch.setenv("NOMINATIM_SEARCH_URL", secret)
    monkeypatch.setattr(mod, "geocode_missing_clubs", MagicMock(side_effect=RuntimeError(secret)))
    finalize.run()
    report = finalize.read("coordinate-enrichment")
    assert report["status"] == "failed"
    assert report["reason"] == "geocoding_error"
    assert all(value is None for value in report["counts"].values())
    assert finalize.read("finalizer-diagnostics")["stages"][-1]["status"] == "failed"
    for path in finalize.path.iterdir():
        assert "secret-" not in path.read_text()
        assert "provider.invalid" not in path.read_text()
    assert "secret-" not in str(mod.Logger.warn.call_args)


@pytest.mark.parametrize("failed_stage", ["merge_partition_metrics", "persist_postgres", "refresh_club_totals"])
def test_upstream_failure_retains_diagnostics_and_propagates(finalize, monkeypatch, failed_stage):
    geocode = MagicMock()
    monkeypatch.setattr(mod, "geocode_missing_clubs", geocode)
    if failed_stage == "merge_partition_metrics":
        monkeypatch.setattr(mod, "_merge_partition_snapshots", MagicMock(side_effect=ValueError("secret-token")))
    elif failed_stage == "persist_postgres":
        finalize.metrics._persist_snapshot_postgres.return_value = False
    else:
        finalize.clubs.club_handler.refresh_club_total_shows.side_effect = RuntimeError("secret-token")
    with pytest.raises((ValueError, RuntimeError)):
        finalize.run()
    geocode.assert_not_called()
    assert finalize.read("coordinate-enrichment")["status"] == "not_run"
    diagnostics = finalize.read("finalizer-diagnostics")
    assert diagnostics["status"] == "failed"
    assert diagnostics["stages"][-1] == {"stage": failed_stage, "status": "failed"}
    assert "secret-token" not in json.dumps(diagnostics)


def test_workflow_retains_only_allowlisted_diagnostics_even_on_failure():
    repo = Path(__file__).resolve().parents[5]
    workflow = yaml.safe_load((repo / ".github/workflows/scraper-schedule.yml").read_text())
    steps = workflow["jobs"]["finalize"]["steps"]
    upload = next(step for step in steps if step["name"] == "Upload finalizer diagnostics and coordinate outcomes")
    assert upload["if"] == "always()"
    assert upload["with"]["path"].splitlines() == [
        "apps/scraper/finalizer-artifacts/coordinate-enrichment.json",
        "apps/scraper/finalizer-artifacts/finalizer-diagnostics.json",
    ]
    assert upload["with"]["retention-days"] == 30
    assert upload["with"]["if-no-files-found"] == "error"
