"""Validate TASK-4074 against production-shaped data; always roll back mutations."""
import argparse
import hashlib
import json
from pathlib import Path

import psycopg2
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
TABLES = ("tickets", "lineup_items", "tagged_shows", "discovery_show_feature_snapshots",
          "saved_shows", "sent_notifications", "ticket_purchase_click_events")


def fingerprint(cur, table, ids, omit_flag=False):
    column = "id" if table == "shows" else "show_id"
    expression = "to_jsonb(t)-'is_cancelled'" if omit_flag else "to_jsonb(t)"
    cur.execute(f"SELECT {expression} FROM {table} t WHERE {column}=ANY(%s)", (ids,))
    rows = sorted(json.dumps(r[0], sort_keys=True, separators=(",", ":")) for r in cur.fetchall())
    return {"count": len(rows), "sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    v = dotenv_values(args.env_file)
    conn = psycopg2.connect(host=v["DATABASE_HOST"], dbname=v["DATABASE_NAME"],
                            user=v["DATABASE_USER"], password=v["DATABASE_PASSWORD"],
                            port=v.get("DATABASE_PORT", 5432), sslmode="require")
    conn.set_session(isolation_level="REPEATABLE READ")
    sql = (HERE.parents[4] / "apps/web/prisma/migrations/20260930000000_retain_cancelled_next_stop_shows/migration.sql").read_text()
    targets = [r["id"] for r in json.loads((HERE / "repair-plan.json").read_text())]
    cohort = [r["id"] for r in json.loads((HERE / "db-before.json").read_text())["rows"]]
    result = {}
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='60s'")
            before = {t: fingerprint(cur, t, cohort, t == "shows") for t in ("shows",) + TABLES}
            cur.execute(sql)
            cur.execute("SELECT id FROM shows WHERE id=ANY(%s) AND is_cancelled ORDER BY id", (targets,))
            assert [r[0] for r in cur.fetchall()] == sorted(targets)
            after = {t: fingerprint(cur, t, cohort, t == "shows") for t in ("shows",) + TABLES}
            assert before == after, "Show fields or dependent records changed"
            cur.execute("SELECT count(*) FROM shows WHERE id=ANY(%s) AND NOT (id=ANY(%s)) AND is_cancelled", (cohort, targets))
            assert cur.fetchone()[0] == 0, "Active/unresolved/past cohort was canceled"
            first = fingerprint(cur, "shows", cohort)
            cur.execute(sql)
            assert first == fingerprint(cur, "shows", cohort), "Repair is not idempotent"
            cur.execute("SAVEPOINT identity_guard")
            cur.execute("UPDATE shows SET show_page_url=show_page_url||'#identity-drift' WHERE id=%s", (targets[0],))
            try:
                cur.execute(sql)
            except psycopg2.Error as exc:
                assert "identity drift" in str(exc)
                cur.execute("ROLLBACK TO SAVEPOINT identity_guard")
            else:
                raise AssertionError("Identity drift was not rejected")
            result = {"mode": "rolled_back", "targets": len(targets), "cohort": len(cohort),
                      "preserved": before, "idempotence": "passed", "identity_guard": "passed"}
        conn.rollback()
        with conn.cursor() as cur:
            restored = {t: fingerprint(cur, t, cohort, t == "shows") for t in ("shows",) + TABLES}
            assert before == restored, "Rollback did not preserve original records"
        result["rollback"] = "passed"
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
    finally:
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    main()
