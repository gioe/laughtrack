"""Background: TASK-4158 collector ships separately from deferred enforcement.

What this script does: enable only event-description collection on the three
reviewed pilot sources. All remain unreviewed/off/version3. No policy, show,
comedian, candidate, review, or directory records are changed. Existing forensic
metadata remains intact; task_4158_event_details records this operation's audit.

Usage: python scripts/archive/enable_pilot_event_details_2026_10_11.py --repo-root /absolute/repo --dry-run
       python scripts/archive/enable_pilot_event_details_2026_10_11.py --repo-root /absolute/repo --apply
"""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

EXPECTED = {
    192: (61, 53, "79a4305232b6333170da1ae93480d6681d9c495a22ed96173b8f1d33fbbc75de"),
    527: (475, 450, "dd64d7f0a11320d9924cf44802367efb612d4aa7b62a70a5de871febc94fb410"),
    595: (476, 451, "94f0ce1fe4efe6cf6bd507442aa1137c0f3db713a5ef37a178c2a0bc5f499454"),
}
ANNOTATION_KEY = "task_4158_event_details"
ANNOTATION = {
    "task": 4158,
    "activated_on": "2026-10-11",
    "reason": "Enable description collection only; enforcement deferred",
    "policy": "unreviewed",
    "gate_mode": "off",
    "policy_version": 3,
}


def fingerprint(row):
    config = {
        key: value
        for key, value in row.items()
        if not key.startswith("comedy_") and key not in {"created_at", "updated_at"}
    }
    config["metadata"] = {
        key: value
        for key, value in (row.get("metadata") or {}).items()
        if key not in {"task_4158_rollout", "seatengine_event_details", ANNOTATION_KEY}
    }
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def rows(cursor):
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def run(transaction, apply=False):
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM scraping_sources WHERE id=ANY(%s) ORDER BY id FOR UPDATE", (sorted(EXPECTED),))
            before = rows(cur)
            problems = []
            if {row["id"] for row in before} != set(EXPECTED):
                problems.append("Missing or unexpected source IDs")
            for row in before:
                sid = row["id"]
                club_id, venue_id, expected_hash = EXPECTED[sid]
                if (
                    row.get("club_id"),
                    row.get("seatengine_id"),
                    row.get("scraper_key"),
                    row.get("platform"),
                    row.get("enabled"),
                ) != (club_id, venue_id, "seatengine", "seatengine", True):
                    problems.append(f"Source {sid}: identity/enabled mismatch")
                if (row.get("comedy_policy"), row.get("comedy_gate_mode"), row.get("comedy_policy_version")) != (
                    "unreviewed",
                    "off",
                    3,
                ):
                    problems.append(f"Source {sid}: expected unreviewed/off/version3")
                metadata = row.get("metadata") or {}
                if not isinstance(metadata, dict):
                    problems.append(f"Source {sid}: metadata is not an object")
                    continue
                if row.get("source_target_id") is not None or "seatengine_venue_routes" in metadata:
                    problems.append(f"Source {sid}: not a direct venue source")
                if fingerprint(row) != expected_hash:
                    problems.append(f"Source {sid}: frozen fetch configuration changed")
                if "seatengine_event_details" in metadata and metadata["seatengine_event_details"] is not True:
                    problems.append(f"Source {sid}: conflicting explicit collector setting")
                if ANNOTATION_KEY in metadata and metadata[ANNOTATION_KEY] != ANNOTATION:
                    problems.append(f"Source {sid}: conflicting activation audit")
            if problems:
                raise ValueError("Refusing entire activation: " + "; ".join(problems))
            print("BEFORE\n" + json.dumps(before, default=str, sort_keys=True, indent=2))
            changed = 0
            if apply:
                for row in before:
                    metadata = row.get("metadata") or {}
                    if metadata.get("seatengine_event_details") is True and metadata.get(ANNOTATION_KEY) == ANNOTATION:
                        continue
                    cur.execute(
                        """UPDATE scraping_sources
                        SET metadata=%s::jsonb
                        WHERE id=%s AND enabled=true AND comedy_policy='unreviewed' AND comedy_gate_mode='off'
                          AND comedy_policy_version=3 AND metadata IS NOT DISTINCT FROM %s::jsonb
                        RETURNING id""",
                        (
                            json.dumps({**metadata, "seatengine_event_details": True, ANNOTATION_KEY: ANNOTATION}),
                            row["id"],
                            json.dumps(row.get("metadata")),
                        ),
                    )
                    result = cur.fetchall()
                    if cur.rowcount != 1 or result != [(row["id"],)]:
                        raise ValueError(f"Source {row['id']}: CAS/update rowcount mismatch")
                    changed += 1
            cur.execute("SELECT * FROM scraping_sources WHERE id=ANY(%s) ORDER BY id", (sorted(EXPECTED),))
            after = rows(cur)
            expected = deepcopy(before)
            if apply:
                for row in expected:
                    row["metadata"] = {
                        **(row.get("metadata") or {}),
                        "seatengine_event_details": True,
                        ANNOTATION_KEY: ANNOTATION,
                    }
            if after != expected:
                raise ValueError("Post-state mismatch; rolling back all changes")
            print("AFTER\n" + json.dumps(after, default=str, sort_keys=True, indent=2))
            print(
                json.dumps(
                    {
                        "apply": apply,
                        "changed_rows": changed,
                        "source_ids": sorted(EXPECTED),
                        "policy_unchanged": True,
                        "gate_mode": "off",
                        "policy_version": 3,
                    }
                )
            )
            return {"apply": apply, "changed_rows": changed, "before": before, "after": after}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Write a before/after audit artifact after successful transaction")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve() / "apps/scraper"
    if not (root / "src/laughtrack/adapters/db.py").is_file():
        raise ValueError("Invalid repository root")
    sys.path[:0] = [str(root / "src"), str(root)]
    from dotenv import load_dotenv

    load_dotenv(root / ".env")
    from laughtrack.adapters.db import get_transaction

    result = run(get_transaction, apply=args.apply)
    if args.output:
        args.output.write_text(json.dumps(result, default=str, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
