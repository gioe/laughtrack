#!/usr/bin/env python3
"""Report Neon billing-driver usage without connecting to project databases."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


API_BASE = "https://console.neon.tech/api/v2"
METRICS = (
    "compute_unit_seconds",
    "root_branch_bytes_month",
    "child_branch_bytes_month",
    "instant_restore_bytes_month",
    "public_network_transfer_bytes",
    "private_network_transfer_bytes",
    "extra_branches_month",
)


@dataclass(frozen=True)
class MetricTotal:
    value: float
    unit: str
    display: str


class NeonApi:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            url = f"{url}?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "laughtrack-neon-usage-report/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"Neon API error {exc.code} for {url}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(f"Unable to reach Neon API: {exc.reason}") from exc


def _rfc3339(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"{value!r} is not an RFC 3339 datetime, for example 2026-07-01T00:00:00Z"
        ) from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError(f"{value!r} must include a timezone")
    return parsed.astimezone(UTC)


def _default_from(granularity: str, now: datetime) -> datetime:
    if granularity == "hourly":
        return now - timedelta(hours=24)
    if granularity == "daily":
        return now - timedelta(days=30)
    return now - timedelta(days=365)


def _metric_total(name: str, value: float) -> MetricTotal:
    if name == "compute_unit_seconds":
        cu_hours = value / 3600
        return MetricTotal(value=cu_hours, unit="CU-hours", display=f"{cu_hours:,.2f} CU-hours")
    if name.endswith("_bytes_month"):
        gb_month = value / 1_000_000_000
        return MetricTotal(value=gb_month, unit="GB-month", display=f"{gb_month:,.3f} GB-month")
    if name.endswith("_transfer_bytes"):
        gb = value / 1_000_000_000
        return MetricTotal(value=gb, unit="GB", display=f"{gb:,.3f} GB")
    if name == "extra_branches_month":
        return MetricTotal(value=value, unit="branch-month", display=f"{value:,.3f} branch-month")
    return MetricTotal(value=value, unit="raw", display=f"{value:,.3f}")


def _collect_metric_totals(project: dict[str, Any]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for period in project.get("periods", []):
        for sample in period.get("consumption", []):
            for metric in sample.get("metrics", []):
                name = metric.get("metric_name")
                if name:
                    totals[name] += float(metric.get("value") or 0)
    return dict(totals)


def _fetch_consumption(
    api: NeonApi,
    *,
    org_id: str,
    from_dt: datetime,
    to_dt: datetime,
    granularity: str,
    project_ids: list[str],
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "from": _rfc3339(from_dt),
        "to": _rfc3339(to_dt),
        "granularity": granularity,
        "org_id": org_id,
        "metrics": ",".join(METRICS),
        "limit": 100,
    }
    if project_ids:
        params["project_ids"] = ",".join(project_ids)

    projects: list[dict[str, Any]] = []
    cursor = None
    while True:
        if cursor:
            params["cursor"] = cursor
        data = api.get("/consumption_history/v2/projects", params)
        projects.extend(data.get("projects", []))
        cursor = data.get("pagination", {}).get("cursor")
        if not cursor:
            return projects


def _index_projects(api: NeonApi) -> dict[str, dict[str, Any]]:
    data = api.get("/projects", {"limit": 100})
    return {project["id"]: project for project in data.get("projects", [])}


def _fetch_branches(api: NeonApi, project_id: str) -> list[dict[str, Any]]:
    data = api.get(f"/projects/{project_id}/branches")
    return data.get("branches", [])


def _fetch_endpoints(api: NeonApi, project_id: str) -> list[dict[str, Any]]:
    data = api.get(f"/projects/{project_id}/endpoints")
    return data.get("endpoints", [])


def _print_metric_group(title: str, metrics: list[tuple[str, str, float]]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for label, metric_name, raw_value in metrics:
        total = _metric_total(metric_name, raw_value)
        print(f"{label}: {total.display}")


def _print_project_report(
    *,
    api: NeonApi,
    project_usage: dict[str, Any],
    projects_by_id: dict[str, dict[str, Any]],
    include_inventory: bool,
) -> None:
    project_id = project_usage["project_id"]
    project = projects_by_id.get(project_id, {})
    project_name = project.get("name") or project_id
    totals = _collect_metric_totals(project_usage)

    print(f"\n## {project_name} ({project_id})")
    _print_metric_group(
        "Compute",
        [("Compute usage", "compute_unit_seconds", totals.get("compute_unit_seconds", 0))],
    )
    _print_metric_group(
        "Storage",
        [
            ("Root branches", "root_branch_bytes_month", totals.get("root_branch_bytes_month", 0)),
            ("Child branches", "child_branch_bytes_month", totals.get("child_branch_bytes_month", 0)),
        ],
    )
    _print_metric_group(
        "PITR / Restore History",
        [
            (
                "Instant restore history",
                "instant_restore_bytes_month",
                totals.get("instant_restore_bytes_month", 0),
            )
        ],
    )
    _print_metric_group(
        "Network Transfer",
        [
            (
                "Public network transfer",
                "public_network_transfer_bytes",
                totals.get("public_network_transfer_bytes", 0),
            ),
            (
                "Private network transfer",
                "private_network_transfer_bytes",
                totals.get("private_network_transfer_bytes", 0),
            ),
        ],
    )
    _print_metric_group(
        "Branch Costs",
        [("Extra branches", "extra_branches_month", totals.get("extra_branches_month", 0))],
    )

    if not include_inventory:
        return

    branches = _fetch_branches(api, project_id)
    endpoints = _fetch_endpoints(api, project_id)
    endpoint_count_by_branch: dict[str, int] = defaultdict(int)
    suspended_by_branch: dict[str, int] = defaultdict(int)
    for endpoint in endpoints:
        branch_id = endpoint.get("branch_id")
        if not branch_id:
            continue
        endpoint_count_by_branch[branch_id] += 1
        if endpoint.get("current_state") == "idle":
            suspended_by_branch[branch_id] += 1

    print("\nBranch Inventory")
    print("----------------")
    print(f"Branches: {len(branches)}")
    print(f"Compute endpoints: {len(endpoints)}")
    for branch in sorted(branches, key=lambda item: (not item.get("primary"), item.get("name") or "")):
        branch_id = branch.get("id")
        name = branch.get("name") or branch_id
        primary = "primary" if branch.get("primary") else "child"
        endpoint_count = endpoint_count_by_branch.get(branch_id, 0)
        idle_count = suspended_by_branch.get(branch_id, 0)
        created_at = branch.get("created_at", "unknown-created-at")
        print(
            f"- {name} ({primary}, id={branch_id}, created={created_at}, "
            f"endpoints={endpoint_count}, idle_endpoints={idle_count})"
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Report Neon compute, storage, restore-history, network-transfer, "
            "and branch billing drivers from control-plane APIs."
        )
    )
    parser.add_argument("--org-id", default=os.environ.get("NEON_ORG_ID"), help="Neon organization ID")
    parser.add_argument(
        "--project-id",
        action="append",
        default=[],
        help="Neon project ID to include. Repeatable. Defaults to NEON_PROJECT_ID or all org projects.",
    )
    parser.add_argument(
        "--from",
        dest="from_dt",
        type=_parse_datetime,
        help="Start datetime in RFC 3339 format. Defaults by granularity.",
    )
    parser.add_argument("--to", dest="to_dt", type=_parse_datetime, help="End datetime in RFC 3339 format")
    parser.add_argument(
        "--granularity",
        choices=("hourly", "daily", "monthly"),
        default=os.environ.get("NEON_USAGE_GRANULARITY", "daily"),
    )
    parser.add_argument(
        "--no-inventory",
        action="store_true",
        help="Skip branch and endpoint inventory calls; consumption metrics are still reported.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    api_key = os.environ.get("NEON_API_KEY")
    if not api_key:
        print("NEON_API_KEY is required.", file=sys.stderr)
        return 2
    if not args.org_id:
        print("NEON_ORG_ID or --org-id is required.", file=sys.stderr)
        return 2

    now = datetime.now(UTC)
    to_dt = args.to_dt or now
    from_dt = args.from_dt or _default_from(args.granularity, to_dt)
    if from_dt >= to_dt:
        print("--from must be earlier than --to.", file=sys.stderr)
        return 2

    env_project = os.environ.get("NEON_PROJECT_ID")
    project_ids = [*args.project_id]
    if env_project and not project_ids:
        project_ids = [env_project]

    api = NeonApi(api_key)
    projects_by_id = _index_projects(api)
    usage_projects = _fetch_consumption(
        api,
        org_id=args.org_id,
        from_dt=from_dt,
        to_dt=to_dt,
        granularity=args.granularity,
        project_ids=project_ids,
    )

    print("# Neon Usage Report")
    print()
    print(f"Period: {_rfc3339(from_dt)} to {_rfc3339(to_dt)} ({args.granularity})")
    print("Source: Neon control-plane APIs only; this script does not connect to project databases.")
    print("Compute wakeups: consumption, branch, and endpoint API calls do not run SQL queries.")

    if not usage_projects:
        print("\nNo consumption records returned for the selected range.")
        return 0

    for project_usage in usage_projects:
        _print_project_report(
            api=api,
            project_usage=project_usage,
            projects_by_id=projects_by_id,
            include_inventory=not args.no_inventory,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
