"""Real PostgreSQL coverage for bounded same-city repair and exact recovery."""

import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest

SPEC = importlib.util.spec_from_file_location(
    "same_city_repair", Path(__file__).parents[3] / "scripts/archive/repair_same_city_assignments_2026_09_24.py"
)
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


@pytest.fixture
def cur():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL enables actual PostgreSQL repair verification")
    conn = psycopg2.connect(dsn)
    conn.set_client_encoding("UTF8")
    cursor = conn.cursor()
    name = "same_city_" + uuid4().hex
    cursor.execute(f"CREATE SCHEMA {name}; SET LOCAL search_path TO {name}; SET LOCAL TIME ZONE 'UTC'")
    cursor.execute("""
        CREATE TABLE clubs(id int PRIMARY KEY,name text UNIQUE,address text,city text,state text,
            visible bool DEFAULT true,status text DEFAULT 'active',closed_at timestamptz,total_shows int DEFAULT 0,
            website text DEFAULT '',zip_code text DEFAULT '',phone_number text DEFAULT '',popularity float DEFAULT 0,
            timezone text DEFAULT 'America/New_York');
        CREATE TABLE scraping_sources(id serial PRIMARY KEY,club_id int REFERENCES clubs,
            platform text,scraper_key text,ticketmaster_id text,source_url text,priority int,enabled bool,
            metadata jsonb DEFAULT '{}',updated_at timestamptz DEFAULT now(),UNIQUE(club_id,platform,priority));
        CREATE UNIQUE INDEX ON scraping_sources(ticketmaster_id) WHERE enabled AND platform='ticketmaster';
        CREATE UNIQUE INDEX ON scraping_sources(club_id,priority) WHERE enabled;
        CREATE TABLE shows(id int PRIMARY KEY,club_id int REFERENCES clubs,date timestamptz,room text,
            name text,show_page_url text,last_scraped_by text,UNIQUE(club_id,date,room));
        CREATE TABLE tickets(id serial PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,
            purchase_url text,price numeric,sold_out bool,type text,UNIQUE(show_id,type));
        CREATE TABLE lineup_items(id serial UNIQUE,show_id int REFERENCES shows ON DELETE CASCADE,
            comedian_id text,role text,PRIMARY KEY(show_id,comedian_id));
        CREATE TABLE tagged_shows(id serial UNIQUE,show_id int REFERENCES shows ON DELETE CASCADE,
            tag_id int,PRIMARY KEY(show_id,tag_id));
        CREATE TABLE saved_shows(profile_id text,show_id int REFERENCES shows ON DELETE CASCADE,
            created_at timestamptz,PRIMARY KEY(profile_id,show_id));
        CREATE TABLE sent_notifications(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,
            user_id text,comedian_id text,notification_type text,notification_group_id text,
            UNIQUE(user_id,comedian_id,show_id,notification_type));
        CREATE TABLE ticket_purchase_click_events(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE SET NULL,
            club_id int REFERENCES clubs);
        CREATE TABLE discovery_show_feature_snapshots(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,
            evidence jsonb);
        CREATE TABLE comedians(id text PRIMARY KEY,home_club_id int REFERENCES clubs);
        CREATE TABLE scraper_run_clubs(id int PRIMARY KEY,club_id int REFERENCES clubs);
        CREATE TABLE club_aliases(id serial PRIMARY KEY,club_id int REFERENCES clubs,alias_name text,city text,state text,
            normalized_alias_name text NOT NULL,normalized_city text NOT NULL,normalized_state text NOT NULL,
            source text,verified bool,created_at timestamptz DEFAULT now(),updated_at timestamptz,
            UNIQUE(normalized_alias_name,normalized_city,normalized_state));
        CREATE FUNCTION lt_normalize_alias_key(text) RETURNS text LANGUAGE sql IMMUTABLE AS
            $$ SELECT btrim(regexp_replace(replace(lower($1),'&',' and '),'[^a-z0-9]+',' ','g')) $$;
        CREATE FUNCTION normalize_alias() RETURNS trigger LANGUAGE plpgsql AS $$
          BEGIN NEW.normalized_alias_name=lt_normalize_alias_key(NEW.alias_name);
          NEW.normalized_city=lt_normalize_alias_key(NEW.city); NEW.normalized_state=lower(NEW.state); RETURN NEW; END $$;
        CREATE TRIGGER club_aliases_set_normalized BEFORE INSERT OR UPDATE ON club_aliases
            FOR EACH ROW EXECUTE FUNCTION normalize_alias();
    """)
    for table in repair.ZERO_REFS:
        cursor.execute(f"CREATE TABLE {table}(id int PRIMARY KEY,club_id int REFERENCES clubs)")
    for ident, row in repair.EXPECTED_CLUBS.items():
        cursor.execute(
            "INSERT INTO clubs(id,name,address,city,state) VALUES(%s,%s,%s,%s,%s)",
            (ident, row["name"], row["address"], row["city"], row["state"]),
        )
    for ident, row in repair.EXPECTED_SOURCES.items():
        cols = list(row)
        cursor.execute(
            f"INSERT INTO scraping_sources(id,{','.join(cols)}) VALUES({','.join(['%s']*(len(cols)+1))})",
            (ident, *row.values()),
        )
    for ident, row in repair.EXPECTED_SHOWS.items():
        cols = list(row)
        cursor.execute(
            f"INSERT INTO shows(id,{','.join(cols)}) VALUES({','.join(['%s']*(len(cols)+1))})", (ident, *row.values())
        )
    cursor.execute(
        "INSERT INTO shows VALUES(900001,10023,'2020-01-01','','Historical show','https://example.com/past','live_nation')"
    )
    cursor.execute("INSERT INTO ticket_purchase_click_events VALUES(90,900001,10023),(91,NULL,10023)")
    cursor.execute("INSERT INTO scraper_run_clubs VALUES(1,10023)")
    cursor.execute("INSERT INTO comedians VALUES('home',10023)")
    try:
        yield cursor
    finally:
        conn.rollback()
        conn.close()


def payload(cur, before, after):
    return {
        "task_id": 4049,
        "show_map": {str(k): v for k, v in repair.SHOW_MAP.items()},
        "show_moves": {str(k): v for k, v in repair.SHOW_MOVES.items()},
        "folds": {str(k): v for k, v in repair.FOLDS.items()},
        "schema": repair.schema(cur),
        "before": before,
        "after": after,
    }


def test_repair_preserves_children_history_and_exact_restore(cur):
    old, new = next(iter(repair.SHOW_MAP.items()))
    oldclub = repair.EXPECTED_SHOWS[old]["club_id"]
    newclub = repair.EXPECTED_SHOWS[new]["club_id"]
    cur.execute(
        "INSERT INTO saved_shows VALUES(%s,%s,%s),(%s,%s,%s)",
        ("profile", old, "2026-01-01", "profile", new, "2026-02-01"),
    )
    cur.execute("INSERT INTO sent_notifications VALUES(1,%s,'user','comedian','push','group')", (old,))
    cur.execute("INSERT INTO ticket_purchase_click_events VALUES(1,%s,%s)", (old, oldclub))
    cur.execute("INSERT INTO discovery_show_feature_snapshots VALUES(1,%s,'{\"old\":true}')", (old,))
    cur.execute(
        "INSERT INTO tickets(show_id,price,sold_out,type) VALUES(%s,50,false,'General'),(%s,60,false,'General')",
        (old, new),
    )
    cur.execute(
        "INSERT INTO lineup_items(show_id,comedian_id,role) VALUES(%s,'performer','headliner'),(%s,'performer','host')",
        (old, new),
    )
    cur.execute("INSERT INTO tagged_shows(show_id,tag_id) VALUES(%s,1)", (old,))
    repair.lock_and_validate_schema(cur)
    before = repair.snapshot(cur)
    repair.validate(cur, before)
    repair.repair(cur, before)
    after = repair.snapshot(cur)
    repair.validate(cur, after)
    assert len(before["shows"]) - len(after["shows"]) == 58
    assert after["saved_shows"][0]["show_id"] == new
    assert after["saved_shows"][0]["created_at"].startswith("2026-01-01")
    assert after["sent_notifications"][0]["show_id"] == new
    assert next(r for r in after["ticket_purchase_click_events"] if r["id"] == 1) == {
        "id": 1,
        "show_id": new,
        "club_id": newclub,
    }
    assert [r for r in after["ticket_purchase_click_events"] if r["id"] in {90, 91}] == [
        r for r in before["ticket_purchase_click_events"] if r["id"] in {90, 91}
    ]
    assert after["scraper_run_clubs"] == before["scraper_run_clubs"]
    assert after["comedians"][0]["home_club_id"] == 12796
    assert len(after["club_aliases"]) == 3
    assert after["discovery_show_feature_snapshots"] == []
    assert after["tickets"][0]["price"] == 60
    assert after["lineup_items"][0]["role"] == "host"
    assert next(r for r in before["tickets"] if r["show_id"] == old)["price"] == 50
    repair.repair(cur, after)
    assert repair.snapshot(cur) == after
    backup = payload(cur, before, after)
    repair.restore(cur, backup)
    assert repair.snapshot(cur) == before
    repair.restore(cur, backup)


def test_folded_ticketmaster_ids_route_to_canonical_twice(cur):
    from sql.club_queries import ClubQueries

    before = repair.snapshot(cur)
    repair.validate(cur, before)
    repair.repair(cur, before)
    after = repair.snapshot(cur)
    for _ in range(2):
        for source in repair.EXPECTED_SOURCES.values():
            old = source["club_id"]
            new = repair.FOLDS.get(old, old)
            if old not in set(repair.FOLDS) | set(repair.FOLDS.values()):
                continue
            venue = repair.EXPECTED_CLUBS[old]
            cur.execute(
                ClubQueries.UPSERT_CLUB_BY_TICKETMASTER_VENUE,
                (
                    source["ticketmaster_id"],
                    venue["name"],
                    venue["address"],
                    "",
                    venue["city"],
                    venue["state"],
                    "America/New_York",
                ),
            )
            columns = [d.name for d in cur.description]
            row = dict(zip(columns, cur.fetchone()))
            assert row["id"] == new
    assert repair.snapshot(cur) == after


@pytest.mark.parametrize("table", sorted(repair.ZERO_REFS))
def test_unreviewed_club_reference_refuses_repair(cur, table):
    cur.execute(f"INSERT INTO {table} VALUES(1,10023)")
    with pytest.raises(ValueError, match="Unreviewed"):
        repair.validate(cur, repair.snapshot(cur))


def test_new_foreign_key_requires_review(cur):
    cur.execute("CREATE TABLE unreviewed_child(id int PRIMARY KEY,club_id int REFERENCES clubs)")
    with pytest.raises(ValueError, match="foreign keys changed"):
        repair.lock_and_validate_schema(cur)


def test_source_drift_and_alias_conflict_refuse_repair(cur):
    cur.execute("UPDATE scraping_sources SET ticketmaster_id='changed' WHERE id=6780")
    with pytest.raises(ValueError, match="Source"):
        repair.validate(cur, repair.snapshot(cur))
    cur.execute(
        "UPDATE scraping_sources SET ticketmaster_id=%s WHERE id=6780",
        (repair.EXPECTED_SOURCES[6780]["ticketmaster_id"],),
    )
    cur.execute(
        "INSERT INTO club_aliases(club_id,alias_name,city,state,source,verified) VALUES(575,'Van Wezel','Sarasota','FL','other',true)"
    )
    with pytest.raises(ValueError, match="alias"):
        repair.validate(cur, repair.snapshot(cur))


def test_restore_refuses_new_user_activity(cur):
    before = repair.snapshot(cur)
    repair.repair(cur, before)
    after = repair.snapshot(cur)
    cur.execute("INSERT INTO favorite_clubs VALUES(1,12796)")
    with pytest.raises(ValueError, match="changed after repair"):
        repair.restore(cur, payload(cur, before, after))


def test_failed_merge_rolls_back_all_rows(cur):
    old, new = next(iter(repair.SHOW_MAP.items()))
    cur.execute(
        "INSERT INTO sent_notifications VALUES(1,%s,'user','comedian','push','a'),(2,%s,'user','comedian','push','b')",
        (old, new),
    )
    before = repair.snapshot(cur)
    cur.execute("SAVEPOINT trial")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        repair.repair(cur, before)
    cur.execute("ROLLBACK TO SAVEPOINT trial")
    assert repair.snapshot(cur) == before


def test_backup_is_private_exclusive_and_fsynced(tmp_path, monkeypatch):
    calls = []
    real_fsync = os.fsync

    def synced(fd):
        calls.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", synced)
    path = tmp_path / "recovery.json"
    repair.save_backup(path, {"before": "original"})
    assert path.stat().st_mode & 0o777 == 0o600
    assert len(calls) == 2
    with pytest.raises(FileExistsError):
        repair.save_backup(path, {"before": "lost"})
    assert json.loads(path.read_text()) == {"before": "original"}


def test_new_fk_column_on_existing_table_requires_review(cur):
    cur.execute("ALTER TABLE tickets ADD COLUMN alternate_show_id int REFERENCES shows")
    with pytest.raises(ValueError, match="foreign keys changed"):
        repair.lock_and_validate_schema(cur)


def test_restore_refuses_changed_unique_constraint(cur):
    before = repair.snapshot(cur)
    repair.repair(cur, before)
    after = repair.snapshot(cur)
    backup = payload(cur, before, after)
    cur.execute("ALTER TABLE shows ADD CONSTRAINT new_identity UNIQUE(show_page_url,club_id,date,room)")
    with pytest.raises(ValueError, match="Schema changed"):
        repair.restore(cur, backup)
