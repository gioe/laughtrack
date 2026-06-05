"""Unit tests for scripts/utils/fetch_scraper_dashboard_artifact.py."""

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

_SCRAPER_ROOT = Path(__file__).resolve().parents[2]  # apps/scraper/
_SCRIPT_PATH = _SCRAPER_ROOT / "scripts" / "utils" / "fetch_scraper_dashboard_artifact.py"
_MODULE_NAME = "fetch_scraper_dashboard_artifact"


def _load_module() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(_MODULE_NAME, str(_SCRIPT_PATH))
    spec = importlib.util.spec_from_loader(_MODULE_NAME, loader)
    if spec is None:
        raise AssertionError(f"Could not load spec for {_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    original = sys.modules.get(_MODULE_NAME)
    try:
        sys.modules[_MODULE_NAME] = module
        loader.exec_module(module)
        return module
    finally:
        if original is None:
            sys.modules.pop(_MODULE_NAME, None)
        else:
            sys.modules[_MODULE_NAME] = original


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(["gh"], returncode, stdout=stdout, stderr=stderr)


def test_main_downloads_matching_artifact_and_prints_metrics_path(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    calls = []

    def fake_run_gh(args):
        calls.append(args)
        if args[0] == "api":
            return _completed(json.dumps({"artifacts": [{"name": "scraper-dashboard-123"}, {"name": "logs"}]}))
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()
        (metrics_dir / "metrics_20260605_010203.json").write_text("{}", encoding="utf-8")
        return _completed()

    monkeypatch.setattr(mod, "_run_gh", fake_run_gh)

    rc = mod.main(["123", "--output-dir", str(tmp_path)])

    assert rc == 0
    assert calls == [
        ["api", "repos/gioe/laughtrack/actions/runs/123/artifacts?per_page=100"],
        ["run", "download", "123", "-n", "scraper-dashboard-123", "-D", str(tmp_path)],
    ]
    captured = capsys.readouterr()
    assert f"Metrics JSON: {tmp_path / 'metrics' / 'metrics_20260605_010203.json'}" in captured.out


def test_main_uses_fresh_tmp_dir_by_default(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    fresh_dir = tmp_path / "laughtrack-scraper-dashboard-123-abc"

    def fake_run_gh(args):
        if args[0] == "api":
            return _completed(json.dumps({"artifacts": [{"name": "scraper-dashboard-123"}]}))
        assert args[-1] == str(fresh_dir)
        metrics_dir = fresh_dir / "metrics"
        metrics_dir.mkdir(parents=True)
        (metrics_dir / "metrics_20260605_010203.json").write_text("{}", encoding="utf-8")
        return _completed()

    monkeypatch.setattr(mod.tempfile, "mkdtemp", lambda prefix: str(fresh_dir))
    monkeypatch.setattr(mod, "_run_gh", fake_run_gh)

    rc = mod.main(["123"])

    assert rc == 0
    captured = capsys.readouterr()
    assert f"Download directory: {fresh_dir}" in captured.out


def test_main_lists_available_artifacts_when_dashboard_is_absent(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    payload = {"artifacts": [{"name": "scraper-logs-123"}, {"name": "web-report"}]}
    monkeypatch.setattr(mod, "_run_gh", lambda _args: _completed(json.dumps(payload)))

    rc = mod.main(["123", "--output-dir", str(tmp_path)])

    assert rc == 1
    captured = capsys.readouterr()
    assert "no scraper dashboard artifact found for run 123" in captured.err
    assert "scraper-logs-123" in captured.err
    assert "web-report" in captured.err


def test_main_rejects_nonmatching_dashboard_artifact(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    monkeypatch.setattr(
        mod,
        "_run_gh",
        lambda _args: _completed(json.dumps({"artifacts": [{"name": "scraper-dashboard-older-name"}]})),
    )

    rc = mod.main(["123", "--output-dir", str(tmp_path)])

    assert rc == 1
    captured = capsys.readouterr()
    assert "no scraper dashboard artifact found for run 123" in captured.err
    assert "scraper-dashboard-older-name" in captured.err


def test_main_reports_gh_api_errors(monkeypatch, tmp_path, capsys):
    mod = _load_module()
    monkeypatch.setattr(mod, "_run_gh", lambda _args: _completed(stderr="not authenticated", returncode=1))

    rc = mod.main(["123", "--output-dir", str(tmp_path)])

    assert rc == 1
    captured = capsys.readouterr()
    assert "Failed to list artifacts for run 123: not authenticated" in captured.err
