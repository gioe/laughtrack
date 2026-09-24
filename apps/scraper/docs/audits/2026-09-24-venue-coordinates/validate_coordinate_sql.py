"""Validate coordinate migration/scheduler against local PostgreSQL temp tables.

Run from apps/scraper with PYTHONPATH=src and --dsn for a local disposable DB.
Only pg_temp tables are changed; all resolver calls are injected, with no HTTP.
"""

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import psycopg2
from laughtrack.utilities.domain.club import coordinates as mod


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", default="host=127.0.0.1 port=55444 dbname=postgres")
    parser.add_argument("--migration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    conn = psycopg2.connect(args.dsn)
    assert conn.get_dsn_parameters()["host"] in ("127.0.0.1", "localhost", "/private/tmp"), "Local validation only"
    evidence = {
        "database": "local PostgreSQL, temporary tables only",
        "provider_calls": 0,
        "migration_sha256": hashlib.sha256(args.migration.read_bytes()).hexdigest(),
    }
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TEMP TABLE clubs (id integer PRIMARY KEY, name text, address text, city text, state text, zip_code text, country text, latitude double precision, longitude double precision, visible boolean, status text, club_type text)"
            )
            cur.execute("CREATE TEMP TABLE shows (club_id integer, date timestamptz)")
            cur.execute("SET search_path TO pg_temp")
        conn.commit()
        migration = args.migration.read_text()
        with conn.cursor() as cur:
            cur.execute(migration)
            cur.execute(
                "SELECT count(*) FROM pg_attribute WHERE attrelid='clubs'::regclass AND attname LIKE 'geocode_%'"
            )
            assert cur.fetchone()[0] == 3
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM pg_attribute WHERE attrelid='clubs'::regclass AND attname LIKE 'geocode_%'"
            )
            assert cur.fetchone()[0] == 0
            cur.execute(migration)
            cur.execute(
                "INSERT INTO clubs (id,name,address,city,state,zip_code,country,latitude,longitude,visible,status,club_type) VALUES (1,'Unresolved','1 Main St','Boston','MA','02116','US',NULL,NULL,TRUE,'active','venue'),(2,'Resolvable','2 Main St','Boston','MA','02116','US',NULL,NULL,TRUE,'active','venue'),(3,'Verified','3 Main St','Boston','MA','02116','US',42,-71,TRUE,'active','venue'),(4,'Hidden','4 Main St','Boston','MA','02116','US',NULL,NULL,FALSE,'active','venue')"
            )
            cur.execute("INSERT INTO shows VALUES (1,NOW()+INTERVAL '1 day'),(2,NOW()+INTERVAL '1 day')")
        conn.commit()
        evidence["migration_transaction_rollback"] = "passed"
        evidence["migration_reapply_after_rollback"] = "passed"
        # Prisma migrations run once; deliberately document raw DDL replay behavior.
        with conn.cursor() as cur:
            cur.execute("SAVEPOINT ddl_replay")
            try:
                cur.execute(migration)
            except psycopg2.errors.DuplicateColumn:
                evidence["raw_ddl_idempotent"] = False
                cur.execute("ROLLBACK TO SAVEPOINT ddl_replay")
            else:
                evidence["raw_ddl_idempotent"] = True
        conn.commit()

        @contextmanager
        def connection(**kwargs):
            yield conn

        calls = []

        def resolver(club):
            calls.append(club.id)
            return (42.1, -71.1) if club.id == 2 else None

        with patch.object(mod, "get_connection", connection):
            preview = mod.preview_missing_clubs(limit=30)
            assert [row.id for row in preview] == [1, 2]
            with conn.cursor() as cur:
                cur.execute("SELECT SUM(geocode_attempt_count) FROM clubs")
                assert cur.fetchone()[0] == 0
            first = mod.geocode_missing_clubs(limit=1, resolver=resolver, sleep=lambda _: None)
            second = mod.geocode_missing_clubs(limit=1, resolver=resolver, sleep=lambda _: None)
            third = mod.geocode_missing_clubs(limit=1, resolver=resolver, sleep=lambda _: None)
            assert calls == [1, 2], calls
            assert (first.attempted, first.unresolved) == (1, 1)
            assert (second.attempted, second.resolved) == (1, 1)
            assert third.attempted == 0
            with conn.cursor() as cur:
                cur.execute("SELECT id,latitude,longitude,geocode_attempt_count,geocode_outcome FROM clubs ORDER BY id")
                rows = cur.fetchall()
            assert rows == [
                (1, None, None, 1, "unresolved"),
                (2, 42.1, -71.1, 1, "resolved"),
                (3, 42.0, -71.0, 0, None),
                (4, None, None, 0, None),
            ], rows
            evidence.update(
                {
                    "preview_read_only": "passed",
                    "unresolved_rotates_to_next_candidate": "passed",
                    "resolved_rerun_idempotence": "passed",
                    "known_coordinates_preserved": "passed",
                    "hidden_excluded": "passed",
                    "resolver_ids": calls,
                    "runs": [asdict(first), asdict(second), asdict(third)],
                    "final_rows": rows,
                }
            )
            # A second real connection owning the advisory lock suppresses work.
            locker = psycopg2.connect(args.dsn)
            try:
                with locker.cursor() as cur:
                    cur.execute("SELECT pg_advisory_xact_lock(%s)", (mod._GEOCODE_LOCK_ID,))
                blocked = mod.geocode_missing_clubs(
                    limit=1, resolver=lambda _: (_ for _ in ()).throw(AssertionError("locked")), sleep=lambda _: None
                )
                assert blocked.attempted == 0
                evidence["cross_connection_advisory_lock"] = "passed"
            finally:
                locker.rollback()
                locker.close()
        args.output.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
