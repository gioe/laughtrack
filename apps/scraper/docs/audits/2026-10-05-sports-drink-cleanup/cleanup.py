"""Bounded TASK-4107 cleanup: rollback by default, private before-images required."""

import argparse
import hashlib
import json
import runpy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from laughtrack.foundation.db_util import connect_with_retry
from replay import ROOT, utc, verify

SHARED = runpy.run_path(str(ROOT.parents[2] / "scripts/core/repair_annoyance_identity.py"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.export.resolve().is_relative_to(ROOT.parents[4]):
        parser.error("Recovery export must be outside the repository")
    selected = verify()
    ids = sorted(r["id"] for r in selected)
    manifest = json.loads((ROOT / "manifest.json").read_text())
    cutoff = utc(manifest["cutoff"])
    if not cutoff <= datetime.now(timezone.utc) <= cutoff + timedelta(hours=24):
        raise ValueError("Evidence expired; revalidate")
    evidence = json.loads((ROOT / "before.json").read_text())
    expected = {r["id"]: r for r in evidence["shows"]}
    plan = {"club_id": 653, "source_id": 249, "expected_shows": {str(i): {} for i in expected}}
    query = runpy.run_path(str(ROOT.parents[2] / "bin/query"))
    conn = connect_with_retry(query["_resolve_database_url"]())
    try:
        with conn.cursor() as cur:
            schema = SHARED["lock_schema"](cur)
            cur.execute("SET LOCAL statement_timeout='30s'")
            cur.execute("SELECT to_jsonb(c) FROM clubs c WHERE id=653 FOR UPDATE")
            club = cur.fetchone()[0]
            before = SHARED["snapshot"](cur, plan)
            if before["scraping_sources"] != [evidence["source"]]:
                raise ValueError("Source configuration drift")
            live = {r["id"]: r for r in before["shows"]}
            if set(live) != set(expected):
                raise ValueError("Venue cohort changed")
            for ident in ids + manifest["hold_ids"] + manifest["replacement_ids"]:
                row = live[ident]
                for key, value in expected[ident].items():
                    if not SHARED["same_value"](key, row.get(key), value):
                        raise ValueError(f"Identity/freshness drift: {ident} {key}")
            for ident in ids:
                if utc(live[ident]["date"]) <= datetime.now(timezone.utc):
                    raise ValueError("Candidate has elapsed; hold and re-review")
                if utc(live[ident]["last_scraped_date"]) >= cutoff:
                    raise ValueError("Candidate was refreshed")
            impacts = {t: sum(r["show_id"] in ids for r in before[t]) for t in SHARED["CHILDREN"]}
            if impacts != manifest["dependent_counts"]:
                raise ValueError("Dependent-row impact changed")
            if any(impacts[t] for t in ("saved_shows", "sent_notifications", "discovery_show_feature_snapshots")):
                raise ValueError("Protected user references require separate review")
            SHARED["save_backup"](
                args.export,
                {
                    "task_id": 4107,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "manifest_sha256": hashlib.sha256((ROOT / "manifest.json").read_bytes()).hexdigest(),
                    "schema": schema,
                    "club_before": club,
                    "before": before,
                    "retire_ids": ids,
                },
            )
            cur.execute("DELETE FROM shows WHERE club_id=653 AND id=ANY(%s) RETURNING id", (ids,))
            if sorted(r[0] for r in cur.fetchall()) != ids:
                raise ValueError("Deleted cohort mismatch")
            after = SHARED["snapshot"](cur, plan)
            for table, rows in before.items():
                if table == "scraping_sources":
                    wanted = rows
                else:
                    key = "id" if table == "shows" else "show_id"
                    wanted = [r for r in rows if r[key] not in ids]
                if after[table] != wanted:
                    raise ValueError(f"Retained data changed: {table}")
            clicks = sorted(
                (r for r in before["ticket_purchase_click_events"] if r["show_id"] in ids), key=lambda r: r["id"]
            )
            cur.execute(
                "SELECT to_jsonb(c) FROM ticket_purchase_click_events c WHERE id=ANY(%s) ORDER BY id",
                ([r["id"] for r in clicks],),
            )
            if [r[0] for r in cur.fetchall()] != [dict(r, show_id=None) for r in clicks]:
                raise ValueError("Click attribution changed")
            cur.execute("UPDATE clubs SET total_shows=(SELECT count(*) FROM shows WHERE club_id=653) WHERE id=653")
            if cur.rowcount != 1:
                raise ValueError("Venue aggregate refresh failed")
            result = {
                "task_id": 4107,
                "mode": "applied" if args.apply else "rolled_back",
                "retired_ids": ids,
                "held_ids": manifest["hold_ids"],
                "preserved_replacement_ids": manifest["replacement_ids"],
                "before_count": len(live),
                "after_count": len(after["shows"]),
                "dependent_counts": impacts,
                "retained_rows_unchanged": True,
                "click_attribution_preserved": True,
                "cap_unchanged": 10,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        if args.apply:
            conn.commit()
        else:
            conn.rollback()
        if args.result:
            args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
