"""Collect blind SeatEngine evidence without classification or database writes."""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
BASELINE = ROOT / "docs/audits/comedy-blind-exclusions-2026-10-11.json"
COHORT = {192: (61, "53"), 527: (475, "450"), 595: (476, "451")}
WORKFLOW = "comedy-blind-snapshot.yml"
PREFIX = "comedy-blind-history-"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_new(path, value):
    """Never replace an evidence artifact, including on a repeated local run."""
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def load_history(baseline, previous=None):
    pairs = {(r["source_id"], str(r["event_id"])) for r in baseline["excluded_groups"]}
    if len(pairs) != 173 or any(s not in COHORT or not e.isdigit() for s, e in pairs):
        raise ValueError("Expected the frozen 173-group exclusion cohort")
    expected = digest(baseline)
    if previous is None:
        return {"version": 1, "baseline_digest": expected, "snapshots": [], "runs": []}
    if previous.get("version") != 1 or previous.get("baseline_digest") != expected:
        raise ValueError("History baseline/version mismatch")
    seen = set()
    for snapshot in previous["snapshots"]:
        key = (snapshot["source_id"], snapshot["event_id"])
        if key in pairs or key in seen or key[0] not in COHORT:
            raise ValueError("Invalid or duplicated historical native group")
        if snapshot["sha256"] != digest(snapshot["evidence"]):
            raise ValueError("Historical snapshot digest mismatch")
        seen.add(key)
    return json.loads(json.dumps(previous))


def validate_source(row):
    from laughtrack.core.entities.club.model import ScrapingSource

    sid = row["id"]
    typed = ScrapingSource.from_dict(row)
    if (
        sid not in COHORT
        or row["club_id"] != COHORT[sid][0]
        or row["enabled"] is not True
        or row["scraper_key"] != "seatengine"
        or row.get("source_target_id")
        or str(typed.typed_id_for_platform("seatengine")) != COHORT[sid][1]
        or "seatengine_venue_routes" in (row.get("metadata") or {})
    ):
        raise ValueError("Source identity, enablement or routing changed")
    return typed


def load_clients():
    """All source/venue reads share an explicitly read-only transaction."""
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    from laughtrack.adapters.db import get_connection
    from laughtrack.core.clients.seatengine.client import SeatEngineClient
    from laughtrack.core.entities.club.model import Club

    clients = {}
    with get_connection(autocommit=False) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            cursor.execute("SELECT * FROM scraping_sources WHERE id=ANY(%s) ORDER BY id", (list(COHORT),))
            rows = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]
            if {r["id"] for r in rows} != set(COHORT):
                raise ValueError("A selected source is missing")
            for row in rows:
                typed = validate_source(row)
                cursor.execute("SELECT * FROM clubs WHERE id=%s", (row["club_id"],))
                found = cursor.fetchone()
                if found is None:
                    raise ValueError("Source venue missing")
                club_row = dict(zip([c[0] for c in cursor.description], found))
                club = Club.from_db_row({**club_row, "scraping_sources": [row]})
                club.active_scraping_source = typed
                clients[row["id"]] = SeatEngineClient(club)
        conn.rollback()
    return clients


def project_group(events):
    """Retain provider evidence, never HTML/forms, headers or source credentials."""
    result = []
    for raw in events:
        event = raw["event"]
        result.append(
            {
                "id": str(raw["id"]),
                "start_date_time": raw.get("start_date_time"),
                "sold_out": raw.get("sold_out"),
                "event": {k: event.get(k) for k in ("id", "name", "status", "labels", "venue_id", "cancelled_at")},
                "talents": [
                    {k: t.get(k) for k in ("id", "name", "role")}
                    for t in event.get("talents", [])
                    if isinstance(t, dict)
                ],
            }
        )
    return result


async def collect(clients, baseline, previous, run_id, *, now=None):
    history = load_history(baseline, previous)
    if any(r["run_id"] == run_id for r in history["runs"]):
        raise ValueError("Run identity already recorded")
    started = now or datetime.now(timezone.utc).isoformat()
    excluded = {(r["source_id"], str(r["event_id"])) for r in baseline["excluded_groups"]}
    seen = {(s["source_id"], s["event_id"]) for s in history["snapshots"]}
    report = {
        "run_id": run_id,
        "started_at": started,
        "sources": [],
        "model_calls": 0,
        "classification_calls": 0,
        "database_writes": 0,
        "new_groups": 0,
    }
    for sid in sorted(COHORT):
        client = clients[sid]
        data = await asyncio.wait_for(
            client.fetch_json(
                f"https://services.seatengine.com/api/v1/venues/{COHORT[sid][1]}/shows", headers=client.headers
            ),
            45,
        )
        events = data.get("data", data.get("shows")) if isinstance(data, dict) else None
        if not isinstance(events, list):
            raise ValueError("Invalid provider calendar response")
        grouped = defaultdict(list)
        for event in events:
            group = event.get("event") if isinstance(event, dict) else None
            if (
                not isinstance(group, dict)
                or not str(group.get("id", "")).isdigit()
                or not str(event.get("id", "")).isdigit()
                or str(group.get("venue_id")) != COHORT[sid][1]
            ):
                raise ValueError("Provider event identity/venue mismatch")
            grouped[str(group["id"])].append(event)
        fresh = sorted((g for g in grouped if (sid, g) not in excluded | seen), key=int)
        selected = fresh[:50]
        status = {
            "source_id": sid,
            "club_id": COHORT[sid][0],
            "venue_id": COHORT[sid][1],
            "provider_occurrences": len(events),
            "provider_groups": len(grouped),
            "new_groups": len(selected),
            "deferred_by_budget": len(fresh) - len(selected),
            "detail_status": {},
        }
        if selected:
            venue = await asyncio.wait_for(client.fetch_venue_details(COHORT[sid][1]), 30)
            client.venue_website = (venue or {}).get("website") or ""
            expected_host = {
                192: "goodnightscomedy.com",
                527: "santamonica.harvelles.com",
                595: "longbeach.harvelles.com",
            }[sid]
            parts = urlsplit(client.venue_website)
            if (
                parts.scheme not in {"http", "https"}
                or (parts.hostname or "").removeprefix("www.") != expected_host
                or parts.username
                or parts.password
                or parts.query
                or parts.fragment
            ):
                raise ValueError("Unreviewed provider public website")
            # Existing helper bounds concurrency=4, request=10s, total=45s and validates same-event pages.
            selected_events = [e for g in selected for e in grouped[g]]
            for event in selected_events:
                url = urlsplit(client._build_public_show_url(event["id"]))
                if (
                    (url.hostname or "").removeprefix("www.") != expected_host
                    or url.username
                    or url.password
                    or url.query
                    or url.fragment
                    or url.path.rstrip("/") != f"/shows/{event['id']}"
                ):
                    raise ValueError("Unreviewed public event URL")
            enriched = await asyncio.wait_for(client.collect_event_descriptions(selected_events), 55)
            markers = {str(e["event"]["id"]): e.get("_comedy_event_detail", {}) for e in enriched}
            for gid in selected:
                marker = markers.get(gid, {"status": "unavailable"})
                detail = {
                    k: marker[k] for k in ("status", "event_id", "show_id", "selector", "url", "text") if k in marker
                }
                evidence = {"provider_occurrences": project_group(grouped[gid]), "detail": detail}
                history["snapshots"].append(
                    {
                        "source_id": sid,
                        "event_id": gid,
                        "first_seen_at": started,
                        "run_id": run_id,
                        "evidence": evidence,
                        "sha256": digest(evidence),
                    }
                )
                state = detail.get("status", "unavailable")
                status["detail_status"][state] = status["detail_status"].get(state, 0) + 1
                seen.add((sid, gid))
        report["sources"].append(status)
        report["new_groups"] += len(selected)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["total_captured_groups"] = len(history["snapshots"])
    report["previous_history_digest"] = digest(previous) if previous else None
    history["runs"].append(report)
    return history, report


def gh(args):
    return subprocess.run(["gh", *args], check=True, text=True, capture_output=True, timeout=120).stdout


def restore(repo, output, *, bootstrap=False):
    """Restore the latest successful workflow artifact; never silently reset history."""
    pages = json.loads(
        gh(
            [
                "api",
                "--paginate",
                "--slurp",
                f"repos/{repo}/actions/workflows/{WORKFLOW}/runs?branch=main&status=success&per_page=100",
            ]
        )
    )
    runs = [r for page in pages for r in page["workflow_runs"]]
    if not runs:
        if not bootstrap:
            raise ValueError("No prior history: explicit first-run bootstrap required")
        Path(output).mkdir(parents=True, exist_ok=False)
        write_new(Path(output) / "bootstrap.json", {"bootstrap": True})
        return
    latest = max(runs, key=lambda r: (r["run_number"], r.get("run_attempt", 1)))
    artifacts = json.loads(gh(["api", f"repos/{repo}/actions/runs/{latest['id']}/artifacts?per_page=100"]))["artifacts"]
    expected = f"{PREFIX}{latest['id']}-{latest.get('run_attempt', 1)}"
    found = [a for a in artifacts if a["name"] == expected and not a["expired"]]
    if len(found) != 1:
        raise ValueError("Expected prior cumulative artifact missing/expired; operator recovery required")
    Path(output).mkdir(parents=True, exist_ok=False)
    gh(["run", "download", str(latest["id"]), "--repo", repo, "--name", expected, "--dir", str(output)])
    if not (Path(output) / "history.json").is_file():
        raise ValueError("Prior artifact missing history.json")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--restore-repo")
    args = parser.parse_args(argv)
    if args.restore_repo:
        restore(args.restore_repo, args.output, bootstrap=args.bootstrap)
        return 0
    if not args.run_id or (args.previous is None and not args.bootstrap):
        parser.error("collection requires --run-id and --previous or explicit first-run --bootstrap")
    if args.output.exists():
        parser.error("output directory already exists; evidence cannot be overwritten")
    baseline = json.loads(BASELINE.read_text())
    previous = json.loads(args.previous.read_text()) if args.previous else None
    clients = load_clients()
    history, report = asyncio.run(collect(clients, baseline, previous, args.run_id))
    args.output.mkdir(parents=True, exist_ok=False)
    write_new(args.output / "history.json", history)
    write_new(args.output / "run.json", report)
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
