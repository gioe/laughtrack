"""Real PostgreSQL coverage of the exact-row disable and guarded recovery."""

import copy
import importlib.util
import json
import stat
from pathlib import Path

import pytest

from scripts.archive import disable_barrel_room_source_2026_10_08 as repair

_spec = importlib.util.spec_from_file_location(
    "barrel_schema", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
database = _schema.database


@pytest.fixture
def plan(database):
    with database.cursor() as cur:
        cur.execute("""
            UPDATE clubs SET id=88,name='Barrel Room' WHERE id=600;
            UPDATE shows SET club_id=88 WHERE club_id=600;
            ALTER TABLE shows ADD source_performance_id text;
            ALTER TABLE scraping_sources ADD platform text, ADD scraper_key text,
                ADD seatengine_id int, ADD updated_at timestamptz DEFAULT now();
            UPDATE scraping_sources SET id=77,club_id=88,platform='seatengine',
                scraper_key='seatengine_classic',seatengine_id=324,
                source_url='https://www.barrelroompdx.com/events' WHERE id=259;
            CREATE FUNCTION pg_temp.refresh_source() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN NEW.updated_at = clock_timestamp(); RETURN NEW; END $$;
            CREATE TRIGGER source_timestamp BEFORE UPDATE ON scraping_sources
                FOR EACH ROW EXECUTE FUNCTION pg_temp.refresh_source();
        """)
        repair.lock_schema(cur)
        return repair.build_plan(cur, repair.snapshot(cur)["scraping_sources"][0])


def test_disable_repeat_preserves_history_and_recovery_handles_timestamp_trigger(database, plan, tmp_path):
    path = tmp_path / "private.json"
    with database.cursor() as cur:
        result = repair.repair(cur, plan, path)
        before, after = result["before"], result["after"]
        assert after["scraping_sources"][0]["enabled"] is False
        assert after["scraping_sources"][0]["updated_at"] != before["scraping_sources"][0]["updated_at"]
        for table in before:
            if table != "scraping_sources":
                assert before[table] == after[table]
        assert repair.repair(cur, plan)["already_applied"]
        assert repair.restore(cur, plan, result)
        assert repair.business(repair.snapshot(cur)) == repair.business(before)
        assert repair.restore(cur, plan, result) is False
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    after_path = Path(str(path) + ".after.json")
    assert stat.S_IMODE(after_path.stat().st_mode) == 0o600
    assert "after" not in json.loads(path.read_text())
    assert json.loads(after_path.read_text())["after"] == after


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE scraping_sources SET seatengine_id=339 WHERE id=77",
        "UPDATE scraping_sources SET metadata='{}' WHERE id=77",
        "UPDATE clubs SET name='Different' WHERE id=88",
        "UPDATE tickets SET price=99 WHERE id=1",
        "INSERT INTO scraping_sources(id,club_id,enabled) VALUES(999,88,true)",
    ],
)
def test_before_drift_refused_without_writes(database, plan, statement):
    with database.cursor() as cur:
        cur.execute(statement)
        before = repair.snapshot(cur)
        with pytest.raises(ValueError, match="before-image drift"):
            repair.repair(cur, plan)
        assert repair.snapshot(cur) == before


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE shows SET description='changed' WHERE id=12",
        "UPDATE tickets SET price=99 WHERE id=1",
        "INSERT INTO saved_shows VALUES(10,'new-user',now())",
        "UPDATE scraping_sources SET metadata='{}' WHERE id=77",
        "UPDATE scraping_sources SET updated_at=now() WHERE id=77",
    ],
)
def test_after_drift_refuses_rollback_without_writes(database, plan, statement):
    with database.cursor() as cur:
        result = repair.repair(cur, plan)
        cur.execute(statement)
        before = repair.snapshot(cur)
        with pytest.raises(ValueError, match="after-state drift"):
            repair.restore(cur, plan, result)
        assert repair.snapshot(cur) == before


def test_existing_backup_is_not_overwritten(database, plan, tmp_path):
    path = tmp_path / "existing.json"
    path.write_text("preserve")
    with database.cursor() as cur:
        before = repair.snapshot(cur)
        with pytest.raises(FileExistsError):
            repair.repair(cur, plan, path)
        assert repair.snapshot(cur) == before
    assert path.read_text() == "preserve"


def test_tampered_backup_and_changed_schema_refuse_recovery(database, plan):
    with database.cursor() as cur:
        result = repair.repair(cur, plan)
        bad = copy.deepcopy(result)
        bad["before"]["tickets"][0]["price"] = 999
        with pytest.raises(ValueError, match="checksum"):
            repair.restore(cur, plan, bad)
        cur.execute("ALTER TABLE scraping_sources ADD new_field text")
        with pytest.raises(ValueError, match="Schema changed"):
            repair.restore(cur, plan, result)


def test_unknown_child_reference_requires_recovery_review(database, plan):
    with database.cursor() as cur:
        cur.execute("CREATE TEMP TABLE new_child(show_id int REFERENCES shows)")
        with pytest.raises(ValueError, match="foreign keys changed"):
            repair.repair(cur, plan)
