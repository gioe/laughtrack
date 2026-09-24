"""Exercise repair and recovery against PostgreSQL, including user references."""

import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest

SPEC = importlib.util.spec_from_file_location(
    "sesh_repair", Path(__file__).parents[3] / "scripts/archive/repair_sesh_locations_2026_09_24.py"
)
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


@pytest.fixture
def cur():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL repair integration tests")
    conn = psycopg2.connect(dsn)
    cursor = conn.cursor()
    schema = "sesh_repair_" + uuid4().hex
    cursor.execute(f"CREATE SCHEMA {schema}; SET LOCAL search_path TO {schema}")
    cursor.execute("""
        CREATE TABLE clubs (id int PRIMARY KEY, city text, state text, timezone text, address text);
        CREATE TABLE scraping_sources (id int, club_id int, platform text, scraper_key text, source_url text);
        CREATE TABLE shows (id int PRIMARY KEY, club_id int, date timestamptz, room text, name text,
            show_page_url text, last_scraped_by text);
        CREATE TABLE tickets (id serial PRIMARY KEY, show_id int REFERENCES shows ON DELETE CASCADE,
            purchase_url text, price numeric, sold_out bool, type text, UNIQUE(show_id,type));
        CREATE TABLE lineup_items (id serial UNIQUE, show_id int REFERENCES shows ON DELETE CASCADE, comedian_id text,
            role text, PRIMARY KEY(show_id,comedian_id));
        CREATE TABLE tagged_shows (id serial UNIQUE, show_id int REFERENCES shows ON DELETE CASCADE, tag_id int,
            PRIMARY KEY(show_id,tag_id));
        CREATE TABLE saved_shows (profile_id text, show_id int REFERENCES shows ON DELETE CASCADE,
            created_at timestamptz, PRIMARY KEY(profile_id,show_id));
        CREATE TABLE sent_notifications (id int PRIMARY KEY, show_id int REFERENCES shows ON DELETE CASCADE,
            user_id text, comedian_id text, notification_type text, notification_group_id text,
            UNIQUE(user_id,comedian_id,show_id,notification_type));
        CREATE TABLE ticket_purchase_click_events (id int PRIMARY KEY, show_id int REFERENCES shows ON DELETE SET NULL);
        CREATE TABLE discovery_show_feature_snapshots (id int PRIMARY KEY, show_id int REFERENCES shows ON DELETE CASCADE, feature_version text, as_of timestamptz, computed_at timestamptz, evidence jsonb, UNIQUE(show_id,feature_version,as_of));
    """)
    cursor.execute(
        "INSERT INTO clubs VALUES(16057,'New York','NY','America/New_York','55 Chrystie St, New York, NY 10002, USA')"
    )
    cursor.execute(
        "INSERT INTO scraping_sources VALUES(7653,16057,'custom','fullcalendar_json','https://www.seshcomedy.com/feed.php')"
    )
    for ident, row in repair.EXPECTED.items():
        cursor.execute(
            "INSERT INTO shows VALUES(%s,16057,%s,%s,%s,%s,'fullcalendar_json')",
            (ident, row["date"], row["room"], row["name"], row["show_page_url"]),
        )
    try:
        yield cursor
    finally:
        conn.rollback()
        conn.close()


def test_repair_preserves_references_and_restores_exactly(cur):
    cur.execute(
        "INSERT INTO saved_shows VALUES('profile',6029206,'2026-01-01'),('profile',6085452,'2026-02-01'),('another',6085453,'2026-01-03')"
    )
    cur.execute("INSERT INTO sent_notifications VALUES(1,6029206,'user','comedian','push','group')")
    cur.execute("INSERT INTO ticket_purchase_click_events VALUES(1,6029206)")
    cur.execute("""INSERT INTO discovery_show_feature_snapshots VALUES
       (1,6029204,'v1','2026-09-20','2026-09-21','{"old":true}'),
       (2,6085451,'v1','2026-09-20','2026-09-20','{"canonical":true}'),
       (3,6029206,'v2','2026-09-20','2026-09-22','{"distinct":true}')""")
    cur.execute(
        "INSERT INTO tickets(show_id,price,sold_out,type) VALUES(6029206,50,false,'General'),(6085452,60,false,'General')"
    )
    cur.execute("INSERT INTO lineup_items(show_id,comedian_id,role) VALUES(6029206,'performer','headliner')")
    cur.execute("INSERT INTO tagged_shows(show_id,tag_id) VALUES(6029206,1)")
    repair.lock_and_validate_schema(cur)
    before = repair.snapshot(cur)
    repair.validate(cur, before)
    repair.repair(cur, before)
    after = repair.snapshot(cur)
    assert len(after["shows"]) == 13
    assert {r["show_id"] for r in after["saved_shows"]} == {6085452}
    assert len(after["saved_shows"]) == 2
    assert next(r for r in after["saved_shows"] if r["profile_id"] == "profile")["created_at"].startswith("2026-01-01")
    assert after["sent_notifications"][0] == dict(before["sent_notifications"][0], show_id=6085452)
    assert after["ticket_purchase_click_events"][0]["show_id"] == 6085452
    assert {r["id"] for r in after["discovery_show_feature_snapshots"]} == {1}
    assert {r["show_id"] for r in after["discovery_show_feature_snapshots"]} == {6085451}
    assert after["tickets"][0]["price"] == 60
    assert after["lineup_items"][0]["show_id"] == 6085452
    repair.validate(cur, after)
    repair.repair(cur, after)
    assert repair.snapshot(cur) == after
    backup = {
        "task_id": 4048,
        "mapping": {str(k): v for k, v in repair.MAPPING.items()},
        "before": before,
        "after": after,
    }
    repair.restore(cur, backup)
    assert repair.snapshot(cur) == before
    repair.restore(cur, backup)


def test_changed_canonical_and_unknown_copies_fail_closed(cur):
    cur.execute("UPDATE shows SET club_id=2861 WHERE id=6085452")
    with pytest.raises(ValueError, match="Reviewed show"):
        repair.validate(cur, repair.snapshot(cur))
    cur.execute("UPDATE shows SET club_id=16057 WHERE id=6085452")
    cur.execute(
        "INSERT INTO shows SELECT 999,club_id,date,room,name,show_page_url,last_scraped_by FROM shows WHERE id=6085452"
    )
    with pytest.raises(ValueError, match="Additional copies"):
        repair.validate(cur, repair.snapshot(cur))


def test_restore_refuses_subsequent_changes(cur):
    before = repair.snapshot(cur)
    repair.repair(cur, before)
    after = repair.snapshot(cur)
    cur.execute("UPDATE shows SET room='new room' WHERE id=6085452")
    with pytest.raises(ValueError, match="changed after repair"):
        repair.restore(
            cur,
            {
                "task_id": 4048,
                "mapping": {str(k): v for k, v in repair.MAPPING.items()},
                "before": before,
                "after": after,
            },
        )


def test_notification_collision_aborts_instead_of_discarding_history(cur):
    cur.execute(
        "INSERT INTO sent_notifications VALUES(1,6029206,'user','comedian','push','a'),(2,6085452,'user','comedian','push','b')"
    )
    before = repair.snapshot(cur)
    cur.execute("SAVEPOINT attempt")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        repair.repair(cur, before)
    cur.execute("ROLLBACK TO SAVEPOINT attempt")
    assert repair.snapshot(cur) == before


def test_backup_is_private_and_never_overwritten(tmp_path):
    target = tmp_path / "recovery.json"
    repair.save_backup(target, {"before": "original"})
    assert target.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        repair.save_backup(target, {"before": "lost"})
    assert json.loads(target.read_text()) == {"before": "original"}


def test_shape_guard_refuses_new_children_and_copy_columns(cur):
    cur.execute("SAVEPOINT shape")
    cur.execute("CREATE TABLE unknown_child(show_id int REFERENCES shows)")
    with pytest.raises(ValueError, match="child schema changed"):
        repair.lock_and_validate_schema(cur)
    cur.execute("ROLLBACK TO SAVEPOINT shape")
    cur.execute("ALTER TABLE tickets ADD COLUMN new_business_field text")
    with pytest.raises(ValueError, match="column shape changed"):
        repair.lock_and_validate_schema(cur)


def test_distinct_ticket_urls_remain_distinct_and_canonical_times_unchanged(cur):
    before = repair.snapshot(cur)
    repair.validate(cur, before)
    repair.repair(cur, before)
    after = repair.snapshot(cur)
    rows = {r["id"]: r for r in after["shows"]}
    assert rows[6670869]["show_page_url"] != rows[6085452]["show_page_url"]
    assert rows[6670869]["date"] != rows[6085452]["date"]
    expected = {r["id"]: r for r in before["shows"] if r["id"] in repair.CANONICAL_IDS}
    assert rows == expected


def test_changed_stale_identity_is_not_merged(cur):
    cur.execute("UPDATE shows SET show_page_url='https://example.com/other' WHERE id=6029205")
    with pytest.raises(ValueError, match="Reviewed show 6029205"):
        repair.validate(cur, repair.snapshot(cur))


def test_backup_failure_rolls_back_transaction(cur, tmp_path, monkeypatch):
    before = repair.snapshot(cur)
    cur.execute("SAVEPOINT backup_attempt")
    repair.repair(cur, before)

    def fail(_):
        raise OSError("disk full")

    monkeypatch.setattr(repair.os, "fsync", fail)
    with pytest.raises(OSError, match="disk full"):
        repair.save_backup(tmp_path / "recovery.json", {"before": before, "after": repair.snapshot(cur)})
    cur.execute("ROLLBACK TO SAVEPOINT backup_attempt")
    assert repair.snapshot(cur) == before
