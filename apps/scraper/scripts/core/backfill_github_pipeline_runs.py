#!/usr/bin/env python3
"""Backfill GitHub Actions workflow runs into the admin pipeline summary tables."""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _hydrate_database_env_from_url() -> None:
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


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _duration_seconds(run: dict[str, Any]) -> float:
    start = _parse_dt(run.get("run_started_at") or run.get("created_at"))
    end = _parse_dt(run.get("updated_at"))
    if not start or not end:
        return 0.0
    return max((end - start).total_seconds(), 0.0)


def _status(run: dict[str, Any]) -> str:
    conclusion = run.get("conclusion")
    if isinstance(conclusion, str) and conclusion:
        return conclusion.lower()
    status = run.get("status")
    return status.lower() if isinstance(status, str) and status else "unknown"


def _link_next(headers: list[tuple[str, str]]) -> str | None:
    link = next((value for key, value in headers if key.lower() == "link"), "")
    for part in link.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        match = re.search(r"<([^>]+)>", section)
        if match:
            return match.group(1)
    return None


def _github_request(url: str, token: str | None) -> tuple[dict[str, Any], str | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "laughtrack-pipeline-backfill",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    try:
        context = ssl.create_default_context(cafile=_certifi_ca_file())
        with urlopen(req, timeout=30, context=context) as res:
            body = json.loads(res.read().decode("utf-8"))
            return body, _link_next(res.headers.items())
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed {exc.code}: {detail}") from exc


def _github_get(url: str, token: str | None) -> dict[str, Any]:
    body, _next_url = _github_request(url, token)
    return body


def _certifi_ca_file() -> str | None:
    try:
        import certifi
    except ImportError:
        return None
    return certifi.where()


def iter_workflow_runs(
    *,
    repository: str,
    token: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repository}/actions/runs?per_page=100"
    runs: list[dict[str, Any]] = []
    while url and len(runs) < limit:
        body, next_url = _github_request(url, token)
        page_runs = body.get("workflow_runs", [])
        if not isinstance(page_runs, list):
            break
        runs.extend(page_runs)
        url = next_url
    return runs[:limit]


def _failure_summary(run: dict[str, Any], token: str | None) -> str | None:
    conclusion = _status(run)
    if conclusion == "success":
        return None

    jobs_url = run.get("jobs_url")
    if not isinstance(jobs_url, str) or not jobs_url:
        return f"Workflow concluded {conclusion}; job details were not available."

    try:
        body = _github_get(jobs_url, token)
    except RuntimeError as exc:
        return f"Workflow concluded {conclusion}; failed to load job details: {exc}"

    jobs = body.get("jobs", [])
    if not isinstance(jobs, list):
        return f"Workflow concluded {conclusion}; job details were not in the expected format."

    failed_jobs: list[str] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_conclusion = str(job.get("conclusion") or job.get("status") or "unknown").lower()
        if job_conclusion not in {"failure", "cancelled", "timed_out", "action_required"}:
            continue

        job_name = str(job.get("name") or "Unnamed job")
        failed_steps: list[str] = []
        steps = job.get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, dict):
                    continue
                step_conclusion = str(step.get("conclusion") or step.get("status") or "").lower()
                if step_conclusion in {"failure", "cancelled", "timed_out", "action_required"}:
                    failed_steps.append(str(step.get("name") or "Unnamed step"))
        if failed_steps:
            failed_jobs.append(f"{job_name}: {', '.join(failed_steps[:3])}")
        else:
            failed_jobs.append(f"{job_name}: {job_conclusion}")

    if failed_jobs:
        return "Failed jobs: " + "; ".join(failed_jobs[:5])
    return f"Workflow concluded {conclusion}; no failed job details were returned by GitHub."


def _record_from_run(run: dict[str, Any], token: str | None) -> PipelineRunRecord:
    workflow_name = str(run.get("name") or run.get("workflow_name") or "GitHub Actions")
    pipeline_key = f"github_actions_{_slug(workflow_name)}"
    run_id = str(run["id"])
    run_attempt = str(run.get("run_attempt") or 1)
    html_url = run.get("html_url")
    created_at = _parse_dt(run.get("created_at")) or datetime.now(timezone.utc)

    raw_snapshot = {
        "source": "github_actions_backfill",
        "workflow_name": workflow_name,
        "pipeline_key": pipeline_key,
        "status": _status(run),
        "run_id": run_id,
        "run_attempt": run_attempt,
        "run_number": run.get("run_number"),
        "event": run.get("event"),
        "repository": run.get("repository", {}).get("full_name"),
        "ref": run.get("head_branch"),
        "sha": run.get("head_sha"),
        "actor": run.get("actor", {}).get("login"),
        "run_url": html_url if isinstance(html_url, str) else None,
        "display_title": run.get("display_title"),
        "failure_summary": _failure_summary(run, token),
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
        "run_started_at": run.get("run_started_at"),
    }

    return PipelineRunRecord(
        pipeline_key=pipeline_key,
        run_id=run_id,
        run_attempt=run_attempt,
        status=_status(run),
        exported_at=created_at,
        duration_seconds=_duration_seconds(run),
        raw_snapshot=raw_snapshot,
    )


def _repository_from_remote() -> str | None:
    import subprocess

    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    remote = result.stdout.strip()
    if remote.startswith("git@github.com:"):
        return remote.removeprefix("git@github.com:").removesuffix(".git")
    parsed = urlparse(remote)
    if parsed.hostname == "github.com":
        return parsed.path.strip("/").removesuffix(".git")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY") or _repository_from_remote())
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--apply", action="store_true", help="Write rows to Postgres. Default is dry-run.")
    args = parser.parse_args()

    if not args.repository:
        raise SystemExit("--repository is required when the Git remote is not a GitHub repository")

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    runs = iter_workflow_runs(repository=args.repository, token=token, limit=args.limit)
    records = [_record_from_run(run, token) for run in runs]

    counts: dict[str, int] = {}
    for record in records:
        counts[record.pipeline_key] = counts.get(record.pipeline_key, 0) + 1

    print(f"Fetched {len(records)} GitHub Actions runs from {args.repository}")
    for key, count in sorted(counts.items()):
        print(f"  {key}: {count}")

    if not args.apply:
        print("Dry run only. Re-run with --apply to write scraper_runs rows.")
        return 0

    repo = PostgresMetricsRepository()
    written = 0
    for record in records:
        if repo.persist_pipeline_run(record):
            written += 1
    print(f"Inserted or updated {written}/{len(records)} pipeline run rows.")
    return 0 if written == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
