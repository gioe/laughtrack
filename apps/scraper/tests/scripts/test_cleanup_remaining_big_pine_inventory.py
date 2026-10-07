"""Real PostgreSQL coverage; temporary tables isolate every mutation and rollback."""

import importlib.util
import json
from pathlib import Path
import stat

import pytest
from scripts.core import cleanup_remaining_big_pine_inventory as cleanup

_spec = importlib.util.spec_from_file_location(
    "remaining_organizer_fixture", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
)
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)
database = _fixture.database


@pytest.fixture
def plan(database):
    decisions = json.loads((cleanup.AUDIT / "decisions.json").read_text())
    plan = {
        "task_id": 4132,
        "club_id": 573,
        "source_id": 360,
        "inventory_ids": [r["show_id"] for r in decisions],
        "retire_ids": sorted(cleanup.RETIRE_IDS),
    }
    with database.cursor() as cur:
        cur.execute("SET LOCAL TIME ZONE 'UTC'")
        cur.execute(
            "DELETE FROM shows; DELETE FROM clubs; DELETE FROM scraping_sources; DELETE FROM ticket_purchase_click_events"
        )
        cur.execute("""ALTER TABLE shows ADD COLUMN name text;
            ALTER TABLE ticket_purchase_click_events ADD COLUMN club_id int;
            CREATE TEMP TABLE source_targets(id int PRIMARY KEY, source_id int, target_type text);
            INSERT INTO clubs(id,name,visible,total_shows) VALUES(573,'Big Pine Comedy Festival',true,53);
            INSERT INTO scraping_sources VALUES(360,573,true,'{"exclude_title_patterns":["^submission$"],"keep":true}','https://example.com'),
                (3126,573,true,'{}','https://platform.example'),(7146,573,true,'{}','https://other.example');
            INSERT INTO source_targets VALUES(1,3126,'festival'),(2,7146,'festival');""")
        for row in decisions:
            ident = row["show_id"]
            cur.execute(
                "INSERT INTO shows(id,club_id,date,show_page_url,name,room) VALUES(%s,573,%s,%s,%s,%s)",
                (ident, row["stored_date"], row["show_page_url"], row["stored_name"], row["room"]),
            )
            cur.execute("INSERT INTO tickets(id,show_id,type) VALUES(%s,%s,'GA')", (ident, ident))
            cur.execute("INSERT INTO ticket_purchase_click_events VALUES(%s,%s,573)", (ident, ident))
        target = min(cleanup.RETIRE_IDS)
        cur.execute(
            """INSERT INTO saved_shows VALUES(%s,'user','2035-01-01T00:00Z');
            INSERT INTO tagged_shows VALUES(%s,1); INSERT INTO lineup_items VALUES(1,%s,'comic','host');
            INSERT INTO sent_notifications VALUES(1,%s);
            INSERT INTO discovery_show_feature_snapshots VALUES(1,%s,'v1','2035-01-01T00:00Z');
            INSERT INTO ticket_purchase_click_events VALUES(999,NULL,573);""",
            (target,) * 5,
        )
        before = cleanup.snapshot(cur, plan)
        plan["click_ids"] = [r["id"] for r in before[cleanup.CLICKS]]
        plan["before_hashes"] = {t: cleanup.digest(v) for t, v in before.items()}
        plan["expected_counts"] = {t: len(v) for t, v in before.items()}
        after = cleanup.expected_after(before)
        plan["after_hashes"] = {t: cleanup.digest(v) for t, v in after.items()}
        plan["after_counts"] = {t: len(v) for t, v in after.items()}
    return plan


def test_exact_cleanup_private_backup_and_dependent_recovery(database, plan, tmp_path):
    path = tmp_path / "private.json"
    with database.cursor() as cur:
        result = cleanup.repair(cur, plan, path)
        before, after = result["before"], result["after"]
        assert {r["id"] for r in after["shows"]} == set(plan["inventory_ids"]) - cleanup.RETIRE_IDS
        assert len(after["shows"]) == 17
        assert next(r for r in after["shows"] if r["id"] == 522192) in before["shows"]
        assert len(after[cleanup.CLICKS]) == len(before[cleanup.CLICKS]) == 54
        assert sum(r["show_id"] is None for r in after[cleanup.CLICKS]) == 37
        assert after["scraping_sources"] == before["scraping_sources"]
        assert after["source_targets"] == before["source_targets"]
        assert after["clubs"][0]["visible"] is True
        assert json.loads(path.read_text())["before"] == before
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert cleanup.repair(cur, plan)["already_applied"] is True
        saved = json.loads(Path(str(path) + ".after.json").read_text())
        cleanup.restore(cur, plan, saved)
        assert cleanup.snapshot(cur, plan) == before
        for table in cleanup.CHILDREN:
            assert cleanup.snapshot(cur, plan)[table] == before[table]
        cleanup.restore(cur, plan, saved)


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE shows SET room='changed' WHERE id=522192",
        "DELETE FROM shows WHERE id=7773673",
        "UPDATE source_targets SET target_type='changed' WHERE id=1",
        "INSERT INTO ticket_purchase_click_events VALUES(888,NULL,573)",
        "INSERT INTO shows(id,club_id) VALUES(888,573)",
        "UPDATE scraping_sources SET metadata='{}' WHERE id=360",
    ],
)
def test_drift_precedes_backup_and_mutation(database, plan, tmp_path, mutation):
    path = tmp_path / "private.json"
    with database.cursor() as cur:
        cur.execute(mutation)
        before = cleanup.snapshot(cur, plan)
        with pytest.raises(ValueError, match="before-image changed"):
            cleanup.repair(cur, plan, path)
        assert cleanup.snapshot(cur, plan) == before
        assert not path.exists()


def test_backup_failure_precedes_deletion(database, plan, tmp_path):
    path = tmp_path / "private.json"
    path.write_text("keep")
    with database.cursor() as cur:
        before = cleanup.snapshot(cur, plan)
        with pytest.raises(FileExistsError):
            cleanup.repair(cur, plan, path)
        assert cleanup.snapshot(cur, plan) == before
        assert path.read_text() == "keep"


def test_unreviewed_cohort_rejected(database, plan):
    plan["retire_ids"].append(522192)
    with database.cursor() as cur, pytest.raises(ValueError, match="exactly the 36"):
        cleanup.repair(cur, plan)


def test_rehashed_native_date_drift_rejected(database, plan):
    with database.cursor() as cur:
        cur.execute("UPDATE shows SET date=date+interval '1 day' WHERE id=7773673")
        before = cleanup.snapshot(cur, plan)
        plan["before_hashes"]["shows"] = cleanup.digest(before["shows"])
        with pytest.raises(ValueError, match="native occurrence identity changed"):
            cleanup.repair(cur, plan)
        assert cleanup.snapshot(cur, plan) == before


@pytest.mark.parametrize(
    "ddl",
    [
        "CREATE TEMP TABLE extra_reference(show_id int REFERENCES shows ON DELETE CASCADE)",
        "CREATE TEMP TABLE child_reference(ticket_id int REFERENCES tickets)",
    ],
)
def test_unknown_relationship_rejected(database, plan, ddl):
    with database.cursor() as cur:
        cur.execute(ddl)
        with pytest.raises(ValueError, match="references|foreign keys"):
            cleanup.repair(cur, plan)


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE shows SET room='changed' WHERE id=522192",
        "INSERT INTO ticket_purchase_click_events VALUES(888,522192,573)",
        "UPDATE ticket_purchase_click_events SET show_id=522192 WHERE id=7773673",
        "INSERT INTO ticket_purchase_click_events VALUES(888,NULL,573)",
        "UPDATE scraping_sources SET metadata='{}' WHERE id=360",
    ],
)
def test_restore_rejects_post_cleanup_drift(database, plan, mutation):
    with database.cursor() as cur:
        result = cleanup.repair(cur, plan)
        cur.execute(mutation)
        before = cleanup.snapshot(cur, plan)
        with pytest.raises(ValueError, match="Affected rows changed"):
            cleanup.restore(cur, plan, result)
        assert cleanup.snapshot(cur, plan) == before


def test_restore_schema_and_checksum_guards(database, plan):
    with database.cursor() as cur:
        result = cleanup.repair(cur, plan)
        result["before_hash"] = "changed"
        with pytest.raises(ValueError, match="checksum"):
            cleanup.restore(cur, plan, result)
        result["before_hash"] = cleanup.digest(result["before"])
        cur.execute("ALTER TABLE tickets ADD COLUMN extra text")
        with pytest.raises(ValueError, match="Schema changed"):
            cleanup.restore(cur, plan, result)


def test_invalid_reviewed_after_hash_precedes_mutation(database, plan, tmp_path):
    plan["after_hashes"]["shows"] = "changed"
    path = tmp_path / "private.json"
    with database.cursor() as cur:
        before = cleanup.snapshot(cur, plan)
        with pytest.raises(ValueError, match="Reviewed after-image"):
            cleanup.repair(cur, plan, path)
        assert cleanup.snapshot(cur, plan) == before
        assert not path.exists()


def test_recomputed_backup_checksum_cannot_change_reviewed_images(database, plan):
    with database.cursor() as cur:
        result = cleanup.repair(cur, plan)
        result["before"]["clubs"][0]["total_shows"] = 100
        result["before_hash"] = cleanup.digest(result["before"])
        with pytest.raises(ValueError, match="images do not match reviewed plan"):
            cleanup.restore(cur, plan, result)


def test_malformed_after_plan_cannot_report_cleanup_before_deletion(database, plan):
    plan["after_hashes"] = dict(plan["before_hashes"])
    plan["after_counts"] = dict(plan["expected_counts"])
    with database.cursor() as cur, pytest.raises(ValueError, match="still includes products"):
        cleanup.repair(cur, plan)
