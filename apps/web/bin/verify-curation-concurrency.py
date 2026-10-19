#!/usr/bin/env python3
"""Disposable native PostgreSQL contention check. Never reads a configured DSN.
Run with apps/scraper/.venv/bin/python apps/web/bin/verify-curation-concurrency.py.
Requires initdb/pg_ctl on PATH; uses only a private temporary Unix socket.
"""

import ast
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import uuid
import psycopg2

WEB = Path(__file__).resolve().parents[1]
FIXTURES = WEB / "lib/admin/curation/fixtures"
for binary in ("initdb", "pg_ctl"):
    if not shutil.which(binary):
        raise SystemExit(
            f"{binary} required: install PostgreSQL before running this check"
        )


def main():
    with tempfile.TemporaryDirectory(prefix="curation-") as tmp:
        data = str(Path(tmp) / "data")
        subprocess.run(
            ["initdb", "-D", data, "-A", "trust", "--no-locale", "--encoding=UTF8"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "pg_ctl",
                "-D",
                data,
                "-l",
                str(Path(tmp) / "postgres.log"),
                "-o",
                f"-k {tmp} -h '' -p 55486",
                "-w",
                "start",
            ],
            check=True,
            capture_output=True,
        )
        try:
            check(tmp)
        finally:
            subprocess.run(
                ["pg_ctl", "-D", data, "-m", "immediate", "-w", "stop"],
                check=True,
                capture_output=True,
            )


def check(socket):
    def connect():
        c = psycopg2.connect(host=socket, port=55486, dbname="postgres")
        with c.cursor() as cur:
            cur.execute("SET statement_timeout='10s'")
        c.commit()
        return c

    admin = connect()
    with admin.cursor() as c:
        c.execute((FIXTURES / "endToEnd.sql").read_text())
        for migration in json.loads((FIXTURES / "migrations.json").read_text()):
            c.execute(
                (WEB / "prisma/migrations" / migration / "migration.sql").read_text()
            )
        c.execute(
            "SELECT curation_approve_comedian('native-person','Native Person','admin','Verified identity')"
        )
        c.execute(
            "INSERT INTO comedians(uuid,name,identity_validated_at,identity_validated_by) VALUES('native-person','Native Person',now(),'admin') RETURNING id"
        )
        person = c.fetchone()[0]
        c.execute("SELECT id FROM curation_entities WHERE comedian_id=%s", (person,))
        entity = c.fetchone()[0]
    admin.commit()

    def block(conn):
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason) SELECT %s,id,version+1,'block',disposition,'blocked','admin','Native concurrency verification' FROM curation_entities WHERE id=%s",
                (str(uuid.uuid4()), entity),
            )

    # A blocked identity wins against an old writer already waiting on the fence.
    blocker = connect()
    writer = connect()
    block(blocker)

    def stale_write():
        with writer.cursor() as c:
            c.execute(
                "INSERT INTO comedians(uuid,name) VALUES('rediscovered','Native Person') RETURNING id"
            )
            row = c.fetchone()
        writer.commit()
        return row

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(stale_write)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with admin.cursor() as c:
                c.execute(
                    "SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s",
                    (writer.get_backend_pid(),),
                )
                waiting = c.fetchone()[0] == "Lock"
            admin.commit()
            if waiting:
                break
            time.sleep(0.02)
        assert waiting, "Old writer never waited on the publication fence"
        blocker.commit()
        assert (
            future.result(timeout=10) is None
        ), "Old writer republished a denied comedian"
    # A crashed worker loses all uncommitted effects; restarting cannot override denial.
    crashed = connect()
    with crashed.cursor() as c:
        c.execute("UPDATE comedians SET visible=true WHERE uuid='native-person'")
    crashed.close()
    assert stale_write() is None
    with admin.cursor() as c:
        c.execute(
            "SELECT disposition,version FROM curation_entities WHERE id=%s", (entity,)
        )
        assert c.fetchone() == ("blocked", 2)
        c.execute(
            "SELECT disposition FROM curation_comedian_policy('native-person','Native Person',%s)",
            (person,),
        )
        assert c.fetchone() == ("blocked",)
        # Exercise the exact production notification predicate with real SQL.
        c.execute(
            "SELECT curation_approve_comedian('native-other','Native Other','admin','Verified identity')"
        )
        c.execute(
            "INSERT INTO comedians(uuid,name,identity_validated_at,identity_validated_by) VALUES('native-other','Native Other',now(),'admin')"
        )
        venue = json.dumps(
            dict(name="Native Room", address="1 Main St", city="Boston", state="MA")
        )
        c.execute(
            "SELECT curation_approve_club(%s::jsonb,'admin','Verified venue')", (venue,)
        )
        c.execute(
            "INSERT INTO clubs(name,address,city,state) VALUES('Native Room','1 Main St','Boston','MA') RETURNING id"
        )
        club = c.fetchone()[0]
        c.execute(
            "INSERT INTO shows(name,club_id,date) VALUES('Native Show',%s,'2029-01-01') RETURNING id",
            (club,),
        )
        show = c.fetchone()[0]
        c.execute(
            "INSERT INTO lineup_items(show_id,comedian_id) VALUES(%s,%s)",
            (show, "native-other"),
        )
        module = ast.parse(
            (
                WEB.parent
                / "scraper/src/laughtrack/core/services/notification/service.py"
            ).read_text()
        )
        query = next(
            ast.literal_eval(n.value)
            for n in module.body
            if isinstance(n, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "_SHOW_PROMOTION_SQL"
                for t in n.targets
            )
        )
        for identities, allowed in [
            (["native-other"], True),
            (["native-person"], False),
            (["native-person", "native-other"], False),
        ]:
            c.execute(query, (identities, show, identities))
            assert bool(c.fetchone()) is allowed
        c.execute(
            "SELECT curation_approve_comedian('native-alias','Native Alias','admin','Verified identity')"
        )
        c.execute(
            "INSERT INTO comedians(uuid,name,identity_validated_at,identity_validated_by) VALUES('native-alias','Native Alias',now(),'admin') RETURNING id"
        )
        alias = c.fetchone()[0]
        c.execute("SELECT id FROM comedians WHERE uuid='native-other'")
        parent = c.fetchone()[0]
        c.execute("DELETE FROM lineup_items WHERE show_id=%s", (show,))
        c.execute(
            "INSERT INTO lineup_items(show_id,comedian_id) VALUES(%s,'native-alias')",
            (show,),
        )
        evidence = json.dumps(
            dict(
                samePerformer=True,
                sourceUrl="https://example.org/bio",
                explanation="The biography explicitly confirms both performer names.",
            )
        )
        c.execute(
            "SELECT curation_propose_parent(%s,%s,%s::jsonb,'admin','Verified alias')",
            (alias, parent, evidence),
        )
        edge = c.fetchone()[0]
        for action, before, after in [
            ("confirm", "proposed", "confirmed"),
            ("sever", "confirmed", "severed"),
        ]:
            c.execute(
                "INSERT INTO curation_decisions(id,relationship_id,version,action,before_state,after_state,actor,reason) SELECT %s,id,version+1,%s,%s,%s,'admin','Verified relationship' FROM curation_relationships WHERE id=%s",
                (str(uuid.uuid4()), action, before, after, edge),
            )
            c.execute(query, (["native-other"], show, ["native-other"]))
            assert bool(c.fetchone()) is (
                action == "confirm"
            ), "Queued attribution did not follow current parent membership"
    admin.commit()
    for conn in (writer, blocker, admin):
        conn.close()
    print(
        "PASS: all migrations, native two-connection lock contention, stale writer, crash/restart, blocked promotion and unrelated performer"
    )


if __name__ == "__main__":
    main()
