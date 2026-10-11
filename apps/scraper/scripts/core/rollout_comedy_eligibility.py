"""Background: TASK-4158 rolls out screening independently of directory eligibility.

What this script does: validates a bounded source manifest, changes audited policy,
and records reversible source-local history. It never publishes or deletes events.

Usage: python scripts/core/rollout_comedy_eligibility.py plan --manifest cohort.json
       python scripts/core/rollout_comedy_eligibility.py apply --manifest cohort.json --dry-run
       python scripts/core/rollout_comedy_eligibility.py rollback --manifest cohort.json
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy, save_source_comedy_policy

ANNOTATION = "task_4158_rollout"
REQUIRED_TABLES = (
    "comedy_event_candidates",
    "comedy_event_decisions",
    "comedy_event_observations",
    "comedy_event_publications",
    "comedy_event_reviews",
    "comedy_review_previews",
    "comedy_review_operations",
    "comedy_source_samples",
    "comedy_source_reports",
    "comedy_source_transitions",
)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _rows(cursor):
    return [
        dict(row) if hasattr(row, "keys") else dict(zip((c[0] for c in cursor.description), row))
        for row in cursor.fetchall()
    ]


def source_fingerprint(row):
    """Bind all fetch configuration, ownership and enabled state, excluding audit churn."""
    config = {k: v for k, v in row.items() if not k.startswith("comedy_") and k not in {"updated_at", "created_at"}}
    config["metadata"] = {k: v for k, v in (row.get("metadata") or {}).items() if k != ANNOTATION}
    return _digest(config)


def validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")
    for key in ("rollout_id", "actor", "reason"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise ValueError(f"Manifest requires {key}")
    if not isinstance(manifest.get("evidence"), dict) or not manifest["evidence"]:
        raise ValueError("Manifest requires evidence")
    targets = manifest.get("targets")
    if not isinstance(targets, list) or not 1 <= len(targets) <= 100:
        raise ValueError("Manifest must contain 1-100 targets")
    ids = []
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("Manifest targets must be objects")
        if type(target.get("source_id")) is not int or target["source_id"] <= 0:
            raise ValueError("Invalid source_id")
        ids.append(target["source_id"])
        SourceComedyPolicy(target.get("policy"), target.get("gate_mode"), target.get("expected_version"))
        if target["policy"] != "mixed" or target["gate_mode"] not in {"shadow", "enforce"}:
            raise ValueError("Rollout targets must be mixed/shadow or mixed/enforce")
        fingerprint = target.get("config_fingerprint", "")
        if (
            not isinstance(fingerprint, str)
            or len(fingerprint) != 64
            or any(c not in "0123456789abcdef" for c in fingerprint)
        ):
            raise ValueError("Invalid config_fingerprint")
        if target["gate_mode"] == "enforce" and (
            manifest["evidence"].get("go_no_go") != "go" or not manifest["evidence"].get("artifact")
        ):
            raise ValueError("Enforcement requires a go decision and reviewed artifact")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate source IDs")


def run(manifest, command, transaction, *, dry_run=False):
    validate_manifest(manifest)
    if command not in {"plan", "apply", "rollback"}:
        raise ValueError("Unknown operation")
    fingerprint = _digest(manifest)
    targets = sorted(manifest["targets"], key=lambda t: t["source_id"])
    with transaction() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM scraping_sources WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
                ([t["source_id"] for t in targets],),
            )
            rows = {r["id"]: r for r in _rows(cursor)}
            problems, actions = [], []
            for target in targets:
                sid = target["source_id"]
                row = rows.get(sid)
                if row is None:
                    problems.append(f"Source {sid} missing")
                    continue
                if source_fingerprint(row) != target["config_fingerprint"]:
                    problems.append(f"Source {sid} configuration changed")
                if not row.get("enabled"):
                    problems.append(f"Source {sid} disabled")
                current = SourceComedyPolicy.from_row(row)
                history = (row.get("metadata") or {}).get(ANNOTATION, {})
                if not isinstance(history, dict):
                    problems.append(f"Source {sid} malformed rollout history")
                    continue
                previous = history.get(manifest["rollout_id"])
                if previous and previous.get("manifest_digest") != fingerprint:
                    problems.append(f"Source {sid} rollout ID already used by another manifest")
                    continue
                noop = False
                if command == "rollback":
                    if not previous:
                        problems.append(f"Source {sid} has no matching rollout")
                        continue
                    restored = previous.get("rollback")
                    expected = restored or previous["after"]
                    noop = bool(restored)
                    desired = previous["before"]
                    if current.version != expected["version"] or (current.policy, current.gate_mode) != (
                        expected["policy"],
                        expected["gate_mode"],
                    ):
                        problems.append(f"Source {sid} changed since rollout; rollback refused")
                elif previous:
                    expected = previous.get("rollback") or previous["after"]
                    if previous.get("rollback"):
                        problems.append(f"Source {sid} rollout already rolled back; use a new rollout ID")
                    elif asdict(current) != expected:
                        # Timestamps may be serialized in JSON history.
                        if _digest(asdict(current)) != _digest(expected):
                            problems.append(f"Source {sid} changed since rollout")
                    desired, noop = target, True
                else:
                    if current.version != target["expected_version"]:
                        problems.append(f"Source {sid} policy version changed")
                    desired = target
                actions.append((row, current, desired, history, previous, noop))
            if command != "rollback":
                cursor.execute(
                    "SELECT name, to_regclass(name) IS NOT NULL AS present FROM unnest(%s::text[]) AS name",
                    (list(REQUIRED_TABLES),),
                )
                problems.extend(f"Missing required table {r['name']}" for r in _rows(cursor) if not r["present"])
            if problems:
                raise ValueError("Rollout refused: " + "; ".join(problems))
            before = [{"source_id": row["id"], **asdict(current)} for row, current, *_ in actions]
            print("BEFORE\n" + json.dumps(before, sort_keys=True, default=str))
            after = []
            for row, current, desired, history, previous, noop in actions:
                policy = current
                if not noop and command != "plan" and not dry_run:
                    policy = save_source_comedy_policy(
                        cursor,
                        row["id"],
                        SourceComedyPolicy(
                            desired["policy"],
                            desired["gate_mode"],
                            current.version,
                            reviewed_by=manifest["actor"],
                            evidence={
                                "task": 4158,
                                "operation": command,
                                "rollout_id": manifest["rollout_id"],
                                "reason": manifest["reason"],
                                "manifest_digest": fingerprint,
                                "evidence": manifest["evidence"],
                            },
                        ),
                    )
                    record = (
                        dict(previous)
                        if previous
                        else {
                            "manifest_digest": fingerprint,
                            "before": asdict(current),
                            "after": asdict(policy),
                        }
                    )
                    if command == "rollback":
                        record["rollback"] = asdict(policy)
                    history = {**history, manifest["rollout_id"]: record}
                    cursor.execute(
                        "UPDATE scraping_sources SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), %s, %s::jsonb) WHERE id = %s",
                        ([ANNOTATION], json.dumps(history, default=str), row["id"]),
                    )
                after.append(
                    {
                        "source_id": row["id"],
                        "policy": policy.policy,
                        "gate_mode": policy.gate_mode,
                        "version": policy.version,
                        "noop": noop,
                        "planned_policy": desired["policy"],
                        "planned_gate_mode": desired["gate_mode"],
                    }
                )
            print("AFTER\n" + json.dumps(after, sort_keys=True, default=str))
            return {"command": command, "dry_run": dry_run or command == "plan", "sources": after}


def main(argv=None, *, transaction=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "apply", "rollback"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if transaction is None:
        from dotenv import load_dotenv

        load_dotenv(_root / ".env")
        from laughtrack.adapters.db import get_transaction

        transaction = get_transaction
    run(json.loads(args.manifest.read_text()), args.command, transaction, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
