"""Annoyance identity repair preserves IDs and all relationships, and refuses drift."""

import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest

from scripts.core import repair_annoyance_identity as repair


@pytest.fixture
def fixture():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL required for PostgreSQL repair regression")
    connection = psycopg2.connect(dsn)
    cur = connection.cursor()
    name = "annoyance_" + uuid4().hex
    cur.execute(f"CREATE SCHEMA {name}; SET LOCAL search_path TO {name}; SET LOCAL TIME ZONE 'UTC'")
    cur.execute("""
        CREATE TABLE scraping_sources(id int PRIMARY KEY,club_id int,source_url text,scraper_key text,enabled bool,metadata jsonb);
        CREATE TABLE shows(id int PRIMARY KEY,club_id int,date timestamptz,room text,name text,show_page_url text,last_scraped_by text,source_performance_id text);
        CREATE UNIQUE INDEX source_identity_key ON shows(club_id,source_performance_id) WHERE source_performance_id IS NOT NULL;
        CREATE TABLE tickets(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,purchase_url text);
        CREATE TABLE lineup_items(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE);
        CREATE TABLE tagged_shows(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE);
        CREATE TABLE saved_shows(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE);
        CREATE TABLE sent_notifications(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE);
        CREATE TABLE discovery_show_feature_snapshots(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE);
        CREATE TABLE ticket_purchase_click_events(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE SET NULL);
        INSERT INTO scraping_sources VALUES(53,183,'https://theannoyance.thundertix.com','thundertix',true,'{"keep":"value"}');
        INSERT INTO shows VALUES(1,183,'2026-11-01T00:00Z','','Existing','https://theannoyance.thundertix.com/events/100','thundertix',NULL),
          (99,183,'2020-01-01T00:00Z','','History','https://theannoyance.thundertix.com/events/99','thundertix',NULL);
        INSERT INTO tickets VALUES(1,1,'https://theannoyance.thundertix.com/orders/new?event_id=100&performance_id=200');
    """)
    cur.execute("""
        ALTER TABLE scraping_sources ADD COLUMN updated_at timestamptz DEFAULT '2000-01-01T00:00Z';
        CREATE FUNCTION set_source_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN NEW.updated_at = NOW(); RETURN NEW; END $$;
        CREATE TRIGGER scraping_sources_set_updated_at BEFORE UPDATE ON scraping_sources
        FOR EACH ROW EXECUTE FUNCTION set_source_updated_at();
    """)
    for table in repair.CHILDREN[1:]:
        cur.execute(f"INSERT INTO {table} VALUES(1,1),(99,99)")
    cur.execute("SELECT to_jsonb(t) FROM scraping_sources t")
    source = cur.fetchone()[0]
    cur.execute("SELECT to_jsonb(t)-'source_performance_id' FROM shows t WHERE id=1")
    show = cur.fetchone()[0]
    plan = {
        "club_id": 183,
        "source_id": 53,
        "expected_source": source,
        "expected_shows": {"1": show},
        "identity_updates": {"1": "thundertix:theannoyance:100:200"},
        "expected_ticket_urls": {
            "1": ["https://theannoyance.thundertix.com/orders/new?event_id=100&performance_id=200"]
        },
        "activation_metadata": {"source_performance_identity": True},
        "historical_rows_unchanged": 1,
        "retire_ids": [],
    }
    try:
        yield cur, plan
    finally:
        connection.rollback()
        connection.close()


def test_apply_repeat_restore_and_private_backup(fixture, tmp_path):
    cur, plan = fixture
    backup = repair.repair(cur, plan)
    assert backup["before"]["shows"] != backup["after"]["shows"]
    assert backup["before"]["scraping_sources"][0]["updated_at"] != backup["after"]["scraping_sources"][0]["updated_at"]
    for table in repair.CHILDREN:
        assert backup["before"][table] == backup["after"][table]
    history_before = next(r for r in backup["before"]["shows"] if r["id"] == 99)
    assert history_before == next(r for r in backup["after"]["shows"] if r["id"] == 99)
    repeat = repair.repair(cur, plan)
    assert repeat["before"] == repeat["after"] == backup["after"]
    destination = tmp_path / "private.json"
    repair.save_backup(destination, backup)
    assert destination.stat().st_mode & 0o777 == 0o600
    assert json.loads(destination.read_text()) == backup
    with pytest.raises(FileExistsError):
        repair.save_backup(destination, backup)
    repair.restore(cur, plan, backup)
    restored = repair.snapshot(cur, plan)
    assert repair.same_business_state(restored, backup["before"], plan["source_id"])
    assert restored["scraping_sources"][0]["updated_at"] != backup["before"]["scraping_sources"][0]["updated_at"]
    repair.restore(cur, plan, backup)


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE shows SET room='Invented' WHERE id=1",
        "UPDATE tickets SET purchase_url='https://wrong.example' WHERE id=1",
        "UPDATE scraping_sources SET enabled=false WHERE id=53",
        "UPDATE scraping_sources SET metadata=metadata WHERE id=53",
        "UPDATE shows SET source_performance_id='thundertix:theannoyance:100:200' WHERE id=99",
        "CREATE TABLE unknown_child(show_id int REFERENCES shows)",
    ],
)
def test_drift_refuses_before_mutation(fixture, mutation):
    cur, plan = fixture
    cur.execute(mutation)
    before = repair.snapshot(cur, plan)
    with pytest.raises(ValueError):
        repair.repair(cur, plan)
    assert repair.snapshot(cur, plan) == before


def test_restore_refuses_relationship_drift(fixture):
    cur, plan = fixture
    backup = repair.repair(cur, plan)
    cur.execute("INSERT INTO saved_shows VALUES(2,1)")
    before = repair.snapshot(cur, plan)
    with pytest.raises(ValueError, match="Affected rows changed"):
        repair.restore(cur, plan, backup)
    assert repair.snapshot(cur, plan) == before


def test_dry_run_rollback_is_exact(fixture):
    cur, plan = fixture
    before = repair.snapshot(cur, plan)
    cur.execute("SAVEPOINT dry_run")
    repair.repair(cur, plan)
    cur.execute("ROLLBACK TO SAVEPOINT dry_run")
    assert repair.snapshot(cur, plan) == before


def test_restore_still_requires_exact_after_timestamp(fixture):
    cur, plan = fixture
    backup = repair.repair(cur, plan)
    backup["after"]["scraping_sources"][0]["updated_at"] = "2001-01-01T00:00:00+00:00"
    with pytest.raises(ValueError, match="Affected rows changed"):
        repair.restore(cur, plan, backup)
