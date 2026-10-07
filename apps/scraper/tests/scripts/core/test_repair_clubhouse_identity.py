"""Run the actual venue migration and guarded reassignment in isolated PostgreSQL."""

import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
from psycopg2 import sql
import pytest

from scripts.core import repair_clubhouse_identity as repair

MIGRATIONS = Path(__file__).resolve().parents[4] / "web/prisma/migrations"
MIGRATION = (MIGRATIONS / "20261007014000_add_clubhouse_new_hyde_park/migration.sql").read_text()


@pytest.fixture
def db():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL required for isolated PostgreSQL verification")
    connection = psycopg2.connect(dsn)
    cur = connection.cursor()
    schema = "clubhouse_" + uuid4().hex
    cur.execute(
        sql.SQL("CREATE SCHEMA {}; SET LOCAL search_path TO {}; SET LOCAL TIME ZONE 'UTC'").format(
            sql.Identifier(schema), sql.Identifier(schema)
        )
    )
    cur.execute("""
    CREATE TABLE clubs(id serial PRIMARY KEY,name text UNIQUE NOT NULL,address text,website text,
        city text,state text,zip_code varchar,country text,timezone text,club_type text,
        visible bool,status text,total_shows int DEFAULT 0,description text);
    CREATE TABLE shows(id int PRIMARY KEY,club_id int REFERENCES clubs,date timestamptz,
        room text,name text,show_page_url text,last_scraped_by text,production_company_id int,
        source_performance_id text,description text,scraped_by_organizer_id int,is_cancelled bool DEFAULT false);
    CREATE UNIQUE INDEX show_slot ON shows(club_id,date,room) WHERE source_performance_id IS NULL;
    CREATE TABLE tickets(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,
        type text,price numeric,purchase_url text,sold_out bool);
    """)
    for table in repair.CHILDREN[1:]:
        delete = "SET NULL" if table == "ticket_purchase_click_events" else "CASCADE"
        cur.execute(
            sql.SQL(
                "CREATE TABLE {} (id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE "
                + delete
                + ",club_id int REFERENCES clubs,private_payload jsonb NOT NULL)"
            ).format(sql.Identifier(table))
        )
    alias_ddl = (
        (MIGRATIONS / "20260513144500_add_club_aliases/migration.sql")
        .read_text()
        .split("INSERT INTO club_aliases", 1)[0]
    )
    cur.execute(alias_ddl)
    cur.execute((MIGRATIONS / "20260625140000_club_aliases_normalize_trigger/migration.sql").read_text())
    source = dict(
        repair.SOURCE, id=repair.SOURCE_ID, total_shows=1, description="LA metadata survives", status="active"
    )
    cur.execute(
        sql.SQL("INSERT INTO clubs ({}) VALUES ({})").format(
            sql.SQL(",").join(map(sql.Identifier, source)), sql.SQL(",").join(sql.Placeholder() for _ in source)
        ),
        list(source.values()),
    )
    cur.execute(
        "INSERT INTO clubs(id,name,address,city,state) VALUES(999,'Other Clubhouse','Elsewhere','Elsewhere','TX')"
    )
    cur.execute(
        "INSERT INTO shows(id,club_id,date,room,name,show_page_url,last_scraped_by,production_company_id,source_performance_id,description) VALUES(%s,%s,%s,'','The Clubhouse',%s,'next_stop_comedy',35,NULL,'preserve me')",
        (repair.SHOW_ID, repair.SOURCE_ID, repair.SHOW["date"], repair.URL),
    )
    cur.execute("UPDATE shows SET scraped_by_organizer_id=35 WHERE id=7123739")
    cur.execute(
        "INSERT INTO shows VALUES(999,999,'2026-10-26T00:00Z','','Unrelated','https://unrelated','other',NULL,NULL,'keep',NULL,false)"
    )
    cur.execute("INSERT INTO tickets VALUES(8110440,%s,'General Admission',27,%s,false)", (repair.SHOW_ID, repair.URL))
    for table in repair.CHILDREN[1:]:
        cur.execute(
            sql.SQL("INSERT INTO {} VALUES(1,%s,%s,%s::jsonb),(999,999,999,%s::jsonb)").format(sql.Identifier(table)),
            (repair.SHOW_ID, repair.SOURCE_ID, json.dumps({"private": table}), json.dumps({"untouched": table})),
        )
    cur.execute(MIGRATION)
    target = repair.lock_and_resolve(cur)
    try:
        yield cur, target
    finally:
        connection.rollback()
        connection.close()


def test_real_migration_twice_repair_twice_restore_twice_preserves_all_references(db, tmp_path):
    cur, target = db
    before = repair.snapshot(cur, target)
    cur.execute(MIGRATION)
    assert repair.snapshot(cur, target) == before
    backup_path = tmp_path / "private.json"
    payload = repair.repair(cur, backup_path)
    assert payload["before"] == before
    assert payload["after"]["clubs"] == before["clubs"]
    assert payload["after"]["club_aliases"] == before["club_aliases"]
    for table in repair.CHILDREN:
        assert payload["after"][table] == before[table]
    show = payload["after"]["shows"][0]
    assert (show["id"], show["club_id"], show["date"]) == (repair.SHOW_ID, target, repair.SHOW["date"])
    assert repair.repair(cur)["before"] == repair.repair(cur)["after"] == payload["after"]
    cur.execute("SELECT club_id,description FROM shows WHERE id=999")
    assert cur.fetchone() == (999, "keep")
    assert backup_path.stat().st_mode & 0o777 == 0o600
    assert json.loads(backup_path.read_text()) == payload
    assert json.loads(Path(str(backup_path) + ".after.json").read_text()) == payload
    repair.restore(cur, payload)
    assert repair.snapshot(cur, target) == before
    repair.restore(cur, payload)


def test_existing_location_alias_query_routes_next_stop_to_new_york(db):
    from sql.club_queries import ClubQueries

    cur, target = db
    cur.execute(ClubQueries.GET_CLUBS_BY_LOCATION, ("The Clubhouse", "New Hyde Park", "NY", "New Hyde Park", "NY"))
    columns = [d.name for d in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    assert len(rows) == 1
    assert rows[0]["id"] == target
    assert rows[0]["alias_matches_candidate"] is True


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE clubs SET address='Changed' WHERE id=8828",
        "UPDATE clubs SET address='Changed' WHERE name='The Clubhouse (New Hyde Park)'",
        "UPDATE clubs SET visible=false WHERE name='The Clubhouse (New Hyde Park)'",
        "UPDATE club_aliases SET verified=false",
        "UPDATE club_aliases SET source='Other evidence'",
        "UPDATE shows SET show_page_url='https://wrong' WHERE id=7123739",
        "UPDATE shows SET date=date+interval '1 hour' WHERE id=7123739",
        "UPDATE shows SET club_id=999 WHERE id=7123739",
        "UPDATE shows SET scraped_by_organizer_id=99 WHERE id=7123739",
        "UPDATE shows SET is_cancelled=true WHERE id=7123739",
        "UPDATE shows SET show_page_url='https://www.nextstopcomedy.com/events/the-clubhouse-2026-10-24-8-pm' WHERE id=999",
        "UPDATE tickets SET price=28 WHERE id=8110440",
        "DELETE FROM tickets WHERE id=8110440",
        "CREATE TABLE unknown_reference(show_id int REFERENCES shows)",
    ],
)
def test_changed_evidence_refuses_without_mutation(db, mutation):
    cur, target = db
    cur.execute(mutation)
    before = repair.snapshot(cur, target)
    with pytest.raises(ValueError):
        repair.repair(cur)
    assert repair.snapshot(cur, target) == before


def test_target_slot_collision_refuses(db):
    cur, target = db
    cur.execute(
        "INSERT INTO shows(id,club_id,date,room,show_page_url) VALUES(17,%s,%s,'','https://other')",
        (target, repair.SHOW["date"]),
    )
    before = repair.snapshot(cur, target)
    with pytest.raises(ValueError, match="collision"):
        repair.repair(cur)
    assert repair.snapshot(cur, target) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE clubs SET description='Changed LA metadata' WHERE id=8828",
        "UPDATE saved_shows SET private_payload='{}' WHERE id=1",
        "UPDATE ticket_purchase_click_events SET club_id=999 WHERE id=1",
    ],
)
def test_restore_refuses_intervening_private_or_venue_changes(db, mutation):
    cur, target = db
    backup = repair.repair(cur)
    cur.execute(mutation)
    before = repair.snapshot(cur, target)
    with pytest.raises(ValueError, match="Affected state changed"):
        repair.restore(cur, backup)
    assert repair.snapshot(cur, target) == before


def test_dry_run_and_failed_backup_leave_original_state(db, tmp_path):
    cur, target = db
    before = repair.snapshot(cur, target)
    cur.execute("SAVEPOINT rehearsal")
    repair.repair(cur)
    cur.execute("ROLLBACK TO SAVEPOINT rehearsal")
    assert repair.snapshot(cur, target) == before
    occupied = tmp_path / "existing.json"
    occupied.write_text("preserve")
    with pytest.raises(FileExistsError):
        repair.repair(cur, occupied)
    assert repair.snapshot(cur, target) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE clubs SET zip_code='99999' WHERE name='The Clubhouse (New Hyde Park)'",
        "UPDATE club_aliases SET club_id=999",
    ],
)
def test_real_migration_rejects_changed_target_or_competing_alias(db, mutation):
    cur, target = db
    cur.execute(mutation)
    before = repair.snapshot(cur, target)
    cur.execute("SAVEPOINT rejected")
    with pytest.raises(psycopg2.Error):
        cur.execute(MIGRATION)
    cur.execute("ROLLBACK TO SAVEPOINT rejected")
    assert repair.snapshot(cur, target) == before
