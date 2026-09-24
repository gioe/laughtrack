"""Exercise repair and recovery against PostgreSQL, including user references."""

import importlib.util
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest

SPEC = importlib.util.spec_from_file_location(
    "orpheum_repair", Path(__file__).parents[3] / "scripts/core/repair_orpheum_show_cities.py"
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
    schema = "orpheum_repair_" + uuid4().hex
    cursor.execute(f"CREATE SCHEMA {schema}; SET LOCAL search_path TO {schema}")
    cursor.execute("""
        CREATE TABLE clubs (id int PRIMARY KEY, city text, state text);
        CREATE TABLE scraping_sources (club_id int, platform text, ticketmaster_id text);
        CREATE TABLE shows (id int PRIMARY KEY, club_id int, date timestamptz, room text,
            show_page_url text, last_scraped_by text);
        CREATE TABLE tickets (id serial PRIMARY KEY, show_id int REFERENCES shows ON DELETE CASCADE,
            purchase_url text, price numeric, sold_out bool, type text, UNIQUE(show_id,type));
        CREATE TABLE lineup_items (show_id int REFERENCES shows ON DELETE CASCADE, comedian_id text,
            role text, PRIMARY KEY(show_id,comedian_id));
        CREATE TABLE tagged_shows (show_id int REFERENCES shows ON DELETE CASCADE, tag_id int,
            PRIMARY KEY(show_id,tag_id));
        CREATE TABLE saved_shows (profile_id text, show_id int REFERENCES shows ON DELETE CASCADE,
            created_at timestamptz, PRIMARY KEY(profile_id,show_id));
        CREATE TABLE sent_notifications (id int PRIMARY KEY, show_id int REFERENCES shows ON DELETE CASCADE,
            user_id text, comedian_id text, notification_type text, notification_group_id text,
            UNIQUE(user_id,comedian_id,show_id,notification_type));
        CREATE TABLE ticket_purchase_click_events (id int PRIMARY KEY, show_id int REFERENCES shows ON DELETE SET NULL);
        CREATE TABLE discovery_show_feature_snapshots (id int PRIMARY KEY, show_id int REFERENCES shows ON DELETE CASCADE);
    """)
    for ident, (city, state, external) in repair.VENUES.items():
        cursor.execute("INSERT INTO clubs VALUES(%s,%s,%s)", (ident, city, state))
        cursor.execute("INSERT INTO scraping_sources VALUES(%s,'ticketmaster',%s)", (ident, external))
    for ident, (club, when, url) in repair.CANONICAL.items():
        cursor.execute("INSERT INTO shows VALUES(%s,%s,%s,'',%s,'ticketmaster_national')", (ident, club, when, url))
    for old, new in repair.MAPPING.items():
        club = 11385 if old == 3399346 else 2861
        when = datetime.fromisoformat(repair.CANONICAL[new][1]) - timedelta(hours=0 if old == 3399346 else 2)
        cursor.execute(
            "INSERT INTO shows VALUES(%s,%s,%s,'',%s,'ticketmaster_national')",
            (old, club, when, repair.CANONICAL[new][2]),
        )
    try:
        yield cursor
    finally:
        conn.rollback()
        conn.close()


def test_repair_preserves_references_and_restores_exactly(cur):
    cur.execute(
        "INSERT INTO saved_shows VALUES('profile',3313105,'2026-01-01'),('profile',6897100,'2026-02-01'),('another',3399346,'2026-01-03')"
    )
    cur.execute("INSERT INTO sent_notifications VALUES(1,3313105,'user','comedian','push','group')")
    cur.execute("INSERT INTO ticket_purchase_click_events VALUES(1,3313105)")
    cur.execute("INSERT INTO discovery_show_feature_snapshots VALUES(1,3313105)")
    cur.execute(
        "INSERT INTO tickets(show_id,price,sold_out,type) VALUES(3313105,50,false,'General'),(6897100,60,false,'General')"
    )
    cur.execute("INSERT INTO lineup_items VALUES(3313105,'performer','headliner')")
    cur.execute("INSERT INTO tagged_shows VALUES(3313105,1)")
    repair.lock_and_validate_schema(cur)
    before = repair.snapshot(cur)
    repair.validate(cur, before)
    repair.repair(cur, before)
    after = repair.snapshot(cur)
    assert len(after["shows"]) == 7
    assert {r["show_id"] for r in after["saved_shows"]} == {6897100}
    assert len(after["saved_shows"]) == 2
    assert next(r for r in after["saved_shows"] if r["profile_id"] == "profile")["created_at"].startswith("2026-01-01")
    assert after["sent_notifications"][0] == dict(before["sent_notifications"][0], show_id=6897100)
    assert after["ticket_purchase_click_events"][0]["show_id"] == 6897100
    assert not after["discovery_show_feature_snapshots"]
    assert after["tickets"][0]["price"] == 60
    assert after["lineup_items"][0]["show_id"] == 6897100
    repair.validate(cur, after)
    repair.repair(cur, after)
    assert repair.snapshot(cur) == after
    backup = {
        "task_id": 4047,
        "mapping": {str(k): v for k, v in repair.MAPPING.items()},
        "before": before,
        "after": after,
    }
    repair.restore(cur, backup)
    assert repair.snapshot(cur) == before
    repair.restore(cur, backup)


def test_changed_canonical_and_unknown_copies_fail_closed(cur):
    cur.execute("UPDATE shows SET club_id=2861 WHERE id=6897100")
    with pytest.raises(ValueError, match="Canonical show"):
        repair.validate(cur, repair.snapshot(cur))
    cur.execute("UPDATE shows SET club_id=27901 WHERE id=6897100")
    cur.execute(
        "INSERT INTO shows SELECT 999,club_id,date,room,show_page_url,last_scraped_by FROM shows WHERE id=6897100"
    )
    with pytest.raises(ValueError, match="Additional copies"):
        repair.validate(cur, repair.snapshot(cur))


def test_restore_refuses_subsequent_changes(cur):
    before = repair.snapshot(cur)
    repair.repair(cur, before)
    after = repair.snapshot(cur)
    cur.execute("UPDATE shows SET room='new room' WHERE id=6897100")
    with pytest.raises(ValueError, match="changed after repair"):
        repair.restore(
            cur,
            {
                "task_id": 4047,
                "mapping": {str(k): v for k, v in repair.MAPPING.items()},
                "before": before,
                "after": after,
            },
        )


def test_notification_collision_aborts_instead_of_discarding_history(cur):
    cur.execute(
        "INSERT INTO sent_notifications VALUES(1,3313105,'user','comedian','push','a'),(2,6897100,'user','comedian','push','b')"
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
