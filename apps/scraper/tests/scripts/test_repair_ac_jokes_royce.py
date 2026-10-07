"""Real PostgreSQL, rollback-isolated coverage for the exact Royce cohort."""

import copy
import importlib.util
import json
from pathlib import Path
import stat

import pytest
from scripts.core import repair_ac_jokes_royce as repair

_spec = importlib.util.spec_from_file_location(
    "royce_repair_schema", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
database = _schema.database


@pytest.fixture
def plan(database):
    native = []
    with database.cursor() as cur:
        for table in repair.CHILDREN:
            cur.execute(f"DELETE FROM {table}")
        cur.execute("DELETE FROM shows; DELETE FROM scraping_sources; DELETE FROM clubs")
        for ident in sorted(repair.PROTECTED_CLUBS):
            cur.execute("INSERT INTO clubs(id,name) VALUES(%s,%s)", (ident, f"Protected {ident}"))
        cur.execute("INSERT INTO production_companies(id,name,slug) VALUES(46,'AC Jokes','ac-jokes')")
        metadata = dict(
            keep=True,
            task_4110_repair="prior",
            wix_venue_routes=dict(source_id=291, component_id="comp-lpdlygbr", producer_id=46, routes=[]),
        )
        cur.execute(
            "INSERT INTO scraping_sources VALUES(291,412,true,%s,'https://www.acjokes.com')", (json.dumps(metadata),)
        )
        for index, (ident, native_id) in enumerate(
            ((ident, native_id) for native_id, ident in repair.NATIVE_SHOWS.items())
        ):
            date = f"2036-10-{17+index}T00:30:00+00:00"
            slug = f"native-{ident}"
            cur.execute(
                "INSERT INTO shows(id,club_id,date,show_page_url,room) VALUES(%s,412,%s,%s,%s)",
                (ident, date, "https://www.acjokes.com/event-details/" + slug, repair.LOCATION["name"]),
            )
            cur.execute("INSERT INTO tickets(id,show_id,type,price) VALUES(%s,%s,'GA',25)", (ident, ident))
            cur.execute("INSERT INTO ticket_purchase_click_events(id,show_id) VALUES(%s,%s)", (ident, ident))
            native.append(
                dict(
                    id=native_id,
                    slug=slug,
                    scheduling=dict(config=dict(startDate=date, scheduleTbd=False)),
                    location=dict(
                        name=repair.LOCATION["name"],
                        type=0,
                        tbd=False,
                        fullAddress=dict(
                            country="US",
                            subdivision="NJ",
                            city="Atlantic City",
                            postalCode="08401",
                            streetAddress=dict(number="2801", name="Pacific Avenue", apt="Suite 308"),
                        ),
                    ),
                )
            )
        for index, club in enumerate(sorted(repair.PROTECTED_CLUBS)):
            cur.execute(
                "INSERT INTO shows(id,club_id,date,show_page_url) VALUES(%s,%s,'2036-01-01T20:00Z','https://held.example')",
                (index + 1, club),
            )
        return dict(
            task_id=4131,
            venue=dict(fields=copy.deepcopy(repair.VENUE_FIELDS)),
            native_events=native,
            before=repair.snapshot(cur),
        )


def test_moves_exact_three_preserves_all_children_and_is_idempotent(database, plan, tmp_path):
    path = tmp_path / "recovery.json"
    with database.cursor() as cur:
        result = repair.repair(cur, plan, path)
        assert len(result["after"]["shows"]) == 6
        for table in repair.CHILDREN:
            assert result["before"][table] == result["after"][table]
        for row in result["after"]["shows"]:
            if row["id"] in repair.MOVE_IDS:
                assert row["club_id"] == result["destination_id"]
                assert row["production_company_id"] == row["scraped_by_organizer_id"] == 46
        metadata = result["after"]["scraping_sources"][0]["metadata"]
        assert metadata["keep"] and metadata["task_4110_repair"] == "prior"
        assert metadata["wix_venue_routes"]["routes"][-1]["location"]["street_apt"] == "Suite 308"
        assert repair.repair(cur, plan)["already_applied"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert "after" not in json.loads(path.read_text())
    assert Path(str(path) + ".after.json").exists()


@pytest.mark.parametrize("drift", ["show", "child", "source", "new_inventory", "offsite", "schema", "venue_identity"])
def test_drift_refused_before_writes(database, plan, drift):
    with database.cursor() as cur:
        if drift == "show":
            cur.execute("UPDATE shows SET room='Elsewhere' WHERE id=7898492")
        elif drift == "child":
            cur.execute("UPDATE tickets SET price=99")
        elif drift == "source":
            cur.execute("UPDATE scraping_sources SET enabled=false")
        elif drift == "new_inventory":
            cur.execute("INSERT INTO shows(id,club_id) VALUES(99,412)")
        elif drift == "offsite":
            cur.execute("UPDATE shows SET room='changed' WHERE club_id=90822")
        elif drift == "schema":
            cur.execute("CREATE TEMP TABLE unexpected(show_id int REFERENCES shows)")
        else:
            cur.execute("INSERT INTO clubs(name,address) VALUES('The Royce Social Hall','Wrong Street')")
        with pytest.raises(ValueError):
            repair.repair(cur, plan)
        cur.execute("SELECT club_id FROM shows WHERE id=7898492")
        assert cur.fetchone()[0] == 412


@pytest.mark.parametrize(
    "change", ["suite", "date", "slug", "native_id", "swapped_ids", "address_conflict", "tbd", "venue"]
)
def test_unverified_plan_rejected(database, plan, change):
    if change == "suite":
        plan["native_events"][0]["location"]["fullAddress"]["streetAddress"]["apt"] = "Suite 304"
    elif change == "date":
        plan["native_events"][0]["scheduling"]["config"]["startDate"] = "2036-01-01T20:00Z"
    elif change == "slug":
        plan["native_events"][0]["slug"] = "different"
    elif change == "native_id":
        plan["native_events"][0]["id"] = "unknown"
    elif change == "swapped_ids":
        a, b = plan["native_events"][:2]
        a["id"], b["id"] = b["id"], a["id"]
    elif change == "address_conflict":
        loc = plan["native_events"][0]["location"]
        loc["address"] = "2801 Pacific"
        loc["fullAddress"]["formattedAddress"] = "Other street"
    elif change == "tbd":
        plan["native_events"][0]["scheduling"]["config"]["scheduleTbd"] = True
    else:
        plan["venue"]["fields"]["address"] = "2801 Pacific Avenue"
    with database.cursor() as cur, pytest.raises(ValueError):
        repair.repair(cur, plan)


def test_backup_failure_prevents_writes(database, plan, monkeypatch):
    def fail(*args):
        raise OSError("backup unavailable")

    monkeypatch.setattr(repair, "save_backup", fail)
    with database.cursor() as cur:
        with pytest.raises(OSError):
            repair.repair(cur, plan, "/unused")
        cur.execute("SELECT count(*) FROM clubs WHERE name='The Royce Social Hall'")
        assert cur.fetchone()[0] == 0


def test_existing_destination_collision_refused(database, plan):
    with database.cursor() as cur:
        ids = {}
        repair.insert_definitions(cur, "clubs", {"royce": plan["venue"]}, ids)
        destination = ids["royce"]
        plan["venue"]["id"] = destination
        cur.execute("INSERT INTO shows(id,club_id,date) SELECT 99,%s,date FROM shows WHERE id=7898492", (destination,))
        plan["before"] = repair.snapshot(cur, destination)
        with pytest.raises(ValueError, match="occupies"):
            repair.repair(cur, plan)


def test_idempotent_repeat_rejects_later_child_drift(database, plan):
    with database.cursor() as cur:
        repair.repair(cur, plan)
        cur.execute("UPDATE tickets SET price=99")
        with pytest.raises(ValueError, match="drift"):
            repair.repair(cur, plan)
