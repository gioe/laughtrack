"""Real PostgreSQL preservation and rollback coverage for TASK-4136."""

import copy
import importlib.util
import json
import re
import stat
from pathlib import Path

import pytest

from scripts.archive import merge_annoyance_historical_pairs_2026_10_08 as repair

_spec = importlib.util.spec_from_file_location(
    "annoyance_pair_schema", Path(__file__).parents[1] / "test_repair_seatengine_organizer_venues.py"
)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
database = _schema.database


@pytest.fixture
def populated(database):
    with database.cursor() as cur:
        for table in repair.CHILDREN:
            cur.execute(f"DELETE FROM {table}")
        cur.execute("""DELETE FROM shows; DELETE FROM clubs; DELETE FROM scraping_sources;
            ALTER TABLE shows ADD COLUMN source_performance_id text;
            ALTER TABLE ticket_purchase_click_events ADD COLUMN payload jsonb;
            INSERT INTO clubs(id,name,total_shows) VALUES(183,'The Annoyance',123);
            INSERT INTO scraping_sources VALUES(183,183,true,'{"source_performance_identity":true}',
                'https://theannoyance.thundertix.com');""")
        for pair, fill in zip(repair.PAIRS, repair.TICKET_FILLS):
            old, new, event, performance, date = pair
            for ident, when in ((old, "2026-05-01T13:00:00Z"), (new, date)):
                cur.execute(
                    "INSERT INTO shows(id,club_id,date,show_page_url) VALUES(%s,183,%s,%s)",
                    (ident, when, f"https://theannoyance.thundertix.com/events/{event}"),
                )
            url = f"https://theannoyance.thundertix.com/orders/new?event_id={event}&performance_id={performance}"
            cur.execute(
                """INSERT INTO tickets(id,show_id,type,price,purchase_url)
                VALUES(%s,%s,'General Admission',%s,%s),(%s,%s,'General Admission',NULL,%s)""",
                (fill["from_id"], old, fill["price"], url, fill["to_id"], new, url),
            )
            cur.execute("INSERT INTO tagged_shows VALUES(%s,1),(%s,1),(%s,2)", (old, new, old))
        for ident in repair.HELD_IDS:
            cur.execute(
                """INSERT INTO shows(id,club_id,date,show_page_url,description)
                VALUES(%s,183,'2026-05-10T20:00Z','https://theannoyance.thundertix.com/events/263406','held')""",
                (ident,),
            )
            cur.execute(
                "INSERT INTO tickets(id,show_id,type,price,purchase_url) VALUES(%s,%s,'GA',0,'held')", (ident, ident)
            )
            cur.execute("INSERT INTO tagged_shows VALUES(%s,9)", (ident,))
        old, new = repair.PAIRS[0][:2]
        cur.execute(
            "INSERT INTO lineup_items VALUES(1,%s,'comic','host'),(2,%s,'comic','host'),(3,%s,'other','guest')",
            (old, new, old),
        )
        cur.execute("INSERT INTO saved_shows VALUES(%s,'user','2026-01-01T00:00Z')", (old,))
        cur.execute("INSERT INTO sent_notifications VALUES(1,%s),(2,%s)", (old, new))
        cur.execute("INSERT INTO discovery_show_feature_snapshots VALUES(1,%s,'v1','2026-01-01T00:00Z')", (old,))
        for i in range(27):
            cur.execute(
                "INSERT INTO ticket_purchase_click_events VALUES(%s,%s,%s::jsonb)",
                (i, old if i < 26 else new, json.dumps(dict(session=f"private-{i}", campaign="retained", price=i))),
            )
        # Exercise the actual production trigger SQL, with function definitions
        # and calls isolated in pg_temp alongside this fixture's temporary tables.
        migrations = Path(__file__).resolve().parents[4] / "web/prisma/migrations"
        functions = (
            "refresh_show_min_price",
            "tickets_trickle_show_min_price",
            "tickets_refresh_all_show_min_prices",
            "refresh_show_tickets_sold_out",
            "tickets_trickle_show_tickets_sold_out",
            "tickets_refresh_all_show_tickets_sold_out",
        )
        for migration in (
            "20260512010000_add_show_min_price_with_trigger",
            "20260703172048_add_show_tickets_sold_out",
        ):
            source = (migrations / migration / "migration.sql").read_text()
            for name in functions:
                source = re.sub(r"\b" + name + r"(?=\s*\()", "pg_temp." + name, source)
            cur.execute(source)
    return database


@pytest.fixture
def plan(populated):
    with populated.cursor() as cur:
        return repair.build_plan(cur)


def test_preservation_27_clicks_coalescence_idempotence_and_json_recovery(populated, plan, tmp_path):
    path = tmp_path / "private.json"
    with populated.cursor() as cur:
        result = repair.repair(cur, plan, path)
        before, after = result["before"], result["after"]
        assert len(before["shows"]) == 6 and len(after["shows"]) == 4
        assert len(before["tickets"]) == 6 and len(after["tickets"]) == 4
        assert len(before["tagged_shows"]) == 8 and len(after["tagged_shows"]) == 6
        assert len(after["lineup_items"]) == 2
        assert before["clubs"] == after["clubs"] and before["scraping_sources"] == after["scraping_sources"]
        remaining = {r["id"]: r for r in before["shows"] if r["id"] not in {p[0] for p in repair.PAIRS}}
        remaining[7451272] = dict(remaining[7451272], min_price=15.0)
        assert {r["id"]: r for r in after["shows"]} == remaining
        for table in repair.CHILDREN:
            assert [r for r in before[table] if r["show_id"] in repair.HELD_IDS] == [
                r for r in after[table] if r["show_id"] in repair.HELD_IDS
            ]
        for table in (
            "saved_shows",
            "sent_notifications",
            "discovery_show_feature_snapshots",
            "ticket_purchase_click_events",
        ):
            assert after[table] == repair.ordered(dict(r, show_id=7451272) for r in before[table])
        assert len(after["ticket_purchase_click_events"]) == 27
        for fill in repair.TICKET_FILLS:
            assert next(r for r in after["tickets"] if r["id"] == fill["to_id"])["price"] == fill["price"]
        assert repair.repair(cur, plan)["already_applied"]
        saved = json.loads(Path(str(path) + ".after.json").read_text())
        assert repair.restore(cur, plan, saved)
        assert repair.snapshot(cur) == before
        assert not repair.restore(cur, plan, saved)
        assert not repair.repair(cur, plan)["already_applied"]
    assert "after" not in json.loads(path.read_text())
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(Path(str(path) + ".after.json").stat().st_mode) == 0o600


@pytest.mark.parametrize("case", ["show", "hold", "ticket", "click", "source", "venue"])
def test_exact_row_drift_refused(populated, plan, case):
    changes = {
        "show": "UPDATE shows SET description='changed' WHERE id=7451272",
        "hold": "UPDATE shows SET description='changed' WHERE id=927780",
        "ticket": "UPDATE tickets SET price=16 WHERE id=4225195",
        "click": "UPDATE ticket_purchase_click_events SET payload='{}' WHERE id=0",
        "source": "UPDATE scraping_sources SET enabled=false",
        "venue": "UPDATE clubs SET total_shows=99",
    }
    with populated.cursor() as cur:
        cur.execute(changes[case])
        before = repair.snapshot(cur)
        with pytest.raises(ValueError, match="before-image"):
            repair.repair(cur, plan)
        assert repair.snapshot(cur) == before


@pytest.mark.parametrize("case", ["column", "index", "show_fk", "child_fk", "trigger", "helper"])
def test_schema_drift_refused_before_apply(populated, plan, case):
    changes = {
        "column": "ALTER TABLE shows ADD COLUMN new_column text",
        "index": "CREATE INDEX new_index ON tickets(price)",
        "show_fk": "CREATE TEMP TABLE new_reference(show_id int REFERENCES shows)",
        "child_fk": "CREATE TEMP TABLE new_reference(ticket_id int REFERENCES tickets)",
        "trigger": "ALTER TABLE tickets DISABLE TRIGGER tickets_trickle_show_min_price_upd",
        "helper": "CREATE OR REPLACE FUNCTION pg_temp.refresh_show_min_price(p_show_id INTEGER) RETURNS VOID AS $$ BEGIN RETURN; END; $$ LANGUAGE plpgsql",
    }
    with populated.cursor() as cur:
        cur.execute(changes[case])
        with pytest.raises(ValueError, match="Schema|foreign keys|inbound"):
            repair.repair(cur, plan)


@pytest.mark.parametrize("case", ["price", "sold_out", "url", "date", "user", "lineup", "snapshot"])
def test_native_or_relationship_conflicts_refused_at_planning(populated, case):
    changes = {
        "price": "UPDATE tickets SET price=17 WHERE id=8491061",
        "sold_out": "UPDATE tickets SET sold_out=true WHERE id=8491061",
        "url": "UPDATE tickets SET purchase_url='https://theannoyance.thundertix.com/orders/new?event_id=188918&performance_id=999' WHERE id=8491061",
        "date": "UPDATE shows SET date=date+interval '1 day' WHERE id=7451272",
        "user": "INSERT INTO saved_shows VALUES(7451272,'user','2026-02-01T00:00Z')",
        "lineup": "UPDATE lineup_items SET role='guest' WHERE show_id=3769502 AND comedian_id='comic'",
        "snapshot": "ALTER TABLE discovery_show_feature_snapshots ADD COLUMN payload text; UPDATE discovery_show_feature_snapshots SET payload='a'; INSERT INTO discovery_show_feature_snapshots VALUES(2,7451272,'v1','2026-01-01T00:00Z','b')",
    }
    with populated.cursor() as cur:
        cur.execute(changes[case])
        before = repair.snapshot(cur)
        with pytest.raises(ValueError, match="coalescence|identity|date|conflict"):
            repair.build_plan(cur)
        assert repair.snapshot(cur) == before


def test_backup_failure_happens_before_mutation(populated, plan, monkeypatch):
    def fail(*args):
        raise OSError("backup unavailable")

    monkeypatch.setattr(repair, "save_backup", fail)
    with populated.cursor() as cur:
        before = repair.snapshot(cur)
        with pytest.raises(OSError):
            repair.repair(cur, plan, "/unused")
        assert repair.snapshot(cur) == before


def test_mid_repair_failure_rolls_back_both_pairs_and_ticket_prices(populated, plan, monkeypatch):
    actual = repair.merge_show
    with populated.cursor() as cur:
        before = repair.snapshot(cur)
        cur.execute("SAVEPOINT repair_attempt")

        def fail(cur, old, new):
            actual(cur, old, new)
            raise RuntimeError("injected after first merge")

        monkeypatch.setattr(repair, "merge_show", fail)
        with pytest.raises(RuntimeError):
            repair.repair(cur, plan)
        cur.execute("ROLLBACK TO SAVEPOINT repair_attempt")
        assert repair.snapshot(cur) == before


@pytest.mark.parametrize("case", ["child", "schema", "checksum"])
def test_restore_refuses_drift(populated, plan, case):
    with populated.cursor() as cur:
        backup = repair.repair(cur, plan)
        if case == "child":
            cur.execute("UPDATE ticket_purchase_click_events SET payload='{}' WHERE id=0")
        elif case == "schema":
            cur.execute("ALTER TABLE shows ADD COLUMN changed text")
        else:
            backup["before"]["shows"][0]["description"] = "tampered"
        with pytest.raises(ValueError, match="drift|Schema|checksum"):
            repair.restore(cur, plan, backup)


def test_plan_cannot_change_reviewed_price_or_after_image(populated, plan):
    changed = copy.deepcopy(plan)
    changed["ticket_fills"][0]["price"] = 100
    with populated.cursor() as cur:
        with pytest.raises(ValueError, match="reviewed plan"):
            repair.repair(cur, changed)
        changed = copy.deepcopy(plan)
        changed["after_hash"] = "unreviewed"
        with pytest.raises(ValueError, match="after-image"):
            repair.repair(cur, changed)
