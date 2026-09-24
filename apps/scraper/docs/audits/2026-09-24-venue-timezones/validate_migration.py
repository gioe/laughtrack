"""Validate the exact migration against a local PostgreSQL snapshot, never production.

Start a throwaway PostgreSQL instance, then run with the scraper virtualenv:
    python validate_migration.py --dsn 'host=127.0.0.1 port=55444 dbname=postgres'
Only temporary clubs and shows tables is written; all scenarios roll back to the baseline.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extensions import parse_dsn


def main():
    parser = argparse.ArgumentParser(description="Validate guarded venue timezone migration locally")
    parser.add_argument("--dsn", required=True)
    args = parser.parse_args()
    host = parse_dsn(args.dsn).get("host", "")
    if host not in ("127.0.0.1", "localhost", "::1") and not host.startswith("/"):
        parser.error("Use an explicit loopback host or local socket for a throwaway PostgreSQL instance")
    here = Path(__file__).resolve().parent
    scraper = here.parents[2]
    migration = scraper.parent / "web/prisma/migrations/20260924170000_restore_verified_venue_timezones/migration.sql"
    sql = migration.read_text()
    rows = json.loads((here / "before.json").read_text())
    sources = json.loads((here / "sources.json").read_text())
    expected = {s["snapshot"]["id"]: s["timezone"] for s in sources if s["status"] == "verified"}
    assert expected
    expected_count = len(expected)
    result = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "migration_sha256": hashlib.sha256(sql.encode()).hexdigest(),
        "snapshot_rows": len(rows),
        "expected_updates": len(expected),
        "scenarios": [],
    }
    connection = psycopg2.connect(args.dsn)
    connection.set_client_encoding("UTF8")
    try:
        with connection.cursor() as cur:
            cur.execute("""CREATE TEMP TABLE clubs (
                id INTEGER PRIMARY KEY, name TEXT, address TEXT, country TEXT,
                visible BOOLEAN, timezone TEXT, zip_code TEXT, city TEXT, state TEXT,
                website TEXT, latitude DOUBLE PRECISION, longitude DOUBLE PRECISION
            )""")
            # Prevent accidental access to real tables even if this script changes.
            cur.execute("SET LOCAL search_path = pg_temp")
            cur.executemany(
                "INSERT INTO clubs VALUES (%s,%s,%s,%s,TRUE,%s,%s,%s,%s,%s,%s,%s)",
                [
                    (
                        r["id"],
                        r["name"],
                        r["address"],
                        r["country"],
                        r["timezone"],
                        r["zip_code"],
                        r["city"],
                        r["state"],
                        r["website"],
                        r["latitude"],
                        r["longitude"],
                    )
                    for r in rows
                ],
            )

            def snapshot():
                cur.execute("SELECT * FROM clubs ORDER BY id")
                return cur.fetchall()

            cur.execute("CREATE TEMP TABLE shows (id INTEGER PRIMARY KEY, club_id INTEGER, date TIMESTAMPTZ)")
            cur.executemany("INSERT INTO shows VALUES (%s,%s,%s)", [(r["id"], r["id"], "2026-12-01T23:00:00Z") for r in rows])
            cur.execute("SELECT * FROM shows ORDER BY id")
            original_shows = cur.fetchall()
            baseline = snapshot()
            cur.execute("SAVEPOINT baseline")
            cur.execute(sql)
            assert cur.rowcount == expected_count
            applied = snapshot()
            cur.execute("SELECT * FROM shows ORDER BY id")
            assert cur.fetchall() == original_shows
            for old, new in zip(baseline, applied):
                assert old[:5] == new[:5] and old[6:] == new[6:]
                assert new[5] == expected.get(old[0], old[5])
            cur.execute(sql)
            assert cur.rowcount == 0
            assert snapshot() == applied
            cur.execute("ROLLBACK TO SAVEPOINT baseline")
            assert snapshot() == baseline
            result["scenarios"].append(
                {
                    "name": "baseline_apply_rerun_rollback",
                    "updates": expected_count,
                    "rerun_updates": 0,
                    "exact_baseline_restored": True,
                    "show_instants_unchanged": True,
                }
            )

            # Every guard is tested against all targeted rows, not one sample.
            guards = {
                "existing_timezone": "timezone = 'Europe/London'",
                "empty_existing_timezone": "timezone = ''",
                "space_existing_timezone": "timezone = '   '",
                "changed_name": "name = name || ' moved'",
                "changed_address": "address = address || ' changed'",
                "null_address": "address = NULL",
                "changed_zip": "zip_code = '00001'",
                "null_zip": "zip_code = NULL",
                "hidden": "visible = FALSE",
                "null_visibility": "visible = NULL",
                "changed_id": "id = id + 1000000",
            }
            for name, assignment in guards.items():
                cur.execute("UPDATE clubs SET " + assignment + " WHERE id = ANY(%s)", (list(expected),))
                guarded = snapshot()
                cur.execute(sql)
                assert cur.rowcount == 0, name
                assert snapshot() == guarded, name
                cur.execute("ROLLBACK TO SAVEPOINT baseline")
                assert snapshot() == baseline
                result["scenarios"].append(
                    {"name": name, "protected_rows": expected_count, "updates": 0, "exact_baseline_restored": True}
                )

        connection.rollback()
    finally:
        connection.close()
    result["passed"] = True
    (here / "migration-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
