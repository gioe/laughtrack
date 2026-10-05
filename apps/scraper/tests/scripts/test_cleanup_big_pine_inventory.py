"""Real PostgreSQL cascade, preservation, and guard checks; each test rolls back."""

import importlib.util
import json
import stat
from pathlib import Path

import pytest

from scripts.core import cleanup_big_pine_inventory as cleanup

_spec = importlib.util.spec_from_file_location(
    "organizer_fixture", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
)
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)
database = _fixture.database


@pytest.fixture
def plan(database):
    plan = json.loads(cleanup.PLAN_PATH.read_text())
    with database.cursor() as cur:
        cur.execute("SET LOCAL TIME ZONE 'UTC'")
        cur.execute(
            "DELETE FROM shows; DELETE FROM clubs; DELETE FROM scraping_sources; DELETE FROM ticket_purchase_click_events"
        )
        cur.execute("""CREATE TEMP TABLE source_targets(id int PRIMARY KEY, source_id int, target_type text);
            INSERT INTO clubs(id,name,visible) VALUES(573,'Big Pine Comedy Festival',true);
            INSERT INTO scraping_sources VALUES(360,573,true,'{"keep":true}','https://example.com'),
                (3126,573,true,'{}','https://platform.example'),(7146,573,true,'{}','https://other.example');
            INSERT INTO source_targets VALUES(1,3126,'festival'),(2,7146,'festival');""")
        ids = sorted(cleanup.RETIRE_IDS | {999})
        for show_id in ids:
            cur.execute(
                "INSERT INTO shows(id,club_id,date,show_page_url) VALUES(%s,573,'2036-01-01T20:00Z',%s)",
                (show_id, f"https://example.com/shows/{show_id}"),
            )
            cur.execute("INSERT INTO tickets(id,show_id,type) VALUES(%s,%s,'GA')", (show_id, show_id))
            cur.execute("INSERT INTO ticket_purchase_click_events VALUES(%s,%s)", (show_id, show_id))
        target = min(cleanup.RETIRE_IDS)
        cur.execute(
            "INSERT INTO saved_shows VALUES(%s,'user','2035-01-01T00:00Z'); INSERT INTO tagged_shows VALUES(%s,1); INSERT INTO lineup_items VALUES(1,%s,'comic','host'); INSERT INTO sent_notifications VALUES(1,%s); INSERT INTO discovery_show_feature_snapshots VALUES(1,%s,'v1','2035-01-01T00:00Z')",
            (target,) * 5,
        )
        plan["inventory_ids"] = ids
        state = cleanup.snapshot(cur, plan)
        plan["before_hashes"] = {table: cleanup.digest(rows) for table, rows in state.items()}
        plan["expected_counts"] = {table: len(rows) for table, rows in state.items()}
    return plan


def test_exact_deletion_preserves_clicks_festival_sources_and_hold(database, plan, tmp_path):
    backup = tmp_path / "private.json"
    with database.cursor() as cur:
        result = cleanup.repair(cur, plan, backup)
        before, after = result["before"], result["after"]
        assert [r["id"] for r in after["shows"]] == [999]
        assert len(after["tickets"]) == 1
        assert len(after[cleanup.CLICKS]) == 20
        assert sum(r["show_id"] is None for r in after[cleanup.CLICKS]) == 19
        assert after["source_targets"] == before["source_targets"]
        assert after["clubs"][0]["visible"] is True
        assert after["clubs"][0]["total_shows"] == 1
        sources = {r["id"]: r for r in after["scraping_sources"]}
        assert sources[360]["metadata"]["keep"] is True
        assert sources[3126] == next(r for r in before["scraping_sources"] if r["id"] == 3126)
        assert json.loads(backup.read_text())["before"] == before
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600
        assert json.loads(Path(str(backup) + ".after.json").read_text())["after"] == after
        assert cleanup.repair(cur, plan)["already_applied"] is True


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE shows SET room='changed' WHERE id=999",
        "DELETE FROM shows WHERE id=1376633",
        "UPDATE source_targets SET target_type='changed' WHERE id=1",
        "INSERT INTO ticket_purchase_click_events VALUES(888,999)",
        "INSERT INTO shows(id,club_id) VALUES(888,573)",
    ],
)
def test_drift_aborts_before_backup_or_mutations(database, plan, tmp_path, mutation):
    with database.cursor() as cur:
        cur.execute(mutation)
        before = cleanup.snapshot(cur, plan)
        backup = tmp_path / "private.json"
        with pytest.raises(ValueError, match="before-image changed"):
            cleanup.repair(cur, plan, backup)
        assert cleanup.snapshot(cur, plan) == before
        assert not backup.exists()


def test_unreviewed_relationship_aborts(database, plan):
    with database.cursor() as cur:
        cur.execute("CREATE TEMP TABLE extra_reference(show_id int REFERENCES shows ON DELETE CASCADE)")
        with pytest.raises(ValueError, match="foreign keys changed"):
            cleanup.repair(cur, plan)


def test_backup_failure_precedes_mutations(database, plan, tmp_path):
    backup = tmp_path / "exists.json"
    backup.write_text("keep")
    with database.cursor() as cur:
        before = cleanup.snapshot(cur, plan)
        with pytest.raises(FileExistsError):
            cleanup.repair(cur, plan, backup)
        assert cleanup.snapshot(cur, plan) == before
        assert backup.read_text() == "keep"


def test_refuses_broader_deletion_cohort(database, plan):
    plan["retire_ids"].append(999)
    with database.cursor() as cur, pytest.raises(ValueError, match="exactly the 19"):
        cleanup.repair(cur, plan)
