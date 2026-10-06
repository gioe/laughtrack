"""PostgreSQL activation tests use private temporary tables and never production."""

import importlib.util
import json
import stat
from pathlib import Path

import pytest

from scripts.core import activate_comedy_shoppe_punchup as activation

_spec = importlib.util.spec_from_file_location(
    "seatengine_activation_test_schema", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
database = _schema.database


@pytest.fixture
def plan(database):
    with database.cursor() as cur:
        cur.execute("""
            ALTER TABLE shows ADD COLUMN name text;
            ALTER TABLE scraping_sources ADD COLUMN platform text;
            ALTER TABLE scraping_sources ADD COLUMN scraper_key text;
            ALTER TABLE scraping_sources ADD COLUMN priority int DEFAULT 0;
            CREATE TEMP TABLE source_targets(id int PRIMARY KEY,name text,metadata jsonb);
            INSERT INTO source_targets VALUES(1,'Existing platform target','{}');
            INSERT INTO clubs(id,name,address) VALUES(327,'The Comedy Shoppe','Legacy organizer address');
            UPDATE shows SET club_id=327;
            DELETE FROM scraping_sources;
            INSERT INTO scraping_sources(id,club_id,enabled,metadata,source_url,platform,scraper_key)
                VALUES(617,327,true,'{"preserve":true}','https://old.example/?secure_code=private','showslinger','show_slinger');
        """)
        cur.execute("SELECT to_jsonb(t) FROM clubs t WHERE id=327")
        organizer = cur.fetchone()[0]
        cur.execute("SELECT to_jsonb(t) FROM scraping_sources t WHERE id=617")
        source = cur.fetchone()[0]
    clubs = {
        f"venue-{i}": {
            "fields": {
                "name": f"Physical Venue {i}",
                "address": f"{i} Main St",
                "city": "Newtown",
                "state": "PA",
                "timezone": "America/New_York",
                "website": "",
            }
        }
        for i in range(7)
    }
    routes = {f"native-{i}": {"club_id": {"$club": f"venue-{i}"}} for i in range(7)}
    return {
        "task_id": 4112,
        "organizer": {"id": 327, "before_hash": activation.digest(organizer)},
        "source": {
            "id": 617,
            "before_hash": activation.digest(source),
            "patch": {
                "platform": "custom",
                "scraper_key": "the_comedy_shoppe",
                "source_url": activation.SOURCE_URL,
                "metadata": {
                    "preserve": True,
                    "punchup_venue_routes": {
                        "source_id": 617,
                        "page_id": activation.PAGE_ID,
                        "slug": "comedyshoppe",
                        "producer_id": {"$producer": "comedy-shoppe"},
                        "routes": routes,
                    },
                },
            },
        },
        "clubs": clubs,
        "producers": {"comedy-shoppe": {"fields": {"name": "The Comedy Shoppe", "slug": "the-comedy-shoppe"}}},
        "duplicate_check": {
            "urls": ["https://event.tixologi.com/event/123/tickets"],
            "events": [{"name": "Reviewed performance", "date": "2036-12-01T20:00:00-05:00", "venue": "venue-0"}],
        },
    }


def test_activation_preserves_history_and_every_existing_relationship(database, plan, tmp_path):
    backup = tmp_path / "private.json"
    with database.cursor() as cur:
        result = activation.activate(cur, plan, backup)
        assert len(result["clubs"]) == 7
        for table in ("shows", *activation.CHILDREN, "source_targets"):
            assert result["before"][table] == result["after"][table]
        source = result["after"]["scraping_sources"][0]
        assert (source["club_id"], source["enabled"], source["priority"]) == (327, True, 0)
        assert source["platform"] == "custom"
        assert source["scraper_key"] == "the_comedy_shoppe"
        assert source["metadata"][activation.MARKER]["previous_source"] == result["before"]["scraping_sources"][0]
        assert len(result["after"]["production_company_venues"]) == 7
        assert result["after"]["destination_sources"] == []
        assert activation.activate(cur, plan)["already_applied"]
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    assert "after" not in json.loads(backup.read_text())
    assert "secure_code" not in json.dumps(plan)


@pytest.mark.parametrize("conflict", ["source", "organizer", "url", "ticket_url", "title_time", "new_fk"])
def test_activation_rejects_changed_state_and_existing_inventory(database, plan, conflict):
    with database.cursor() as cur:
        if conflict == "source":
            cur.execute("UPDATE scraping_sources SET priority=1")
        elif conflict == "organizer":
            cur.execute("UPDATE clubs SET address='changed' WHERE id=327")
        elif conflict == "url":
            cur.execute("UPDATE shows SET show_page_url=%s WHERE id=10", (plan["duplicate_check"]["urls"][0],))
        elif conflict == "ticket_url":
            cur.execute("UPDATE tickets SET purchase_url=%s WHERE id=1", (plan["duplicate_check"]["urls"][0],))
        elif conflict == "title_time":
            event = plan["duplicate_check"]["events"][0]
            cur.execute("UPDATE shows SET name=%s,date=%s WHERE id=10", (event["name"], event["date"]))
        else:
            cur.execute("CREATE TEMP TABLE unknown_relationship(show_id int REFERENCES shows)")
        with pytest.raises(ValueError):
            activation.activate(cur, plan)
        cur.execute("SELECT count(*) FROM production_companies")
        assert cur.fetchone()[0] == 0


def test_recovery_failure_precedes_inserts(database, plan, monkeypatch):
    def fail(*args):
        raise OSError("Recovery unavailable")

    monkeypatch.setattr(activation, "save_backup", fail)
    with database.cursor() as cur, pytest.raises(OSError):
        activation.activate(cur, plan, "/unused")
    with database.cursor() as cur:
        cur.execute("SELECT count(*) FROM production_companies")
        assert cur.fetchone()[0] == 0
