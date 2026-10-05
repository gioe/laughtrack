"""Backfill reviewed iO Crowdwork identities and activate atomically; default rollback."""

import argparse
import hashlib
import json
import runpy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from psycopg2.extras import execute_values

from laughtrack.core.entities.event.philly_improv import crowdwork_performance_identity
from laughtrack.foundation.db_util import connect_with_retry

ROOT = Path(__file__).resolve().parent
SCRAPER = ROOT.parents[2]
# Reuse the existing schema/reference snapshot and durable private export helpers.
shared = runpy.run_path(str(SCRAPER / "scripts/core/repair_annoyance_identity.py"))
MARKER = "task_4106_identity_repair"


def normalized(rows, ignore):
    return sorted(
        ({k: v for k, v in r.items() if k not in ignore} for r in rows), key=lambda row: json.dumps(row, sort_keys=True)
    )


def repair(cur, plan):
    schema = shared["lock_schema"](cur)
    cur.execute("SET LOCAL statement_timeout='30s'")
    before = shared["snapshot"](cur, plan)
    sources = before["scraping_sources"]
    if len(sources) != 1 or sources[0]["id"] != 45:
        raise ValueError("Source cohort drift")
    source = sources[0]
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    if (source.get("metadata") or {}).get(MARKER):
        raise ValueError("Repair already applied; do not overwrite recovery data")
    if datetime.now(timezone.utc) > datetime.fromisoformat(plan["captured_at"]) + timedelta(hours=24):
        raise ValueError("Reviewed plan expired")
    for key, value in plan["expected_source"].items():
        if source.get(key) != value:
            raise ValueError(f"Source {key} drift")
    rows = {str(r["id"]): r for r in before["shows"]}
    owned = {ident for ident, r in rows.items() if r["last_scraped_by"] == "crowdwork"}
    if owned != set(plan["expected_shows"]):
        raise ValueError("Crowdwork row cohort drift")
    updates = []
    for ident, expected in plan["expected_shows"].items():
        row = rows[ident]
        for key, value in expected.items():
            if not shared["same_value"](key, row.get(key), value):
                raise ValueError(f"Show {ident} {key} drift")
        if row["source_performance_id"] is not None:
            raise ValueError("Already identified row")
        urls = {t["purchase_url"] for t in before["tickets"] if str(t["show_id"]) == ident}
        if urls != {row["show_page_url"]}:
            raise ValueError(f"Ticket identity drift: {ident}")
        identity = crowdwork_performance_identity(row["show_page_url"], datetime.fromisoformat(row["date"]))
        if not identity:
            raise ValueError(f"Invalid Crowdwork identity: {ident}")
        updates.append((int(ident), identity))
    if len({identity for _, identity in updates}) != len(updates):
        raise ValueError("Ambiguous existing Crowdwork identities")
    execute_values(
        cur,
        """UPDATE shows s SET source_performance_id=v.identity
        FROM (VALUES %s) AS v(id,identity) WHERE s.id=v.id""",
        updates,
    )
    metadata = dict(source["metadata"] or {}, source_performance_identity=True, **{MARKER: digest})
    cur.execute("UPDATE scraping_sources SET metadata=%s::jsonb WHERE id=45", (json.dumps(metadata),))
    after = shared["snapshot"](cur, plan)
    if normalized(before["shows"], {"source_performance_id"}) != normalized(after["shows"], {"source_performance_id"}):
        raise ValueError("Existing show business fields changed")
    expected_ids = dict(updates)
    for row in after["shows"]:
        if row["source_performance_id"] != expected_ids.get(row["id"], rows[str(row["id"])]["source_performance_id"]):
            raise ValueError("Identity assignment mismatch")
    for table in shared["CHILDREN"]:
        if before[table] != after[table]:
            raise ValueError(f"Relationship changes: {table}")
    if normalized(before["scraping_sources"], {"metadata", "updated_at"}) != normalized(
        after["scraping_sources"], {"metadata", "updated_at"}
    ):
        raise ValueError("Source business fields changed")
    return {"task_id": 4106, "plan_hash": digest, "schema": schema, "before": before, "after": after}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--restore", type=Path)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires a new private backup path")
    plan = json.loads((ROOT / "plan.json").read_text())
    query = runpy.run_path(str(SCRAPER / "bin/query"))
    conn = connect_with_retry(query["_resolve_database_url"]())
    try:
        with conn.cursor() as cur:
            if args.restore:
                backup = json.loads(args.restore.read_text())
                digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
                if backup.get("task_id") != 4106 or backup.get("plan_hash") != digest:
                    raise ValueError("Backup does not match reviewed plan")
                if shared["lock_schema"](cur) != backup["schema"]:
                    raise ValueError("Schema changed after backup")
                if shared["snapshot"](cur, plan) != backup["after"]:
                    raise ValueError("Rows changed after repair; restore requires a new reviewed plan")
                originals = {r["id"]: r for r in backup["before"]["shows"]}
                execute_values(
                    cur,
                    """UPDATE shows s SET source_performance_id=v.identity
                    FROM (VALUES %s) AS v(id,identity) WHERE s.id=v.id""",
                    [(int(i), originals[int(i)]["source_performance_id"]) for i in plan["expected_shows"]],
                )
                metadata = backup["before"]["scraping_sources"][0]["metadata"]
                cur.execute("UPDATE scraping_sources SET metadata=%s::jsonb WHERE id=45", (json.dumps(metadata),))
                if not shared["same_business_state"](shared["snapshot"](cur, plan), backup["before"], 45):
                    raise ValueError("Restore did not reproduce original business state")
                conn.commit()
                print("Restored original identities and source metadata")
                return
            backup = repair(cur, plan)
        if args.apply:
            shared["save_backup"](args.backup, backup)
            conn.commit()
        else:
            conn.rollback()
        print(
            json.dumps(
                {
                    "mode": "apply" if args.apply else "rolled_back",
                    "identities_updated": len(plan["expected_shows"]),
                    "show_count": len(backup["after"]["shows"]),
                    "relationships_unchanged": {t: len(backup["after"][t]) for t in shared["CHILDREN"]},
                }
            )
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
