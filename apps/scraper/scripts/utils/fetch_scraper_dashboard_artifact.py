#!/usr/bin/env python3
"""Download a GitHub Actions scraper dashboard artifact for a run id."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_REPO = "gioe/laughtrack"
ARTIFACT_PREFIX = "scraper-dashboard-"


def _run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _load_artifacts(payload: str) -> list[dict[str, Any]]:
    data = json.loads(payload)
    artifacts = data.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("GitHub API response did not contain an artifacts list")
    return [artifact for artifact in artifacts if isinstance(artifact, dict)]


def _artifact_names(artifacts: list[dict[str, Any]]) -> list[str]:
    names = [artifact.get("name") for artifact in artifacts]
    return sorted(name for name in names if isinstance(name, str))


def _find_dashboard_artifact(artifacts: list[dict[str, Any]], run_id: str) -> str | None:
    expected = f"{ARTIFACT_PREFIX}{run_id}"
    names = _artifact_names(artifacts)
    if expected in names:
        return expected
    return None


def _find_metrics_json(download_dir: Path) -> Path | None:
    metrics_files = sorted(
        download_dir.rglob("metrics/*.json"),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )
    return metrics_files[0] if metrics_files else None


def fetch_artifacts(repo: str, run_id: str) -> list[dict[str, Any]]:
    result = _run_gh(
        [
            "api",
            f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100",
        ]
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "gh api failed"
        raise RuntimeError(f"Failed to list artifacts for run {run_id}: {message}")
    return _load_artifacts(result.stdout)


def download_artifact(run_id: str, artifact_name: str, download_dir: Path) -> None:
    download_dir.mkdir(parents=True, exist_ok=True)
    result = _run_gh(["run", "download", run_id, "-n", artifact_name, "-D", str(download_dir)])
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "gh run download failed"
        raise RuntimeError(f"Failed to download artifact '{artifact_name}': {message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download scraper-dashboard-<run_id> from GitHub Actions and print the metrics JSON path."
    )
    parser.add_argument("run_id", help="GitHub Actions run id")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repo, default: {DEFAULT_REPO}")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Download directory, default: /tmp/laughtrack-scraper-dashboard-<run_id>",
    )
    args = parser.parse_args(argv)

    run_id = str(args.run_id)
    download_dir = args.output_dir or Path(tempfile.gettempdir()) / f"laughtrack-scraper-dashboard-{run_id}"

    try:
        artifacts = fetch_artifacts(args.repo, run_id)
    except (json.JSONDecodeError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    artifact_name = _find_dashboard_artifact(artifacts, run_id)
    if artifact_name is None:
        names = _artifact_names(artifacts)
        print(f"ERROR: no scraper dashboard artifact found for run {run_id}.", file=sys.stderr)
        if names:
            print("Available artifacts:", file=sys.stderr)
            for name in names:
                print(f"  - {name}", file=sys.stderr)
        else:
            print("Available artifacts: none", file=sys.stderr)
        return 1

    try:
        download_artifact(run_id, artifact_name, download_dir)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    metrics_path = _find_metrics_json(download_dir)
    print(f"Artifact: {artifact_name}")
    print(f"Download directory: {download_dir}")
    if metrics_path is None:
        print(f"ERROR: downloaded artifact did not contain metrics/*.json under {download_dir}", file=sys.stderr)
        return 1

    print(f"Metrics JSON: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
