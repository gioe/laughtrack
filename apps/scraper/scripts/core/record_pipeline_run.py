#!/usr/bin/env python3
"""Persist a GitHub Actions workflow run into the admin pipeline summary tables."""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _hydrate_database_env_from_url() -> None:
    """Let workflow jobs with only DATABASE_URL use the scraper DB connection stack."""
    if all(os.getenv(key) for key in ("DATABASE_NAME", "DATABASE_USER", "DATABASE_HOST", "DATABASE_PASSWORD")):
        return

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return

    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        return

    os.environ.setdefault("DATABASE_NAME", parsed.path.lstrip("/"))
    if parsed.username:
        os.environ.setdefault("DATABASE_USER", unquote(parsed.username))
    if parsed.password:
        os.environ.setdefault("DATABASE_PASSWORD", unquote(parsed.password))
    if parsed.hostname:
        os.environ.setdefault("DATABASE_HOST", parsed.hostname)
    if parsed.port:
        os.environ.setdefault("DATABASE_PORT", str(parsed.port))


_hydrate_database_env_from_url()

from laughtrack.core.services.metrics.postgres_repository import (  # noqa: E402
    PipelineRunRecord,
    PostgresMetricsRepository,
)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "github_actions"


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _run_url(repository: str, run_id: str) -> str | None:
    server_url = _env("GITHUB_SERVER_URL", "https://github.com")
    if not repository or not run_id:
        return None
    return f"{server_url}/{repository}/actions/runs/{run_id}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a GitHub Actions workflow run in scraper_runs.",
    )
    parser.add_argument("--pipeline-key", default="")
    parser.add_argument("--workflow-name", default=_env("GITHUB_WORKFLOW", "GitHub Actions"))
    parser.add_argument("--status", default="")
    parser.add_argument("--duration-seconds", type=float, default=0.0)
    parser.add_argument("--failure-summary", default=_env("GITHUB_FAILURE_SUMMARY"))
    args = parser.parse_args()

    workflow_name = args.workflow_name
    pipeline_key = args.pipeline_key or f"github_actions_{_slug(workflow_name)}"
    run_id = _env("GITHUB_RUN_ID")
    run_attempt = _env("GITHUB_RUN_ATTEMPT", "1")
    status = (args.status or _env("GITHUB_JOB_STATUS") or "unknown").lower()
    if status not in {"success", "failure", "cancelled", "skipped"}:
        status = "failure"

    if not run_id:
        raise SystemExit("GITHUB_RUN_ID is required to record a pipeline run")

    repository = _env("GITHUB_REPOSITORY")
    raw_snapshot = {
        "source": "github_actions",
        "workflow_name": workflow_name,
        "pipeline_key": pipeline_key,
        "status": status,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "run_number": _env("GITHUB_RUN_NUMBER"),
        "job": _env("GITHUB_JOB"),
        "event": _env("GITHUB_EVENT_NAME"),
        "repository": repository,
        "ref": _env("GITHUB_REF"),
        "sha": _env("GITHUB_SHA"),
        "actor": _env("GITHUB_ACTOR"),
        "run_url": _run_url(repository, run_id),
        "failure_summary": args.failure_summary or None,
    }

    ok = PostgresMetricsRepository().persist_pipeline_run(
        PipelineRunRecord(
            pipeline_key=pipeline_key,
            run_id=run_id,
            run_attempt=run_attempt,
            status=status,
            exported_at=datetime.now(timezone.utc),
            duration_seconds=max(args.duration_seconds, 0.0),
            raw_snapshot=raw_snapshot,
        ),
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
