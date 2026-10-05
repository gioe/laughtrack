"""Real PostgreSQL regressions for the strictly bounded AC Jokes repair."""

import importlib.util
import copy
import json
import stat
from pathlib import Path

import pytest

from scripts.core import repair_ac_jokes_venues as repair

# Reuse the temporary seven-child-table schema used by the previous venue repair.
_spec = importlib.util.spec_from_file_location(
    "seatengine_repair_test_schema", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
database = _schema.database


@pytest.fixture
def plan(database):
    with database.cursor() as cur:
        for table in repair.CHILDREN:
            cur.execute(f"DELETE FROM {table}")
        cur.execute("DELETE FROM shows; DELETE FROM scraping_sources")
        cur.execute("INSERT INTO clubs(id,name) VALUES(412,'AC Jokes Resorts')")
        cur.execute("INSERT INTO scraping_sources VALUES(291,412,true,'{\"keep\":true}','https://acjokes.com')")
        for ident in (6537828, 6537839, 7475796, *range(100, 140)):
            cur.execute(
                "INSERT INTO shows(id,club_id,date,show_page_url) VALUES(%s,412,'2036-01-01T20:00Z'::timestamptz + %s * interval '1 minute',%s)",
                (ident, ident % 1440, f"https://acjokes.com/{ident}"),
            )
            cur.execute("INSERT INTO tickets(id,show_id,type,price) VALUES(%s,%s,'GA',20)", (ident, ident))
            cur.execute("INSERT INTO ticket_purchase_click_events(id,show_id) VALUES(%s,%s)", (ident, ident))
        cur.execute("SELECT to_jsonb(t) FROM shows t ORDER BY id")
        rows = [row[0] for row in cur.fetchall()]
    fields = lambda name: {
        "name": name,
        "address": "1 Main St",
        "city": "Atlantic City",
        "state": "NJ",
        "timezone": "America/New_York",
        "website": "https://example.com",
    }
    return {
        "task_id": 4110,
        "clubs": {
            "resorts": {"id": 412, "fields": {"name": "AC Jokes Resorts"}},
            "hi-point": {"fields": fields("Hi Point")},
            "cove": {"fields": fields("Cove")},
        },
        "producers": {"ac-jokes": {"fields": {"name": "AC Jokes", "slug": "ac-jokes"}}},
        "shows": [
            {
                "id": row["id"],
                "before": row,
                "club": "cove" if row["id"] == 7475796 else "hi-point",
                "producer": "ac-jokes",
            }
            for row in rows
            if row["id"] > 100000
        ],
        "holds": [{"id": row["id"], "before": row} for row in rows if row["id"] < 100000]
        + [{"id": 6537818, "absent": True}],
        "sources": [
            {
                "id": 291,
                "before": {"club_id": 412, "enabled": True, "metadata": {"keep": True}},
                "patch": {
                    "metadata": {
                        "keep": True,
                        "wix_venue_routes": {
                            "source_id": 291,
                            "component_id": "comp-lpdlygbr",
                            "producer_id": {"$producer": "ac-jokes"},
                            "routes": [{"club_id": {"$club": symbol}} for symbol in ("resorts", "hi-point", "cove")],
                        },
                    }
                },
            }
        ],
    }


def test_three_moves_preserve_forty_rows_and_every_child(database, plan, tmp_path):
    path = tmp_path / "backup.json"
    with database.cursor() as cur:
        result = repair.repair(cur, plan, path)
        assert len(result["before"]["shows"]) == len(result["after"]["shows"]) == 43
        before = {r["id"]: r for r in result["before"]["shows"]}
        after = {r["id"]: r for r in result["after"]["shows"]}
        assert all(before[ident] == after[ident] for ident in range(100, 140))
        for table in repair.CHILDREN:
            assert result["before"][table] == result["after"][table]
        assert after[6537828]["club_id"] == result["clubs"]["hi-point"]
        assert after[7475796]["club_id"] == result["clubs"]["cove"]
        assert {row["club_id"] for row in result["after"]["production_company_venues"]} == set(result["clubs"].values())
        assert repair.repair(cur, plan)["already_applied"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert "after" not in json.loads(path.read_text())


@pytest.mark.parametrize(
    "conflict", ["slot", "held_drift", "absent_reappears", "source_drift", "unknown_fk", "new_inventory"]
)
def test_refuses_drift_before_mutation(database, plan, conflict):
    with database.cursor() as cur:
        if conflict == "slot":
            # A second show at the destination/time must never be overwritten.
            plan["clubs"]["hi-point"] = {"id": 601, "fields": {"name": "Known Venue"}}
            cur.execute("INSERT INTO shows(id,club_id,date) SELECT 99,601,date FROM shows WHERE id=6537828")
        elif conflict == "held_drift":
            cur.execute("UPDATE shows SET club_id=600 WHERE id=100")
        elif conflict == "absent_reappears":
            cur.execute("INSERT INTO shows(id) VALUES(6537818)")
        elif conflict == "source_drift":
            cur.execute("UPDATE scraping_sources SET enabled=false")
        elif conflict == "new_inventory":
            cur.execute("INSERT INTO shows(id,club_id) VALUES(77,412)")
        else:
            cur.execute("CREATE TEMP TABLE unexpected(show_id int REFERENCES shows)")
        with pytest.raises(ValueError):
            repair.repair(cur, plan)
        cur.execute("SELECT club_id FROM shows WHERE id=6537828")
        assert cur.fetchone()[0] == 412


def test_backup_failure_prevents_business_writes(database, plan, monkeypatch):
    def fail(*args):
        raise OSError("Cannot write recovery")

    monkeypatch.setattr(repair, "save_backup", fail)
    with database.cursor() as cur, pytest.raises(OSError):
        repair.repair(cur, plan, "/unused")
    with database.cursor() as cur:
        cur.execute("SELECT count(*) FROM production_companies")
        assert cur.fetchone()[0] == 0


def test_unreviewed_move_id_rejected(plan):
    plan["shows"][0]["id"] = 99
    with pytest.raises(ValueError):
        repair.validate_plan(plan)


def test_full_held_row_preservation_rejects_unplanned_description_change():
    before = {"shows": [{"id": 100, "description": "Keep original"}], "clubs": [{"id": 412}]}
    before.update({table: [] for table in repair.CHILDREN})
    after = copy.deepcopy(before)
    after["shows"][0]["description"] = "Changed"
    with pytest.raises(ValueError, match="Unreviewed show fields"):
        repair.verify_preservation(before, after)
