"""Real PostgreSQL verification of bounded Port showtime repair and recovery."""

import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest

SPEC = importlib.util.spec_from_file_location(
    "port_repair", Path(__file__).parents[3] / "scripts/archive/repair_port_showtimes_2026_09_24.py"
)
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


@pytest.fixture
def cur(monkeypatch):
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL enables actual PostgreSQL repair verification")
    conn = psycopg2.connect(dsn)
    cursor = conn.cursor()
    name = "port_repair_" + uuid4().hex
    cursor.execute(f"CREATE SCHEMA {name}; SET LOCAL search_path TO {name}; SET LOCAL TIME ZONE 'UTC'")
    cursor.execute("""
    CREATE TABLE scraping_sources(id int PRIMARY KEY,club_id int,source_url text,scraper_key text,enabled bool,metadata jsonb);
    CREATE TABLE shows(id int PRIMARY KEY,club_id int,date timestamptz,room text,name text,show_page_url text,last_scraped_by text,UNIQUE(club_id,date,room));
    CREATE TABLE tickets(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,price numeric);
    CREATE TABLE lineup_items(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,comedian_id text);
    CREATE TABLE tagged_shows(show_id int REFERENCES shows ON DELETE CASCADE,tag_id int,PRIMARY KEY(show_id,tag_id));
    CREATE TABLE saved_shows(show_id int REFERENCES shows ON DELETE CASCADE,profile_id text,PRIMARY KEY(show_id,profile_id));
    CREATE TABLE sent_notifications(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,user_id text);
    CREATE TABLE discovery_show_feature_snapshots(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,evidence jsonb);
    CREATE TABLE ticket_purchase_click_events(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE SET NULL,club_id int);
    INSERT INTO scraping_sources VALUES(7054,11482,'https://wl.eventim.us/port','seetickets_whitelabel',true,'{"keep":"unchanged"}');
    INSERT INTO shows VALUES(1,11482,'2026-09-24T04:00:00Z','','Verified tonight','https://example.com/1','seetickets_whitelabel'),
      (2,11482,'2026-10-24T04:00:00Z','','Retire reviewed event','https://example.com/2','seetickets_whitelabel'),
      (99,11482,'2020-01-01T05:00:00Z','','Historical','https://example.com/99','old_scraper');
    INSERT INTO tickets VALUES(1,1,25),(2,2,30),(99,99,15);
    INSERT INTO lineup_items VALUES(1,1,'comic'),(2,2,'comic'),(99,99,'historic');
    INSERT INTO tagged_shows VALUES(1,10),(2,10),(99,10);
    INSERT INTO saved_shows VALUES(1,'user'),(2,'user'),(99,'user');
    INSERT INTO sent_notifications VALUES(1,1,'user'),(2,2,'user'),(99,99,'user');
    INSERT INTO discovery_show_feature_snapshots VALUES(1,1,'{}'),(2,2,'{}'),(99,99,'{}');
    INSERT INTO ticket_purchase_click_events VALUES(1,1,11482),(2,2,11482),(3,2,NULL),(99,99,11482),(100,NULL,11482);
    """)
    cursor.execute("SELECT to_jsonb(t) FROM scraping_sources t")
    source = cursor.fetchone()[0]
    cursor.execute("SELECT to_jsonb(t) FROM shows t")
    originals = {str(r[0]["id"]): r[0] for r in cursor.fetchall()}
    monkeypatch.setattr(
        repair,
        "REVIEWED_PLAN",
        {
            "captured_at": "2026-09-24T12:00:00Z",
            "expected_source": source,
            "expected_source_ids": [7054],
            "expected_future_ids": [2],
            "expected_shows": originals,
            "updates": {"1": "2026-09-24T23:00:00Z"},
            "retire_ids": [2],
        },
    )
    try:
        yield cursor
    finally:
        conn.rollback()
        conn.close()


def apply(cur):
    schema = repair.lock_and_validate_schema(cur)
    before = repair.snapshot(cur)
    clicks = [r["id"] for r in before["ticket_purchase_click_events"]]
    repair.repair(cur, before)
    after = repair.snapshot(cur, clicks)
    repair.validate(cur, after)
    return {
        "task_id": 4050,
        "plan_hash": repair.plan_hash(),
        "schema": schema,
        "click_ids": clicks,
        "before": before,
        "after": after,
    }


def test_preserves_relationships_source_history_and_exact_restore(cur):
    backup = apply(cur)
    before, after = backup["before"], backup["after"]
    assert {r["id"] for r in after["shows"]} == {1, 99}
    for table in repair.CHILDREN:
        if table == "ticket_purchase_click_events":
            assert {r["id"] for r in before[table]} == {r["id"] for r in after[table]}
            assert all(r["show_id"] is None for r in after[table] if r["id"] in (2, 3))
        else:
            assert [r for r in before[table] if r["show_id"] != 2] == after[table]
    assert [r for r in before["shows"] if r["id"] == 99] == [r for r in after["shows"] if r["id"] == 99]
    original_source = before["scraping_sources"][0]
    new_source = after["scraping_sources"][0]
    assert {k: v for k, v in original_source.items() if k != "metadata"} == {
        k: v for k, v in new_source.items() if k != "metadata"
    }
    assert new_source["metadata"]["keep"] == "unchanged"
    assert new_source["metadata"]["calendar_url"] == repair.CALENDAR_URL
    repair.repair(cur, after)
    assert repair.snapshot(cur, backup["click_ids"]) == after
    repair.restore(cur, backup)
    assert repair.snapshot(cur, backup["click_ids"]) == before
    repair.restore(cur, backup)


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE shows SET name='changed' WHERE id=1",
        "UPDATE shows SET last_scraped_by='new' WHERE id=1",
        "UPDATE shows SET date='2026-09-24T05:00:00Z' WHERE id=1",
        "UPDATE scraping_sources SET source_url='changed' WHERE id=7054",
        "INSERT INTO scraping_sources VALUES(7000,11482,'other','other',true,'{}')",
        "INSERT INTO shows VALUES(3,11482,'2026-10-25T04:00:00Z','','new','new','seetickets_whitelabel')",
        "INSERT INTO shows VALUES(3,11482,'2026-09-24T23:00:00Z','','collision','new','seetickets_whitelabel')",
    ],
)
def test_refuses_drift_before_writes(cur, query):
    cur.execute(query)
    before = repair.snapshot(cur)
    with pytest.raises(ValueError):
        repair.repair(cur, before)
    assert repair.snapshot(cur) == before


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO saved_shows VALUES(1,'new-user')",
        "UPDATE ticket_purchase_click_events SET club_id=77 WHERE id=2",
        "UPDATE shows SET name='historical drift' WHERE id=99",
        "ALTER TABLE tickets ADD COLUMN changed text",
    ],
)
def test_restore_refuses_post_state_or_schema_drift(cur, query):
    backup = apply(cur)
    cur.execute(query)
    with pytest.raises(ValueError):
        repair.restore(cur, backup)


def test_unknown_fk_refuses(cur):
    cur.execute("CREATE TABLE extra(id int PRIMARY KEY,show_id int REFERENCES shows)")
    with pytest.raises(ValueError, match="foreign keys"):
        repair.lock_and_validate_schema(cur)


def test_transaction_rollback_preserves_exact_before(cur):
    before = repair.snapshot(cur)
    cur.execute("SAVEPOINT dry_run")
    apply(cur)
    cur.execute("ROLLBACK TO SAVEPOINT dry_run")
    assert repair.snapshot(cur) == before


def test_backup_is_private_exclusive_and_fsynced(tmp_path, monkeypatch):
    calls = []
    original = os.fsync

    def fsync(fd):
        calls.append(fd)
        original(fd)

    monkeypatch.setattr(os, "fsync", fsync)
    path = tmp_path / "recovery.json"
    repair.save_backup(path, {"private": "data"})
    assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(path.read_text()) == {"private": "data"}
    assert len(calls) == 2
    with pytest.raises(FileExistsError):
        repair.save_backup(path, {})


def test_click_cascade_schema_drift_refuses(cur):
    cur.execute("ALTER TABLE ticket_purchase_click_events DROP CONSTRAINT ticket_purchase_click_events_show_id_fkey")
    cur.execute("ALTER TABLE ticket_purchase_click_events ADD FOREIGN KEY(show_id) REFERENCES shows ON DELETE CASCADE")
    with pytest.raises(ValueError, match="foreign keys"):
        repair.lock_and_validate_schema(cur)


def test_reviewed_retirement_cannot_include_history(cur, monkeypatch):
    plan = json.loads(json.dumps(repair.REVIEWED_PLAN))
    plan["retire_ids"].append(99)
    monkeypatch.setattr(repair, "REVIEWED_PLAN", plan)
    with pytest.raises(ValueError, match="historical"):
        repair.repair(cur, repair.snapshot(cur))


@pytest.mark.parametrize(
    "actual,wanted,valid",
    [
        ("2026-06-30T22:19:49.33529+00:00", "2026-06-30T22:19:49.335290+00:00", True),
        (None, None, True),
        (None, "2026-06-30T22:19:49.335290+00:00", False),
        ("2026-06-30T22:19:49.33529+00:00", None, False),
        ("2026-06-30T22:19:49.335291+00:00", "2026-06-30T22:19:49.335290+00:00", False),
    ],
)
def test_scrape_timestamp_guard_compares_instants_null_safely(cur, monkeypatch, actual, wanted, valid):
    plan = json.loads(json.dumps(repair.REVIEWED_PLAN))
    plan["expected_shows"]["1"]["last_scraped_date"] = wanted
    monkeypatch.setattr(repair, "REVIEWED_PLAN", plan)
    state = repair.snapshot(cur)
    next(row for row in state["shows"] if row["id"] == 1)["last_scraped_date"] = actual
    if valid:
        assert repair.validate(cur, state) is False
    else:
        with pytest.raises(ValueError, match="last_scraped_date drift"):
            repair.validate(cur, state)
