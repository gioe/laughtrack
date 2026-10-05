"""Rollback-isolated PostgreSQL coverage for the reviewed organizer repair."""

import copy
import json
import os
import stat
from pathlib import Path

import psycopg2
import pytest

from scripts.core import repair_seatengine_organizer_venues as repair


@pytest.fixture
def database():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL required for repair regression")
    connection = psycopg2.connect(dsn)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TEMP TABLE clubs(id serial PRIMARY KEY,name text UNIQUE,address text,website text,
                    city text,state text,zip_code text,timezone text,visible boolean DEFAULT true,total_shows int DEFAULT 0);
                CREATE TEMP TABLE production_companies(id serial PRIMARY KEY,name text UNIQUE,slug text UNIQUE,website text);
                CREATE TEMP TABLE production_company_venues(production_company_id int,club_id int,
                    PRIMARY KEY(production_company_id,club_id));
                CREATE TEMP TABLE scraping_sources(id int PRIMARY KEY,club_id int,enabled boolean,metadata jsonb,source_url text);
                CREATE TEMP TABLE shows(id int PRIMARY KEY,club_id int,date timestamptz,show_page_url text,
                    production_company_id int,room text DEFAULT '',scraped_by_organizer_id int,
                    is_cancelled boolean DEFAULT false, description text);
                CREATE TEMP TABLE tickets(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,
                    type text,price numeric,purchase_url text,sold_out boolean DEFAULT false,UNIQUE(show_id,type));
                CREATE TEMP TABLE lineup_items(id int,show_id int REFERENCES shows ON DELETE CASCADE,
                    comedian_id text,role text,PRIMARY KEY(show_id,comedian_id));
                CREATE TEMP TABLE tagged_shows(show_id int REFERENCES shows ON DELETE CASCADE,tag_id int,
                    PRIMARY KEY(show_id,tag_id));
                CREATE TEMP TABLE saved_shows(show_id int REFERENCES shows ON DELETE CASCADE,profile_id text,
                    created_at timestamptz,PRIMARY KEY(show_id,profile_id));
                CREATE TEMP TABLE sent_notifications(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE);
                CREATE TEMP TABLE ticket_purchase_click_events(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE SET NULL);
                CREATE TEMP TABLE discovery_show_feature_snapshots(id int PRIMARY KEY,
                    show_id int REFERENCES shows ON DELETE CASCADE,feature_version text,as_of timestamptz,
                    UNIQUE(show_id,feature_version,as_of));
                INSERT INTO clubs(id,name) VALUES(600,'Account'),(601,'Known Venue');
                INSERT INTO scraping_sources VALUES(259,600,true,'{"keep":true}','https://example.com');
                INSERT INTO shows(id,club_id,date,show_page_url,production_company_id,room) VALUES
                    (10,600,'2036-01-01T20:00Z','https://example.com/shows/100',NULL,''),
                    (11,600,'2036-01-01T20:00Z','https://example.com/duplicate',NULL,''),
                    (12,600,'2036-01-02T20:00Z','https://example.com/hold',NULL,'');
                INSERT INTO tickets(id,show_id,type,price,purchase_url) VALUES(1,10,'GA',20,'https://example.com/native'),
                    (2,11,'VIP',30,'https://example.com/old');
                INSERT INTO lineup_items VALUES(1,10,'comic','headliner'),(2,11,'comic','headliner');
                INSERT INTO tagged_shows VALUES(10,1),(11,1),(11,2);
                INSERT INTO saved_shows VALUES(11,'user','2035-01-01T00:00Z');
                INSERT INTO sent_notifications VALUES(1,11);
                INSERT INTO ticket_purchase_click_events VALUES(1,11);
                INSERT INTO discovery_show_feature_snapshots VALUES(1,11,'v1','2035-01-01T00:00Z');
            """)
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture
def plan():
    return {
        "task_id": 4109,
        "clubs": {
            "new": {
                "fields": {
                    "name": "Physical Venue",
                    "address": "1 Main St",
                    "website": "https://venue.example",
                    "city": "Chicago",
                    "state": "IL",
                    "timezone": "America/Chicago",
                }
            }
        },
        "producers": {"producer": {"fields": {"name": "Comedy producer", "slug": "comedy-producer"}}},
        "shows": [
            {
                "id": 10,
                "before": {
                    "club_id": 600,
                    "date": "2036-01-01T20:00:00Z",
                    "show_page_url": "https://example.com/shows/100",
                },
                "club": "new",
                "producer": "producer",
            }
        ],
        "holds": [
            {
                "id": 12,
                "before": {"club_id": 600, "date": "2036-01-02T20:00:00Z", "show_page_url": "https://example.com/hold"},
            },
            {"id": 13, "absent": True},
        ],
        "merges": [
            {
                "from": 11,
                "to": 10,
                "before": {
                    "club_id": 600,
                    "date": "2036-01-01T20:00:00Z",
                    "show_page_url": "https://example.com/duplicate",
                },
            }
        ],
        "sources": [
            {
                "id": 259,
                "before": {"club_id": 600, "enabled": True, "metadata": {"keep": True}},
                "patch": {
                    "metadata": {
                        "keep": True,
                        "task_4109_routing": {
                            "producer_id": {"$producer": "producer"},
                            "routes": [{"club_id": {"$club": "new"}}],
                        },
                    }
                },
            }
        ],
    }


def test_repair_preserves_relationships_holds_and_is_idempotent(database, plan, tmp_path):
    backup = tmp_path / "private.json"
    with database.cursor() as cur:
        result = repair.repair(cur, plan, backup)
        assert not result["already_applied"]
        before, after = result["before"], result["after"]
        assert {row["id"] for row in after["shows"]} == {10, 12}
        assert next(row for row in after["shows"] if row["id"] == 12) == next(
            row for row in before["shows"] if row["id"] == 12
        )
        assert {row["id"] for row in after["tickets"]} == {1, 2}
        for table in repair.CHILDREN:
            assert all(row["show_id"] == 10 for row in after[table])
        assert len(after["lineup_items"]) == 1
        assert len(after["tagged_shows"]) == 2
        assert next(row for row in after["clubs"] if row["id"] == result["clubs"]["new"])["total_shows"] == 1
        assert next(row for row in after["clubs"] if row["id"] == 600)["total_shows"] == 1
        assert repair.repair(cur, plan)["already_applied"]
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    original = json.loads(backup.read_text())
    assert "after" not in original
    assert len(original["before"]["shows"]) == 3
    assert json.loads(Path(str(backup) + ".after.json").read_text())["clubs"] == result["clubs"]


@pytest.mark.parametrize("case", ["date", "source", "absent", "child", "unknown_fk"])
def test_conflicts_abort(database, plan, case):
    with database.cursor() as cur:
        if case == "date":
            cur.execute("UPDATE shows SET date=date+interval '1 hour' WHERE id=10")
        elif case == "source":
            cur.execute("UPDATE scraping_sources SET enabled=false")
        elif case == "absent":
            cur.execute("INSERT INTO shows(id) VALUES(13)")
        elif case == "child":
            cur.execute("UPDATE lineup_items SET role='host' WHERE show_id=11")
        else:
            cur.execute("CREATE TEMP TABLE unexpected(show_id int REFERENCES shows)")
        with pytest.raises(ValueError):
            repair.repair(cur, plan)


def test_snapshot_written_before_any_business_mutation(database, plan, monkeypatch):
    def reject(path, payload):
        with database.cursor() as cur:
            cur.execute("SELECT count(*) FROM clubs")
            assert cur.fetchone()[0] == 2
            cur.execute("SELECT count(*) FROM shows")
            assert cur.fetchone()[0] == 3
        raise OSError("Backup unavailable")

    monkeypatch.setattr(repair, "save_backup", reject)
    with database.cursor() as cur, pytest.raises(OSError, match="Backup unavailable"):
        repair.repair(cur, plan, "/unused")


def test_laugh_tonight_cannot_be_enabled(plan):
    unsafe = copy.deepcopy(plan)
    unsafe["sources"][0]["id"] = 294
    with pytest.raises(ValueError, match="must remain disabled"):
        repair.validate_plan(unsafe)


def test_reviewed_alias_coalescence_description_and_cancellation(database, plan):
    with database.cursor() as cur:
        cur.execute("UPDATE tickets SET type='GA',price=NULL WHERE id=2")
        cur.execute("UPDATE shows SET description='Retained description' WHERE id=11")
        cur.execute("SELECT to_jsonb(t) FROM tickets t ORDER BY id")
        first, second = [row[0] for row in cur.fetchall()]
        plan["merges"][0].update(
            before_to={"description": None},
            patch={"description": "Retained description"},
            coalesce=[
                {
                    "table": "tickets",
                    "from_id": 2,
                    "to_id": 1,
                    "before_from": second,
                    "before_to": first,
                    "reason": "Same verified performance GA; preserve priced canonical offer and backup alias",
                }
            ],
        )
        plan["holds"][0]["before"]["is_cancelled"] = False
        plan["holds"][0]["patch"] = {"is_cancelled": True}
        result = repair.repair(cur, plan)
        assert [row["id"] for row in result["after"]["tickets"]] == [1]
        shows = {row["id"]: row for row in result["after"]["shows"]}
        assert shows[10]["description"] == "Retained description"
        assert shows[10]["scraped_by_organizer_id"] == result["producers"]["producer"]
        assert shows[12]["is_cancelled"] is True
        assert shows[12]["club_id"] == 600
        assert repair.repair(cur, plan)["already_applied"]


def test_plan_rejects_hold_venue_mutation(plan):
    plan["holds"][0]["patch"] = {"club_id": 123}
    with pytest.raises(ValueError, match="cancellation"):
        repair.validate_plan(plan)
