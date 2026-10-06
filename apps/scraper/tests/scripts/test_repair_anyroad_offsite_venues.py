"""Real PostgreSQL regressions for exact AnyRoad moves and reversible routing."""

import importlib.util
import json
import stat
from pathlib import Path

import pytest

from scripts.archive import repair_anyroad_offsite_venues_2026_10_06 as repair

_spec = importlib.util.spec_from_file_location(
    "anyroad_repair_schema", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
database = _schema.database


@pytest.fixture
def plan(database):
    with database.cursor() as cur:
        for table in repair.CHILDREN:
            cur.execute(f"DELETE FROM {table}")
        cur.execute("""
            DELETE FROM shows; DELETE FROM scraping_sources;
            ALTER TABLE shows ADD COLUMN source_performance_id text;
            CREATE UNIQUE INDEX native_key ON shows(club_id,source_performance_id) WHERE source_performance_id IS NOT NULL;
            CREATE UNIQUE INDEX legacy_key ON shows(club_id,date,room) WHERE source_performance_id IS NULL;
            CREATE TEMP TABLE organizer_aliases(id int PRIMARY KEY,producer_id int REFERENCES production_companies ON DELETE CASCADE);
            INSERT INTO clubs(id,name,address,website,city,state,zip_code,timezone) VALUES
                (10970,'The Rozzie Square Theater','18b Corinth St','https://rozziesquaretheater.com','Boston','MA','02131','America/New_York'),
                (61212,'The Substation','4228 Washington St','https://thesubstation.space','Boston','MA','02131','America/New_York');
            INSERT INTO scraping_sources VALUES(6820,10970,true,'{"plugin_id":"rozziesquaretheater"}','https://app.anyroad.com/i/plugin/rozziesquaretheater'),
                (12257,61212,true,'{"keep":true}','https://eventbrite.com');
        """)
        for index, ident in enumerate((3179506, 3558318, 3179545, 3179544, 99)):
            cur.execute(
                "INSERT INTO shows(id,club_id,date,show_page_url,room) VALUES(%s,%s,'2036-01-01T20:00Z'::timestamptz+%s*interval '1 day',%s,'The Substation')",
                (ident, 61212 if ident == 99 else 10970, index, f"https://anyroad.com/{ident}"),
            )
            cur.execute("INSERT INTO tickets(id,show_id,type,price) VALUES(%s,%s,'GA',20)", (ident, ident))
            cur.execute("INSERT INTO ticket_purchase_click_events(id,show_id) VALUES(%s,%s)", (ident, ident))
        return repair.build_plan(
            cur,
            [
                {"location_info": "18b Corinth Street, Boston, MA", "club_id": 10970},
                {"location_info": "The Substation, 4228 Washington Street", "club_id": 61212},
            ],
        )


def test_exact_moves_room_hold_preservation_and_rollback(database, plan, tmp_path):
    backup = tmp_path / "private.json"
    with database.cursor() as cur:
        result = repair.repair(cur, plan, backup)
        before = {row["id"]: row for row in result["before"]["shows"]}
        after = {row["id"]: row for row in result["after"]["shows"]}
        assert after[3179506]["club_id"] == after[3558318]["club_id"] == 61212
        assert after[3179545]["club_id"] == 10970
        assert after[3179545]["room"] == "18b Corinth Street, Boston, MA"
        assert before[3179544] == after[3179544]
        assert before[99] == after[99]
        for table in repair.CHILDREN:
            assert result["before"][table] == result["after"][table]
        assert repair.repair(cur, plan)["already_applied"]
        assert repair.rollback(cur, result)
        assert not repair.rollback(cur, result)
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    assert "after" not in json.loads(backup.read_text())


@pytest.mark.parametrize("kind", ["physical", "native", "room", "show", "source", "venue", "inventory"])
def test_conflicts_refused_before_moves(database, plan, kind):
    with database.cursor() as cur:
        if kind == "physical":
            cur.execute(
                "UPDATE shows SET date=(SELECT date FROM shows WHERE id=3179506),room='The Substation' WHERE id=99"
            )
        elif kind == "native":
            cur.execute("UPDATE shows SET source_performance_id='native-1' WHERE id IN(99,3179506)")
        elif kind == "room":
            cur.execute(
                "UPDATE shows SET club_id=10970,date=(SELECT date FROM shows WHERE id=3179545),room='18b Corinth Street, Boston, MA' WHERE id=99"
            )
        elif kind == "show":
            cur.execute("UPDATE shows SET description='unreviewed change' WHERE id=3179544")
        elif kind == "source":
            cur.execute("UPDATE scraping_sources SET enabled=false WHERE id=6820")
        elif kind == "venue":
            cur.execute("UPDATE clubs SET address='Different place' WHERE id=61212")
        else:
            cur.execute("INSERT INTO shows(id,club_id) VALUES(88,10970)")
        if kind in {"physical", "native", "room"}:
            plan["expected_show_hashes"] = {
                str(row["id"]): repair.digest(row) for row in repair.rows(cur, "shows", "club_id", repair.CLUB_IDS)
            }
        with pytest.raises(ValueError):
            repair.repair(cur, plan)
        cur.execute("SELECT club_id FROM shows WHERE id=3179506")
        assert cur.fetchone()[0] == 10970


def test_rollback_refuses_new_producer_reference(database, plan):
    with database.cursor() as cur:
        result = repair.repair(cur, plan)
        cur.execute("INSERT INTO organizer_aliases VALUES(1,%s)", (result["producer_id"],))
        with pytest.raises(ValueError, match="refusing rollback"):
            repair.rollback(cur, result)


def test_backup_failure_precedes_producer_and_show_writes(database, plan, monkeypatch):
    def fail(*args):
        raise OSError("Recovery unavailable")

    monkeypatch.setattr(repair, "save_backup", fail)
    with database.cursor() as cur, pytest.raises(OSError):
        repair.repair(cur, plan, "/unused")
    with database.cursor() as cur:
        cur.execute("SELECT count(*) FROM production_companies")
        assert cur.fetchone()[0] == 0
