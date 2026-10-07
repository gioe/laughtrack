"""Read-only six-show relationship audit for TASK-4127.

Run from apps/scraper with PYTHONPATH=src:. .venv/bin/python3
docs/audits/2026-10-07-annoyance-history/verify_history.py --output /absolute/report.json
Full child rows stay in memory; only counts and ephemeral keyed hashes leave it.
No repair, scraper persistence, or production write path is invoked.
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
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from scripts.core.repair_annoyance_identity import CHILDREN, ticket_identity

PAIRS = ((7451272, 3769502), (1371908, 847662), (1024865, 927780))
IDS = [ident for pair in PAIRS for ident in pair]


def snapshot(conn, secret):
    # Same single-statement snapshot pattern as the TASK-4126 verifier.
    tables = ("shows", *CHILDREN)
    queries = [
        sql.SQL("SELECT %s, to_jsonb(t) FROM {} t WHERE {} = ANY(%s)").format(
            sql.Identifier(table), sql.Identifier("id" if table == "shows" else "show_id")
        )
        for table in tables
    ]
    with conn.cursor() as cur:
        cur.execute(sql.SQL(" UNION ALL ").join(queries), [v for t in tables for v in (t, IDS)])
        rows = {t: [] for t in tables}
        for table, row in cur.fetchall():
            rows[table].append(row)
    public = {}
    for table, items in rows.items():
        canonical = "\n".join(sorted(json.dumps(row, sort_keys=True) for row in items))
        public[table] = {
            "count": len(items),
            "by_show": {str(i): sum(r["id" if table == "shows" else "show_id"] == i for r in items) for i in IDS},
            "all_columns_hmac_sha256": hmac.new(secret, canonical.encode(), hashlib.sha256).hexdigest(),
        }
    if {r["id"] for r in rows["shows"]} != set(IDS) or any(r["club_id"] != 183 for r in rows["shows"]):
        raise AssertionError("Expected six Annoyance shows changed")
    pairs = []
    for pair in PAIRS:
        identities = []
        for ident in pair:
            urls = [r["purchase_url"] for r in rows["tickets"] if r["show_id"] == ident]
            native = {ticket_identity(url) for url in urls}
            if len(native) != 1:
                raise AssertionError(f"Show {ident} lacks one unambiguous ticket identity")
            identities.append(next(iter(native)))
        if identities[0] != identities[1]:
            raise AssertionError("Pair no longer shares a native identity")
        pairs.append({"show_ids": pair, "native_identity": identities[0]})
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "tables": public,
        "shows": sorted(rows["shows"], key=lambda r: r["id"]),
        "tickets": [{k: r[k] for k in ("id", "show_id", "purchase_url", "price")} for r in rows["tickets"]],
        "pairs": pairs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    values = dotenv_values(ROOT / ".env")
    conn = psycopg2.connect(
        host=values["DATABASE_HOST"],
        user=values["DATABASE_USER"],
        password=values["DATABASE_PASSWORD"],
        dbname=values["DATABASE_NAME"],
        port=values.get("DATABASE_PORT", "5432"),
        sslmode="require",
        options="-c default_transaction_read_only=on -c statement_timeout=15000",
    )
    try:
        conn.set_session(readonly=True, isolation_level="READ COMMITTED", autocommit=True)
        with conn.cursor() as cur:
            cur.execute("SHOW transaction_read_only")
            assert cur.fetchone() == ("on",)
            cur.execute("""SELECT c.conrelid::regclass::text, a.attname
                FROM pg_constraint c JOIN LATERAL unnest(c.conkey) k(attnum) ON true
                JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.attnum
                WHERE c.confrelid='shows'::regclass AND c.contype='f'""")
            foreign_keys = sorted((t.split(".")[-1].strip('"'), col) for t, col in cur.fetchall())
            if set(foreign_keys) != {(t, "show_id") for t in CHILDREN}:
                raise AssertionError("Show foreign keys changed; review audit coverage")
        secret = secrets.token_bytes(32)
        before = snapshot(conn, secret)
        after = snapshot(conn, secret)
        if before["tables"] != after["tables"]:
            raise AssertionError("Rows changed between read-only observations")
        report = {
            "task_id": 4127,
            "production_mutations": 0,
            "transaction_read_only": True,
            "foreign_keys": foreign_keys,
            "before": before,
            "after": after,
            "all_rows_unchanged_between_observations": True,
            "limitations": "Two independent statement snapshots detect net visible changes only; no claim about historical correctness or concurrent reverted writes. The ephemeral HMAC key is discarded; hashes are comparable only within this run.",
        }
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "shows": len(after["shows"]),
                    "relationships": {t: after["tables"][t]["count"] for t in CHILDREN},
                    "production_mutations": 0,
                }
            )
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
