"""Real PostgreSQL coverage of reviewed AnyRoad merge/room repair and recovery."""

import copy
import importlib.util
import json
import stat
from pathlib import Path

import pytest

from scripts.archive import repair_anyroad_blank_rooms_2026_10_08 as repair

_spec = importlib.util.spec_from_file_location(
    "anyroad_blank_schema", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
database = _schema.database


@pytest.fixture
def decisions(database):
    with database.cursor() as cur:
        for table in repair.CHILDREN:
            cur.execute(f"DELETE FROM {table}")
        cur.execute("""DELETE FROM shows; DELETE FROM clubs; DELETE FROM scraping_sources;
            ALTER TABLE shows ADD COLUMN source_performance_id text;
            INSERT INTO clubs(id,name,total_shows) VALUES(10970,'The Rozzie Square Theater',15),(61212,'The Substation',0);
            INSERT INTO production_companies(id,name) VALUES(50,'The Rozzie Square Theater');
            INSERT INTO production_company_venues VALUES(50,10970),(50,61212);
            INSERT INTO scraping_sources VALUES(6820,10970,true,'{"plugin_id":"rozziesquaretheater","anyroad_venue_routes":{"producer_id":50}}','https://app.anyroad.com/i/plugin/rozziesquaretheater'),(12257,61212,true,'{}','https://unrelated.example');
        """)
        result = []
        for i, (old, target) in enumerate(repair.MERGES.items()):
            date = f"2036-12-{i+1:02d}"
            url = f"https://app.anyroad.com/i/plugin/rozziesquaretheater/tours/experience-{i}"
            for ident, hour, room in ((old, 14, ""), (target, 23, "Old room")):
                cur.execute(
                    "INSERT INTO shows(id,club_id,date,show_page_url,room) VALUES(%s,10970,%s,%s,%s)",
                    (ident, date + f"T{hour}:00Z", url, room),
                )
                cur.execute(
                    "INSERT INTO tickets(id,show_id,type,price,purchase_url) VALUES(%s,%s,'GA',11,%s)",
                    (ident, ident, url),
                )
            result.append(
                dict(
                    id=target,
                    merge_from=old,
                    experience_id=str(i + 1),
                    reason="native reviewed slot",
                    patch=dict(
                        room="The Substation" if i == 2 else "18b Corinth Street, Boston, MA",
                        club_id=61212 if i == 2 else 10970,
                        production_company_id=50,
                        scraped_by_organizer_id=50,
                        date=date + "T23:30:00+00:00",
                    ),
                )
            )
        for i, ident in enumerate(sorted(repair.ROOM_ONLY)):
            cur.execute(
                "INSERT INTO shows(id,club_id,date,show_page_url,room) VALUES(%s,10970,%s,%s,NULL)",
                (
                    ident,
                    f"2037-06-{i+1:02d}T22:00Z",
                    "https://app.anyroad.com/i/plugin/rozziesquaretheater/tours/comedy",
                ),
            )
            result.append(
                dict(
                    id=ident,
                    merge_from=None,
                    experience_id="79259",
                    reason="verified future calendar",
                    patch=dict(
                        room="18b Corinth Street, Boston, MA", production_company_id=50, scraped_by_organizer_id=50
                    ),
                )
            )
        for i, ident in enumerate((3789176, 3179550, 3179544)):
            cur.execute(
                "INSERT INTO shows(id,club_id,date,show_page_url,room) VALUES(%s,10970,%s,%s,NULL)",
                (ident, f"2036-12-{i+1:02d}T14:00Z", f"https://hold.example/{ident}"),
            )
        old, target = next(iter(repair.MERGES.items()))
        cur.execute("INSERT INTO lineup_items VALUES(1,%s,'comic','host'),(2,%s,'comic','host')", (old, target))
        cur.execute("INSERT INTO tagged_shows VALUES(%s,1),(%s,1),(%s,2)", (old, target, old))
        cur.execute("INSERT INTO saved_shows VALUES(%s,'user','2035-01-01T00:00Z')", (old,))
        cur.execute("INSERT INTO sent_notifications VALUES(1,%s)", (old,))
        cur.execute("INSERT INTO ticket_purchase_click_events VALUES(1,%s)", (old,))
        cur.execute("INSERT INTO discovery_show_feature_snapshots VALUES(1,%s,'v1','2035-01-01T00:00Z')", (old,))
        return result


@pytest.fixture
def plan(database, decisions):
    with database.cursor() as cur:
        return repair.build_plan(cur, decisions)


def test_merge_holds_relationships_repeat_json_restore_and_reapply(database, plan, tmp_path):
    path = tmp_path / "backup.json"
    with database.cursor() as cur:
        result = repair.repair(cur, plan, path)
        assert len(result["before"]["shows"]) - len(result["after"]["shows"]) == 5
        assert len(result["before"]["tickets"]) - len(result["after"]["tickets"]) == 5
        after = {r["id"]: r for r in result["after"]["shows"]}
        before = {r["id"]: r for r in result["before"]["shows"]}
        for ident in (3789176, 3179550, 3179544):
            assert after[ident] == before[ident]
        target = next(iter(repair.MERGES.values()))
        for table in (
            "saved_shows",
            "sent_notifications",
            "ticket_purchase_click_events",
            "discovery_show_feature_snapshots",
        ):
            assert result["after"][table] == [dict(r, show_id=target) for r in result["before"][table]]
        assert repair.repair(cur, plan)["already_applied"]
        saved = json.loads(Path(str(path) + ".after.json").read_text())
        assert repair.restore(cur, plan, saved)
        assert repair.snapshot(cur) == result["before"]
        assert not repair.restore(cur, plan, saved)
        assert not repair.repair(cur, plan)["already_applied"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(Path(str(path) + ".after.json").stat().st_mode) == 0o600
    assert "after" not in json.loads(path.read_text())


@pytest.mark.parametrize("kind", ["source", "show", "hold", "child", "inventory", "venue"])
def test_before_image_drift_refused(database, plan, kind):
    with database.cursor() as cur:
        queries = {
            "source": "UPDATE scraping_sources SET enabled=false WHERE id=6820",
            "show": "UPDATE shows SET date=date+interval '1 hour' WHERE id=3179527",
            "hold": "UPDATE shows SET description='drift' WHERE id=3179544",
            "child": "UPDATE tickets SET price=99 WHERE show_id=3789152",
            "inventory": "INSERT INTO shows(id,club_id,date) VALUES(99,10970,'2036-12-30T20:00Z')",
            "venue": "UPDATE clubs SET address='changed' WHERE id=10970",
        }
        cur.execute(queries[kind])
        with pytest.raises(ValueError, match="before-image"):
            repair.repair(cur, plan)


@pytest.mark.parametrize("kind", ["slot", "native", "ticket", "user"])
def test_collision_refused_before_writes(database, decisions, kind):
    with database.cursor() as cur:
        if kind == "slot":
            cur.execute(
                "INSERT INTO shows(id,club_id,date,room) VALUES(99,10970,'2036-12-01T23:30Z','18b Corinth Street, Boston, MA')"
            )
        elif kind == "native":
            cur.execute("UPDATE shows SET source_performance_id='same-native' WHERE id=3179527")
            cur.execute("UPDATE shows SET source_performance_id='same-native' WHERE id=3179544")
        elif kind == "ticket":
            cur.execute("UPDATE tickets SET price=19 WHERE show_id=3789152")
        else:
            cur.execute("INSERT INTO saved_shows VALUES(3179527,'user','2035-02-01T00:00Z')")
        before = repair.snapshot(cur)
        with pytest.raises(ValueError, match="collision|conflict"):
            repair.build_plan(cur, decisions)
        assert repair.snapshot(cur) == before


def test_backup_failure_precedes_all_mutations(database, plan, monkeypatch):
    with database.cursor() as cur:
        before = repair.snapshot(cur)

        def fail(*args):
            raise OSError("backup unavailable")

        monkeypatch.setattr(repair, "save_backup", fail)
        with pytest.raises(OSError):
            repair.repair(cur, plan, "/unused")
        assert repair.snapshot(cur) == before


@pytest.mark.parametrize("kind", ["child", "schema", "checksum"])
def test_restore_refuses_drift(database, plan, kind):
    with database.cursor() as cur:
        backup = repair.repair(cur, plan)
        if kind == "child":
            cur.execute("INSERT INTO ticket_purchase_click_events VALUES(2,3179527)")
        elif kind == "schema":
            cur.execute("ALTER TABLE shows ADD COLUMN unknown text")
        else:
            backup["before"]["shows"][0]["description"] = "tampered"
        with pytest.raises(ValueError, match="drift|Schema|checksum"):
            repair.restore(cur, plan, backup)


def test_unknown_child_reference_refused(database, plan):
    with database.cursor() as cur:
        cur.execute("CREATE TEMP TABLE unknown_reference(show_id int REFERENCES shows)")
        with pytest.raises(ValueError, match="foreign keys"):
            repair.repair(cur, plan)


def test_modified_decision_cannot_change_reviewed_after_image(database, plan):
    changed = copy.deepcopy(plan)
    changed["decisions"][0]["patch"]["room"] = "unreviewed room"
    with database.cursor() as cur, pytest.raises(ValueError, match="after-image"):
        repair.repair(cur, changed)
