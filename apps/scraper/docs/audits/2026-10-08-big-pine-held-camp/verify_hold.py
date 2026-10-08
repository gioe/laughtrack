"""Read-only full-row preservation check for TASK-4137's continued hold.

Run from apps/scraper with PYTHONPATH=src:. .venv/bin/python3
docs/audits/2026-10-08-big-pine-held-camp/verify_hold.py --output /absolute/report.json.
Private relationship rows remain in memory. Only counts and keyed hashes leave it.
"""

import argparse
import hashlib
import hmac
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from scripts.core.cleanup_remaining_big_pine_inventory import snapshot
from scripts.core.repair_annoyance_identity import CHILDREN


def observe(conn):
    with conn:
        with conn.cursor() as cur:
            cur.execute("SHOW transaction_read_only")
            assert cur.fetchone() == ("on",)
            cur.execute("SET LOCAL TIME ZONE 'UTC'")
            cur.execute("""SELECT c.conrelid::regclass::text, a.attname
                FROM pg_constraint c JOIN LATERAL unnest(c.conkey) k(attnum) ON true
                JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.attnum
                WHERE c.confrelid='shows'::regclass AND c.contype='f'""")
            actual = {(t.split(".")[-1].strip('"'), col) for t, col in cur.fetchall()}
            if actual != {(t, "show_id") for t in CHILDREN}:
                raise ValueError("Show foreign keys changed; review snapshot coverage")
            state = snapshot(cur, {"inventory_ids": [522192]})
    return state


def summarize(state, secret):
    return {
        table: {
            "count": len(rows),
            "all_columns_hmac_sha256": hmac.new(
                secret, json.dumps(rows, sort_keys=True).encode(), hashlib.sha256
            ).hexdigest(),
        }
        for table, rows in state.items()
    }


def main():
    parser = argparse.ArgumentParser(description="Verify Big Pine's continued hold without production writes.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    values = dotenv_values(ROOT / ".env")
    conn = psycopg2.connect(
        host=values["DATABASE_HOST"], user=values["DATABASE_USER"], password=values["DATABASE_PASSWORD"],
        dbname=values["DATABASE_NAME"], port=values.get("DATABASE_PORT", "5432"), sslmode="require",
        options="-c default_transaction_read_only=on -c statement_timeout=15000",
    )
    try:
        conn.set_session(readonly=True, isolation_level="REPEATABLE READ")
        started_at = datetime.now(timezone.utc).isoformat()
        before = observe(conn)
        after = observe(conn)
        if before != after:
            raise ValueError("Protected full-row state changed between observations")
        expected_ids = json.loads((ROOT / "docs/audits/2026-10-07-big-pine-remaining/live-verification.json").read_text())["retained_show_ids"]
        if {r["id"] for r in after["shows"]} != set(expected_ids):
            raise ValueError("Prior retained festival cohort changed")
        held = next(r for r in after["shows"] if r["id"] == 522192)
        if (held["club_id"] != 573 or datetime.fromisoformat(held["date"]) != datetime.fromisoformat("2026-05-10T16:00:00+00:00")
                or held["show_page_url"] != "https://www.bigpinecomedyfestival.org/shows/356284"):
            raise ValueError("Held occurrence no longer matches reviewed identity")
        if not after["clubs"][0]["visible"]:
            raise ValueError("Festival visibility changed")
        if {r["id"] for r in after["scraping_sources"]} != {360, 3126, 7146} or {r["id"] for r in after["source_targets"]} != {1, 2}:
            raise ValueError("Protected source/target cohort changed")
        secret = secrets.token_bytes(32)
        report = {
            "task_id": 4137, "decision": "continued_hold", "production_mutations": 0,
            "started_at": started_at, "verified_at": datetime.now(timezone.utc).isoformat(),
            "transaction_read_only": True, "isolation_level": "REPEATABLE READ per independent observation",
            "before": summarize(before, secret), "after": summarize(after, secret),
            "all_full_rows_unchanged": True, "retained_show_ids": sorted(expected_ids),
            "held_show": {k: held[k] for k in ("id", "club_id", "name", "date", "show_page_url", "source_performance_id")},
            "held_relationship_counts": {t: sum(r["show_id"] == 522192 for r in after[t]) for t in CHILDREN},
            "limitations": "Two independent coherent snapshots prove net equality at the observation points, not absence of intervening reverted writes; no assertion of historical date correctness. HMAC key discarded after this run."
        }
        with args.output.open("x") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(json.dumps({"output": str(args.output), "counts": {t: len(r) for t, r in after.items()}, "production_mutations": 0}))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
