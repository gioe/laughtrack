"""Actual PostgreSQL guards, dependent preservation, recovery and replay."""

import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest

SPEC = importlib.util.spec_from_file_location(
    "alberta_repair", Path(__file__).parents[3] / "scripts/core/repair_next_stop_alberta_wall_times.py"
)
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


@pytest.fixture
def db():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL enables actual PostgreSQL verification")
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    schema = "alberta_" + uuid4().hex
    cur.execute(f"CREATE SCHEMA {schema}; SET LOCAL search_path TO {schema}; SET LOCAL TIME ZONE 'UTC'")
    cur.execute("""
    CREATE TABLE clubs(id int PRIMARY KEY,name text,timezone text);
    CREATE TABLE production_companies(id int PRIMARY KEY,name text,slug text,scraping_url text);
    CREATE TABLE shows(id int PRIMARY KEY,club_id int,date timestamptz,room text,name text,show_page_url text,UNIQUE(club_id,date,room));
    CREATE TABLE tickets(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,type text,price numeric,purchase_url text,sold_out bool,UNIQUE(show_id,type));
    CREATE TABLE lineup_items(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,comedian_id text,UNIQUE(show_id,comedian_id));
    CREATE TABLE tagged_shows(show_id int REFERENCES shows ON DELETE CASCADE,tag_id int,PRIMARY KEY(show_id,tag_id));
    CREATE TABLE saved_shows(show_id int REFERENCES shows ON DELETE CASCADE,profile_id text,PRIMARY KEY(show_id,profile_id));
    CREATE TABLE sent_notifications(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,user_id text);
    CREATE TABLE discovery_show_feature_snapshots(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,feature_version text,as_of timestamptz,evidence jsonb);
    CREATE TABLE ticket_purchase_click_events(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE SET NULL,club_id int);
    INSERT INTO clubs VALUES(1,'Alberta venue','America/Edmonton');
    INSERT INTO production_companies VALUES(10,'Next Stop Comedy','next-stop-comedy','https://www.nextstopcomedy.com/events');
    INSERT INTO shows VALUES(1,1,'2027-03-14T02:00Z','','Historical canonical','https://www.nextstopcomedy.com/events/alberta-2027-03-13'),
      (2,1,'2027-03-14T01:00Z','','New duplicate','https://www.nextstopcomedy.com/events/alberta-2027-03-13'),
      (3,1,'2027-02-14T03:00Z','','Standalone','https://www.nextstopcomedy.com/events/alberta-2027-02-13');
    INSERT INTO tickets VALUES(1,1,'GA',20,'https://tickets/1',false),(2,2,'VIP',30,'https://tickets/2',false);
    INSERT INTO lineup_items VALUES(1,1,'comic'),(2,2,'comic');
    INSERT INTO tagged_shows VALUES(1,10),(2,10),(2,20);
    INSERT INTO saved_shows VALUES(1,'user'),(2,'user'),(2,'other');
    INSERT INTO sent_notifications VALUES(1,1,'user'),(2,2,'user');
    INSERT INTO discovery_show_feature_snapshots VALUES(1,1,'a','2026-10-01','{}'),(2,2,'a','2026-10-02','{}');
    INSERT INTO ticket_purchase_click_events VALUES(1,1,1),(2,2,1);
    """)
    cur.execute("SELECT to_jsonb(t) FROM shows t")
    shows = {str(r[0]["id"]): r[0] for r in cur.fetchall()}
    cur.execute("SELECT to_jsonb(t) FROM production_companies t")
    source = cur.fetchone()[0]
    plan = dict(
        task_id=4119,
        captured_at="2026-10-06T00:00Z",
        organizer_id=10,
        expected_organizer=source,
        cohort_club_ids=[1],
        expected_clubs={"1": {"id": 1, "name": "Alberta venue", "timezone": "America/Edmonton"}},
        expected_shows=shows,
        groups=[
            dict(canonical_id=1, duplicate_ids=[2], target_date="2027-03-14T01:00Z"),
            dict(canonical_id=3, duplicate_ids=[], target_date="2027-02-14T02:00Z"),
        ],
    )
    try:
        yield cur, plan
    finally:
        conn.rollback()
        conn.close()


def test_preserves_business_fields_and_children_restores_reapplies(db, tmp_path):
    cur, plan = db
    result = repair.repair(cur, plan, tmp_path / "recovery.json")
    assert result["after_hash"] == repair.digest(result["after"])
    assert (tmp_path / "recovery.json").stat().st_mode & 0o777 == 0o600
    assert json.loads((tmp_path / "recovery.json.after.json").read_text()) == result
    shows = {r["id"]: r for r in result["after"]["shows"]}
    assert set(shows) == {1, 3}
    assert shows[1]["name"] == "Historical canonical"
    for table in ("tickets", "sent_notifications", "discovery_show_feature_snapshots", "ticket_purchase_click_events"):
        assert {r["id"] for r in result["before"][table]} == {r["id"] for r in result["after"][table]}
        for old in result["before"][table]:
            new = next(r for r in result["after"][table] if r["id"] == old["id"])
            assert new == dict(old, show_id=1 if old["show_id"] == 2 else old["show_id"])
    assert len(result["after"]["lineup_items"]) == 1
    assert len(result["after"]["saved_shows"]) == 2
    assert len(result["after"]["tagged_shows"]) == 2
    assert repair.repair(cur, plan)["already_applied"]
    repair.restore(cur, plan, result)
    assert repair.snapshot(cur, plan) == result["before"]
    repair.restore(cur, plan, result)
    assert repair.repair(cur, plan)["after"] == result["after"]


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE shows SET name='drift' WHERE id=1",
        "UPDATE shows SET date='2027-03-14T03:00Z' WHERE id=1",
        "UPDATE production_companies SET scraping_url='drift' WHERE id=10",
        "UPDATE clubs SET timezone='America/New_York' WHERE id=1",
        "INSERT INTO shows VALUES(4,1,'2027-04-01','','new','https://other/event')",
    ],
)
def test_drift_refuses_before_writes(db, query):
    cur, plan = db
    cur.execute(query)
    before = repair.snapshot(cur, plan)
    with pytest.raises(ValueError):
        repair.repair(cur, plan)
    assert repair.snapshot(cur, plan) == before


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE tickets SET price=99 WHERE id=1",
        "INSERT INTO saved_shows VALUES(1,'new-user')",
        "ALTER TABLE tickets ADD COLUMN drift text",
    ],
)
def test_restore_refuses_state_or_schema_drift(db, query):
    cur, plan = db
    result = repair.repair(cur, plan)
    cur.execute(query)
    with pytest.raises(ValueError):
        repair.restore(cur, plan, result)


def test_schema_coverage_fails_closed(db):
    cur, plan = db
    cur.execute("CREATE TABLE new_child(id int PRIMARY KEY,show_id int REFERENCES shows)")
    with pytest.raises(ValueError, match="foreign keys"):
        repair.repair(cur, plan)


def test_dry_run_rolls_back_all_changes(db):
    cur, plan = db
    before = repair.snapshot(cur, plan)
    cur.execute("SAVEPOINT dry_run")
    repair.repair(cur, plan)
    cur.execute("ROLLBACK TO SAVEPOINT dry_run")
    assert repair.snapshot(cur, plan) == before


def test_destination_collision_even_from_other_source(db):
    cur, plan = db
    cur.execute("INSERT INTO shows VALUES(4,1,'2027-02-14T02:00Z','','Other source','https://other/event')")
    cur.execute("SELECT to_jsonb(t) FROM shows t WHERE id=4")
    plan["expected_shows"]["4"] = cur.fetchone()[0]
    with pytest.raises(ValueError, match="destination collision"):
        repair.repair(cur, plan)


def test_conflicting_child_fails_closed(db):
    cur, plan = db
    cur.execute("UPDATE tickets SET type='GA' WHERE id=2")
    cur.execute("SAVEPOINT conflict")
    with pytest.raises(ValueError, match="Lossless merge conflict"):
        repair.repair(cur, plan)
    cur.execute("ROLLBACK TO SAVEPOINT conflict")
    assert repair.snapshot(cur, plan)["tickets"][0]["price"] == 20
