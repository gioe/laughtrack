"""Real PostgreSQL checks for the date-only Mainstage repair and recovery."""

import copy
import importlib.util
import json
import stat
from datetime import timedelta
from pathlib import Path

import pytest

from scripts.archive import repair_anyroad_mainstage_times_2026_10_08 as repair

_spec = importlib.util.spec_from_file_location(
    "mainstage_schema", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
database = _schema.database


@pytest.fixture
def plan(database):
    with database.cursor() as cur:
        for table in (
            "tickets",
            "lineup_items",
            "tagged_shows",
            "saved_shows",
            "sent_notifications",
            "ticket_purchase_click_events",
            "discovery_show_feature_snapshots",
        ):
            cur.execute(f"DELETE FROM {table}")
        cur.execute("""DELETE FROM shows; DELETE FROM clubs; DELETE FROM scraping_sources;
            INSERT INTO clubs(id,name,total_shows) VALUES(10970,'Rozzie',3),(61212,'Substation',0);
            INSERT INTO production_companies(id,name) VALUES(50,'Rozzie');
            INSERT INTO production_company_venues VALUES(50,10970),(50,61212);
            INSERT INTO scraping_sources VALUES(6820,10970,true,'{"plugin_id":"rozziesquaretheater","anyroad_venue_routes":{"producer_id":50}}','https://app.anyroad.com/i/plugin/rozziesquaretheater');
        """)
        for ident, date in repair.DATES.items():
            cur.execute(
                "INSERT INTO shows(id,club_id,date,show_page_url,room) VALUES(%s,10970,%s,%s,%s)",
                (ident, repair.timestamp(date) - timedelta(minutes=30), repair.URL, repair.ROOM),
            )
            cur.execute(
                "INSERT INTO tickets(id,show_id,type,price,purchase_url) VALUES(%s,%s,'GA',15,%s)",
                (ident, ident, repair.URL),
            )
        cur.execute(
            """INSERT INTO shows(id,club_id,date,show_page_url,room) VALUES(99,10970,'2026-11-21T23:00Z','https://unrelated.example','Other room');
            INSERT INTO lineup_items VALUES(1,3179528,'comic','host');
            INSERT INTO tagged_shows VALUES(3179528,1);
            INSERT INTO saved_shows VALUES(3179528,'user','2026-01-01T00:00Z');
            INSERT INTO sent_notifications VALUES(1,3179528);
            INSERT INTO ticket_purchase_click_events VALUES(1,3179528);
            INSERT INTO discovery_show_feature_snapshots VALUES(1,3179528,'v1','2026-01-01T00:00Z');
        """
        )
        return repair.build_plan(cur)


def test_repeat_preserves_every_relationship_and_rollback_restores_exact_state(database, plan, tmp_path):
    path = tmp_path / "private.json"
    with database.cursor() as cur:
        result = repair.repair(cur, plan, path)
        before, after = result["before"], result["after"]
        assert set(r["id"] for r in before["shows"]) == set(r["id"] for r in after["shows"])
        for table in before:
            if table != "shows":
                assert before[table] == after[table]
        for original, updated in zip(before["shows"], after["shows"]):
            expected = dict(original)
            if original["id"] in repair.DATES:
                expected["date"] = repair.DATES[original["id"]]
            assert updated == expected
        assert repair.repair(cur, plan)["already_applied"]
        assert repair.restore(cur, plan, result)
        assert repair.snapshot(cur) == before
        assert repair.restore(cur, plan, result) is False
        assert not repair.repair(cur, plan)["already_applied"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    after_path = Path(str(path) + ".after.json")
    assert stat.S_IMODE(after_path.stat().st_mode) == 0o600
    assert json.loads(after_path.read_text())["after"] == after


@pytest.mark.parametrize("kind", ["slot", "native_other_venue"])
def test_collision_refused_before_any_write(database, plan, kind):
    with database.cursor() as cur:
        club, url, room = (
            (10970, "https://other.example", repair.ROOM) if kind == "slot" else (61212, repair.URL, "Other room")
        )
        cur.execute(
            "INSERT INTO shows(id,club_id,date,show_page_url,room) VALUES(100,%s,%s,%s,%s)",
            (club, repair.DATES[3179528], url, room),
        )
        before = repair.snapshot(cur)
        with pytest.raises(ValueError, match="collision"):
            repair.build_plan(cur)
        with pytest.raises(ValueError, match="before-image drift"):
            repair.repair(cur, plan)
        assert repair.snapshot(cur) == before


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE tickets SET price=20 WHERE show_id=3179528",
        "UPDATE shows SET description='changed' WHERE id=99",
        "UPDATE scraping_sources SET enabled=false WHERE id=6820",
        "INSERT INTO saved_shows VALUES(3179529,'new-user',now())",
    ],
)
def test_after_state_drift_refuses_rollback_without_changes(database, plan, statement):
    with database.cursor() as cur:
        result = repair.repair(cur, plan)
        cur.execute(statement)
        state = repair.snapshot(cur)
        with pytest.raises(ValueError, match="after-state drift"):
            repair.restore(cur, plan, result)
        assert repair.snapshot(cur) == state


def test_backup_cannot_be_overwritten(database, plan, tmp_path):
    path = tmp_path / "existing.json"
    path.write_text("preserve")
    with database.cursor() as cur:
        before = repair.snapshot(cur)
        with pytest.raises(FileExistsError):
            repair.repair(cur, plan, path)
        assert repair.snapshot(cur) == before
    assert path.read_text() == "preserve"


def test_tampered_recovery_and_plan_refused(database, plan):
    with database.cursor() as cur:
        result = repair.repair(cur, plan)
        bad = copy.deepcopy(result)
        bad["before"]["shows"][0]["room"] = "corrupt"
        with pytest.raises(ValueError, match="checksum"):
            repair.restore(cur, plan, bad)
        with pytest.raises(ValueError, match="reviewed plan"):
            repair.repair(cur, dict(plan, dates={}))
        assert repair.snapshot(cur) == result["after"]
