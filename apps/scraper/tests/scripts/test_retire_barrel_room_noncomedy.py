"""PostgreSQL regression coverage for the approved cleanup and exact recovery."""

import copy
import importlib.util
import json
import stat
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from scripts.archive import retire_barrel_room_noncomedy_2026_10_08 as repair

_spec = importlib.util.spec_from_file_location(
    "barrel_cleanup_schema", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
database = _schema.database


def test_committed_native_manifest_is_pinned():
    review = repair.evidence()
    assert len({r["id"] for r in review["shows"]}) == 36
    assert all(r["identity_and_date_match"] and r["decision"] == "verified_non_comedy" for r in review["shows"])


@pytest.fixture
def plan(database, monkeypatch):
    # Move fixture dates far into the future so tests do not expire with this one-off.
    review = copy.deepcopy(repair.evidence())
    for row in review["shows"]:
        row["date"] = (datetime.fromisoformat(row["date"]) + timedelta(days=36500)).isoformat()
    monkeypatch.setattr(repair, "evidence", lambda: review)
    with database.cursor() as cur:
        cur.execute("""
            UPDATE clubs SET id=88,name='Barrel Room',total_shows=39 WHERE id=600;
            UPDATE shows SET club_id=88,date='2016-01-01T00:00Z' WHERE club_id=600;
            ALTER TABLE shows ADD name text, ADD source_performance_id text;
            UPDATE shows SET name='Historical comedy';
            UPDATE scraping_sources SET id=77,club_id=88,enabled=false WHERE id=259;
            ALTER TABLE ticket_purchase_click_events ADD club_id int, ADD purchase_url text;
            UPDATE ticket_purchase_click_events SET club_id=88,purchase_url='https://historical.example';
            INSERT INTO ticket_purchase_click_events VALUES(3,NULL,88,'https://already-detached.example');
        """)
        for row in review["shows"]:
            cur.execute(
                "INSERT INTO shows(id,club_id,name,date,show_page_url) VALUES(%s,88,%s,%s,%s)",
                (row["id"], row["name"], row["date"], row["show_page_url"]),
            )
            cur.execute(
                "INSERT INTO tickets(id,show_id,type,price,purchase_url) VALUES(%s,%s,'GA',20,%s)",
                (row["id"], row["id"], row["show_page_url"]),
            )
            cur.execute("INSERT INTO tagged_shows VALUES(%s,8)", (row["id"],))
        cur.execute(
            "INSERT INTO ticket_purchase_click_events VALUES(2,%s,88,'https://retired.example')",
            (review["shows"][0]["id"],),
        )
        return repair.build_plan(cur)


def test_cleanup_preserves_click_records_history_source_and_exact_restore(database, plan, tmp_path):
    path = tmp_path / "private.json"
    with database.cursor() as cur:
        result = repair.repair(cur, plan, path)
        before, after = result["before"], result["after"]
        assert len(after["shows"]) == 3
        assert {r["id"] for r in after["shows"]} == {10, 11, 12}
        assert after["scraping_sources"] == before["scraping_sources"]
        assert after["clubs"][0] == dict(before["clubs"][0], total_shows=3)
        for table in repair.PROTECTED:
            assert before[table] == after[table]
        assert len(after[repair.CLICKS]) == len(before[repair.CLICKS]) == 3
        clicks = {r["id"]: r for r in after[repair.CLICKS]}
        assert clicks[2] == dict(next(r for r in before[repair.CLICKS] if r["id"] == 2), show_id=None)
        assert clicks[1]["show_id"] == 11
        assert clicks[3]["show_id"] is None
        cur.execute("SELECT id FROM shows WHERE club_id=88 AND date>now() AND is_cancelled=false")
        assert cur.fetchall() == []
        assert repair.repair(cur, plan)["already_applied"]
        assert repair.restore(cur, plan, result)
        assert repair.snapshot(cur) == before
        assert not repair.restore(cur, plan, result)
        assert not repair.repair(cur, plan)["already_applied"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    after_path = Path(str(path) + ".after.json")
    assert stat.S_IMODE(after_path.stat().st_mode) == 0o600
    assert json.loads(after_path.read_text())["after"] == after


@pytest.mark.parametrize("table", repair.PROTECTED)
def test_protected_target_reference_refused_even_with_fresh_plan(database, plan, table):
    ident = repair.evidence()["shows"][0]["id"]
    statements = {
        "lineup_items": "INSERT INTO lineup_items VALUES(99,%s,'new-comic','host')",
        "saved_shows": "INSERT INTO saved_shows VALUES(%s,'new-user',now())",
        "sent_notifications": "INSERT INTO sent_notifications VALUES(99,%s)",
        "discovery_show_feature_snapshots": "INSERT INTO discovery_show_feature_snapshots VALUES(99,%s,'v1',now())",
    }
    with database.cursor() as cur:
        cur.execute(statements[table], (ident,))
        before = repair.snapshot(cur)
        with pytest.raises(ValueError, match="Protected reference"):
            repair.build_plan(cur)
        with pytest.raises(ValueError, match="before-image drift"):
            repair.repair(cur, plan)
        assert repair.snapshot(cur) == before


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE scraping_sources SET enabled=true WHERE id=77",
        "UPDATE shows SET description='changed history' WHERE id=10",
        "UPDATE tickets SET price=99 WHERE id=1",
        "UPDATE ticket_purchase_click_events SET purchase_url='drift' WHERE id=2",
    ],
)
def test_before_drift_aborts_without_writes(database, plan, statement):
    with database.cursor() as cur:
        cur.execute(statement)
        before = repair.snapshot(cur)
        with pytest.raises(ValueError, match="before-image drift"):
            repair.repair(cur, plan)
        assert repair.snapshot(cur) == before


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE ticket_purchase_click_events SET show_id=10 WHERE id=2",
        "UPDATE ticket_purchase_click_events SET club_id=601 WHERE id=2",
        "INSERT INTO ticket_purchase_click_events VALUES(99,NULL,88,'new')",
        "UPDATE shows SET description='changed history' WHERE id=10",
        "UPDATE scraping_sources SET enabled=true WHERE id=77",
    ],
)
def test_after_drift_refuses_restore_without_writes(database, plan, statement):
    with database.cursor() as cur:
        result = repair.repair(cur, plan)
        cur.execute(statement)
        state = repair.snapshot(cur)
        with pytest.raises(ValueError, match="after-state drift"):
            repair.restore(cur, plan, result)
        assert repair.snapshot(cur) == state


def test_backup_collision_rolls_back_transaction(database, plan, tmp_path):
    path = tmp_path / "private.json"
    Path(str(path) + ".after.json").write_text("existing")
    with database.cursor() as cur:
        before = repair.snapshot(cur)
        cur.execute("SAVEPOINT apply_attempt")
        with pytest.raises(FileExistsError):
            repair.repair(cur, plan, path)
        cur.execute("ROLLBACK TO SAVEPOINT apply_attempt")
        assert repair.snapshot(cur) == before
    assert Path(str(path) + ".after.json").read_text() == "existing"


def test_schema_and_tampered_recovery_are_rejected(database, plan):
    with database.cursor() as cur:
        result = repair.repair(cur, plan)
        bad = copy.deepcopy(result)
        bad["before"]["shows"][0]["description"] = "tampered"
        with pytest.raises(ValueError, match="checksum"):
            repair.restore(cur, plan, bad)
        cur.execute("ALTER TABLE tickets ADD new_column text")
        with pytest.raises(ValueError, match="Schema changed"):
            repair.restore(cur, plan, result)


def test_unknown_child_fk_refused(database, plan):
    with database.cursor() as cur:
        cur.execute("CREATE TEMP TABLE new_child(show_id int REFERENCES shows)")
        with pytest.raises(ValueError, match="foreign keys changed"):
            repair.repair(cur, plan)
