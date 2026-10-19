#!/usr/bin/env python3
"""Rehearse legacy quarantine and policy performance on supplied read-only snapshots.
Snapshots contain production data: retain locally, never commit or upload them.
Requires psycopg2, initdb and pg_ctl. Uses only a disposable private Unix socket.
"""

import json, os, subprocess, tempfile, time
from pathlib import Path
import psycopg2
from psycopg2.extras import Json, execute_values

W = Path(__file__).resolve().parents[1]
M = W / "prisma/migrations"
import argparse

parser = argparse.ArgumentParser(
    description="Disposable native PostgreSQL rollout rehearsal; never connects to a configured database."
)
parser.add_argument("--policy-snapshot", required=True)
parser.add_argument("--host-snapshot", required=True)
args = parser.parse_args()
policy = json.load(open(args.policy_snapshot))[0]["snapshot"]
hosts = json.load(open(args.host_snapshot))[0]["snapshot"]
with tempfile.TemporaryDirectory(prefix="task4187-prod-") as tmp:
    data = tmp + "/data"
    subprocess.run(
        ["initdb", "-D", data, "-A", "trust", "--no-locale", "--encoding=UTF8"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "pg_ctl",
            "-D",
            data,
            "-l",
            tmp + "/pg.log",
            "-o",
            f"-k {tmp} -h '' -p 55488",
            "-w",
            "start",
        ],
        check=True,
    )
    try:
        c = psycopg2.connect(host=tmp, port=55488, dbname="postgres")
        c.autocommit = True
        with c.cursor() as q:
            q.execute((W / "lib/admin/curation/fixtures/endToEnd.sql").read_text())
            migrations = json.loads(
                (W / "lib/admin/curation/fixtures/migrations.json").read_text()
            )
            for name in migrations:
                if name >= "20261015100000":
                    break
                q.execute((M / name / "migration.sql").read_text())

            def load(table, rows):
                if not rows:
                    return
                q.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s",
                    (table,),
                )
                known = {v[0] for v in q.fetchall()}
                columns = [k for k in rows[0] if k in known]
                q.execute(f"ALTER TABLE {table} DISABLE TRIGGER USER")
                execute_values(
                    q,
                    f"INSERT INTO {table} (" + ",".join(columns) + ") VALUES %s",
                    [
                        [
                            (
                                Json(row.get(k))
                                if isinstance(row.get(k), (dict, list))
                                else row.get(k)
                            )
                            for k in columns
                        ]
                        for row in rows
                    ],
                )
                q.execute(f"ALTER TABLE {table} ENABLE TRIGGER USER")

            load("comedians", policy["comedians"])
            load("podcasts", hosts["podcasts"])
            load("curation_entities", policy["entities"])
            load("curation_identity_keys", policy["keys"])
            load("curation_relationships", policy["relationships"])
            load("comedian_deny_list", [{"name": x} for x in policy["denied"]])
            load("comedian_identity_candidates", policy["candidates"])
            load("comedian_podcasts", hosts["associations"])
            load("podcast_candidate_reviews", hosts["candidates"])
            q.execute("ANALYZE")
            q.execute("SET statement_timeout='30s'")
            sample = policy["comedians"][:20]
            expected = []
            start = time.perf_counter()
            for p in sample:
                q.execute(
                    "SELECT * FROM curation_comedian_policy(%s,%s,%s)",
                    (p["uuid"], p["name"], p["id"]),
                )
                expected.append(q.fetchall())
            print(
                "old_policy_20_seconds",
                round(time.perf_counter() - start, 3),
                flush=True,
            )
            q.execute(
                (
                    M
                    / "20261015100000_curation_comedian_lookup_performance/migration.sql"
                ).read_text()
            )
            q.execute("ANALYZE")
            start = time.perf_counter()
            for p, want in zip(sample, expected):
                q.execute(
                    "SELECT * FROM curation_comedian_policy(%s,%s,%s)",
                    (p["uuid"], p["name"], p["id"]),
                )
                assert q.fetchall() == want
            print(
                "new_policy_20_seconds",
                round(time.perf_counter() - start, 3),
                flush=True,
            )
            q.execute(
                "SELECT count(*) FROM comedians WHERE parent_comedian_id IS NOT NULL"
            )
            parent_before = q.fetchone()[0]
            q.execute(
                "SELECT count(*) FROM curation_decisions WHERE action IN ('approve','confirm')"
            )
            approvals = q.fetchone()[0]
            for name in migrations:
                if name <= "20261015100000_curation_comedian_lookup_performance":
                    continue
                start = time.perf_counter()
                q.execute((M / name / "migration.sql").read_text())
                print(
                    "migration",
                    name,
                    "seconds",
                    round(time.perf_counter() - start, 3),
                    flush=True,
                )
            q.execute(
                "SELECT count(*) FROM curation_decisions WHERE action IN ('approve','confirm')"
            )
            assert q.fetchone()[0] == approvals
            q.execute(
                "SELECT count(*) FROM comedians WHERE parent_comedian_id IS NOT NULL"
            )
            assert q.fetchone()[0] == 0
            q.execute(
                "SELECT count(*) FROM curation_observations WHERE source='legacy-rollout:parent'"
            )
            assert q.fetchone()[0] == parent_before
            q.execute(
                "SELECT count(*) FROM curation_observations WHERE source IN ('legacy-rollout:comedian_podcasts','legacy-rollout:podcast_candidate_reviews')"
            )
            print("retained_host_observations", q.fetchone()[0], flush=True)
            for table, status in [
                ("comedian_podcasts", "review_status"),
                ("podcast_candidate_reviews", "candidate_status"),
            ]:
                q.execute(f"SELECT {status},count(*) FROM {table} GROUP BY 1")
                print(table, q.fetchall(), flush=True)
                q.execute(
                    f"SELECT count(*) FROM {table} x WHERE x.{status}='rejected' AND NOT EXISTS (SELECT 1 FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id WHERE s.comedian_id=x.comedian_id AND t.podcast_id=x.podcast_id AND r.kind=x.association_type||'_of' AND r.disposition IN ('rejected','severed'))"
                )
                assert q.fetchone()[0] == 0
            ids = [p["id"] for p in policy["comedians"][:275]]
            start = time.perf_counter()
            q.execute(
                "UPDATE comedians SET instagram_followers=123456 WHERE id=ANY(%s)",
                (ids,),
            )
            print("bulk_275_seconds", round(time.perf_counter() - start, 3), flush=True)
            q.execute(
                "SELECT count(*) FROM comedians WHERE id=ANY(%s) AND instagram_followers=123456",
                (ids,),
            )
            assert q.fetchone()[0] == 0, "Unapproved updates must remain held"
            q.execute(
                "SELECT tgenabled FROM pg_trigger WHERE tgname='curation_comedian_write'"
            )
            assert q.fetchone()[0] == "O"
            print(
                "PASS: quarantine preserves evidence/denials, approvals unchanged, parent and host preflights passed, unapproved bulk writes held",
                flush=True,
            )
    finally:
        subprocess.run(
            ["pg_ctl", "-D", data, "-m", "immediate", "-w", "stop"], check=True
        )
