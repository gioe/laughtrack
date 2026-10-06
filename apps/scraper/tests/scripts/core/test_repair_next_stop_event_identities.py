"""Offline plan guards; optional rollback-only real PostgreSQL repair rehearsal."""

import copy
import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
from psycopg2 import sql
import pytest

SCRAPER = Path(__file__).parents[3]
SPEC = importlib.util.spec_from_file_location(
    "next_stop_identity_repair", SCRAPER / "scripts/archive/repair_next_stop_event_identities_2026_10_06.py"
)
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)
NATIVE = "1df52ed6-a1f9-4f4f-9002-87a6eff110cf"
OLD_URL = "https://www.nextstopcomedy.com/events/brewery-old"
NEW_URL = "https://www.nextstopcomedy.com/events/brewery-new"


def plan_from(state):
    tickets = {r["id"]: r for r in state["tickets"]}
    return dict(
        task_id=4121,
        captured_at="2026-10-06T00:00:00+00:00",
        snapshot_floor="2026-09-29T00:00:00+00:00",
        organizer_id=35,
        expected_organizer=state["production_companies"][0],
        cohort_club_ids=[1],
        expected_clubs={str(r["id"]): r for r in state["clubs"]},
        expected_shows={str(r["id"]): r for r in state["shows"]},
        expected_children={t: state[t] for t in repair.CHILDREN},
        reviewed_event_urls={OLD_URL: NATIVE, NEW_URL: NATIVE},
        groups=[
            dict(
                native_id=NATIVE,
                canonical_id=1,
                duplicate_ids=[2],
                target_date="2027-01-01T01:00:00+00:00",
                target_url=NEW_URL,
                allow_historical=False,
                reason="Reviewed current native event",
                ticket_coalescences=[
                    dict(
                        from_id=20,
                        to_id=10,
                        before_from=tickets[20],
                        before_to=tickets[10],
                        reason="Same reviewed GA offer",
                    )
                ],
                proposed_ticket_updates=[
                    dict(
                        id=10,
                        before=tickets[10],
                        patch=dict(price=47, purchase_url=NEW_URL),
                        reason="Current native GA offer",
                    )
                ],
            )
        ],
    )


@pytest.fixture
def state():
    def show(ident, date, url):
        return dict(
            id=ident,
            club_id=1,
            date=date,
            room="",
            name="Comedy",
            show_page_url=url,
            source_performance_id=None,
            production_company_id=35,
            last_scraped_by="next_stop_comedy",
            min_price=52 if ident == 1 else 47,
            tickets_sold_out=False,
        )

    return {
        "clubs": [dict(id=1, name="Brewery", timezone="America/Edmonton")],
        "production_companies": [dict(id=35, name="Next Stop Comedy", slug="next-stop-comedy")],
        "shows": [
            show(1, "2027-01-01T02:00:00+00:00", OLD_URL),
            show(2, "2027-01-01T01:00:00+00:00", NEW_URL),
            show(3, "2026-10-01T01:00:00+00:00", "https://other/held"),
        ],
        "tickets": [
            dict(id=10, show_id=1, type="General Admission", price=52, purchase_url=OLD_URL, sold_out=False),
            dict(id=20, show_id=2, type="General Admission", price=47, purchase_url=NEW_URL, sold_out=False),
            dict(id=30, show_id=3, type="GA", price=47, purchase_url="https://other/held", sold_out=False),
        ],
        "lineup_items": [
            dict(id=1, show_id=1, comedian_id="comic", role="host"),
            dict(id=2, show_id=2, comedian_id="comic", role="host"),
        ],
        "tagged_shows": [dict(show_id=1, tag_id=7), dict(show_id=2, tag_id=7)],
        "saved_shows": [
            dict(show_id=1, profile_id="user", note="keep"),
            dict(show_id=2, profile_id="user", note="keep"),
            dict(show_id=2, profile_id="other", note="private"),
        ],
        "sent_notifications": [dict(id=1, show_id=1, user_id="user"), dict(id=2, show_id=2, user_id="user")],
        "discovery_show_feature_snapshots": [
            dict(
                id=1,
                show_id=2,
                feature_version="v1",
                as_of="2026-10-01T00:00:00+00:00",
                evidence={"score": 3},
            )
        ],
        "ticket_purchase_click_events": [dict(id=1, show_id=1, club_id=1), dict(id=2, show_id=2, club_id=1)],
        repair.AUDIT: [],
    }


def test_offline_plan_preserves_ids_current_offer_and_public_history(state):
    plan = plan_from(state)
    repair.validate_plan(plan)
    repair.validate_before(state, plan)
    after, archives = repair.planned_state(state, plan)
    assert {r["id"] for r in after["shows"]} == {1, 3}
    ticket = next(r for r in after["tickets"] if r["id"] == 10)
    assert (ticket["price"], ticket["purchase_url"]) == (47, NEW_URL)
    assert {(kind, ident) for kind, ident, *_ in archives} == {
        ("show", 1),
        ("show", 2),
        ("ticket", 10),
        ("ticket", 20),
    }
    assert next(a[2] for a in archives if a[:2] == ("ticket", 10))["price"] == 52
    assert after["ticket_purchase_click_events"] == [
        dict(id=1, show_id=1, club_id=1),
        dict(id=2, show_id=1, club_id=1),
    ]
    assert next(r for r in after["shows"] if r["id"] == 3) == state["shows"][2]


@pytest.mark.parametrize("change", ["uuid", "alias", "history", "venue", "child", "price_guard"])
def test_offline_unreviewed_changes_fail(state, change):
    plan = plan_from(copy.deepcopy(state))
    group = plan["groups"][0]
    if change == "uuid":
        group["native_id"] = "not-a-uuid"
    if change == "alias":
        plan["reviewed_event_urls"].pop(OLD_URL)
    if change == "history":
        plan["expected_shows"]["1"]["date"] = "2026-10-01T00:00:00Z"
    if change == "venue":
        plan["expected_shows"]["2"]["club_id"] = 2
    if change == "child":
        plan["expected_children"].pop("saved_shows")
    if change == "price_guard":
        group["ticket_coalescences"][0]["before_from"] = dict(
            group["ticket_coalescences"][0]["before_from"], price=1
        )
    with pytest.raises(ValueError):
        repair.validate_plan(plan)
        repair.planned_state(state, plan)


def test_offline_conflicting_private_relationship_refuses(state):
    state["saved_shows"][1]["note"] = "different private data"
    with pytest.raises(ValueError, match="saved_shows"):
        repair.planned_state(state, plan_from(state))


def test_historical_correction_requires_explicit_approval_and_archives_old_date(state):
    state["shows"][0]["date"] = "2026-10-01T01:00:00+00:00"
    plan = plan_from(state)
    plan["groups"][0]["allow_historical"] = True
    repair.validate_plan(plan)
    after, archives = repair.planned_state(state, plan)
    assert next(a[2] for a in archives if a[:2] == ("show", 1))["date"] == state["shows"][0]["date"]
    assert next(r for r in after["shows"] if r["id"] == 1)["date"] == plan["groups"][0]["target_date"]


@pytest.fixture
def db(state):
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Set TEST_DATABASE_URL for isolated rollback-only PostgreSQL tests")
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    schema = "next_stop_" + uuid4().hex
    cur.execute(
        sql.SQL("CREATE SCHEMA {}; SET LOCAL search_path TO {}; SET LOCAL TIME ZONE 'UTC'").format(
            sql.Identifier(schema), sql.Identifier(schema)
        )
    )
    cur.execute("""
    CREATE TABLE clubs(id int PRIMARY KEY,name text,timezone text);
    CREATE TABLE production_companies(id int PRIMARY KEY,name text,slug text);
    CREATE TABLE shows(id int PRIMARY KEY,club_id int,date timestamptz,room text,name text,show_page_url text,source_performance_id text,production_company_id int,last_scraped_by text,min_price numeric,tickets_sold_out bool);
    CREATE UNIQUE INDEX show_native ON shows(club_id,source_performance_id) WHERE source_performance_id IS NOT NULL;
    CREATE UNIQUE INDEX show_slot ON shows(club_id,date,room) WHERE source_performance_id IS NULL;
    CREATE TABLE tickets(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,type text,price numeric,purchase_url text,sold_out bool,UNIQUE(show_id,type));
    CREATE TABLE lineup_items(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,comedian_id text,role text,UNIQUE(show_id,comedian_id));
    CREATE TABLE tagged_shows(show_id int REFERENCES shows ON DELETE CASCADE,tag_id int,PRIMARY KEY(show_id,tag_id));
    CREATE TABLE saved_shows(show_id int REFERENCES shows ON DELETE CASCADE,profile_id text,note text,PRIMARY KEY(show_id,profile_id));
    CREATE TABLE sent_notifications(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,user_id text);
    CREATE TABLE discovery_show_feature_snapshots(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE CASCADE,feature_version text,as_of timestamptz,evidence jsonb);
    CREATE TABLE ticket_purchase_click_events(id int PRIMARY KEY,show_id int REFERENCES shows ON DELETE SET NULL,club_id int);
    CREATE TABLE admin_action_audits(id serial PRIMARY KEY,actor_profile_id text,action text,entity_type text,entity_id text,reason text,before_json jsonb,after_json jsonb,created_at timestamptz DEFAULT now());
    """)
    migrations = SCRAPER.parent / "web/prisma/migrations"
    for migration in (
        "20260512010000_add_show_min_price_with_trigger",
        "20260703172048_add_show_tickets_sold_out",
    ):
        cur.execute((migrations / migration / "migration.sql").read_text())
    for table in repair.TABLES:
        for row in state[table]:
            cur.execute(
                sql.SQL("INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{},%s::jsonb)").format(
                    sql.Identifier(table), sql.Identifier(table)
                ),
                (json.dumps(row),),
            )
    plan = plan_from(state)
    captured = repair.snapshot(cur, plan)
    plan = plan_from(captured)
    try:
        yield cur, plan
    finally:
        conn.rollback()
        conn.close()


def test_postgres_apply_archive_restore_reapply(db, tmp_path):
    cur, plan = db
    path = tmp_path / "private.json"
    result = repair.repair(cur, plan, path)
    assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(Path(str(path) + ".after.json").read_text()) == result
    assert repair.repair(cur, plan)["already_applied"]
    assert len(result["after"][repair.AUDIT]) == 4
    assert len(result["after"]["ticket_purchase_click_events"]) == 2
    assert next(r for r in result["after"]["shows"] if r["id"] == 1)["min_price"] == 47
    repair.restore(cur, plan, result)
    assert repair.snapshot(cur, plan) == result["before"]
    repair.restore(cur, plan, result)
    again = repair.repair(cur, plan)
    # Audit sequence IDs may advance across rollback/reapply; business rows do not.
    for table in repair.previous.TABLES:
        assert again["after"][table] == result["after"][table]


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE shows SET name='drift' WHERE id=3",
        "UPDATE tickets SET price=99 WHERE id=10",
        "INSERT INTO saved_shows VALUES(2,'new-user','private')",
        "UPDATE production_companies SET name='drift'",
    ],
)
def test_postgres_before_drift_refuses_all_writes(db, query):
    cur, plan = db
    cur.execute(query)
    before = repair.snapshot(cur, plan)
    with pytest.raises(ValueError):
        repair.repair(cur, plan)
    assert repair.snapshot(cur, plan) == before


def test_postgres_unknown_fk_refuses(db):
    cur, plan = db
    cur.execute("CREATE TABLE new_child(id int PRIMARY KEY,show_id int REFERENCES shows)")
    with pytest.raises(ValueError, match="foreign keys"):
        repair.repair(cur, plan)


def test_postgres_restore_refuses_changed_private_references(db):
    cur, plan = db
    recovery = repair.repair(cur, plan)
    cur.execute("UPDATE ticket_purchase_click_events SET club_id=2 WHERE id=2")
    with pytest.raises(ValueError, match="Affected state changed"):
        repair.restore(cur, plan, recovery)


def test_postgres_dry_run_rolls_back(db):
    cur, plan = db
    before = repair.snapshot(cur, plan)
    cur.execute("SAVEPOINT rehearsal")
    repair.repair(cur, plan)
    cur.execute("ROLLBACK TO SAVEPOINT rehearsal")
    assert repair.snapshot(cur, plan) == before


def test_postgres_large_click_cohort_uses_bounded_round_trips(db):
    cur, plan = db
    cur.execute("INSERT INTO ticket_purchase_click_events SELECT n,2,1 FROM generate_series(100,1100) n")
    plan = plan_from(repair.snapshot(cur, plan))

    class CountingCursor:
        statements = 0

        def execute(self, *args, **kwargs):
            self.statements += 1
            return cur.execute(*args, **kwargs)

        def __getattr__(self, name):
            return getattr(cur, name)

    counted = CountingCursor()
    result = repair.repair(counted, plan)
    assert counted.statements < 70
    assert len(result["after"]["ticket_purchase_click_events"]) == 1003
    counted.statements = 0
    repair.restore(counted, plan, result)
    assert counted.statements < 65
    assert repair.snapshot(cur, plan) == result["before"]
