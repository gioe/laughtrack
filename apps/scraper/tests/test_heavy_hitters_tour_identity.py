"""Guarded tour-label cleanup and repeat-ingestion regressions."""

import copy
import importlib.util
import json
import stat
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from scripts.archive import disposition_heavy_hitters_tour_2026_10_08 as repair

_spec = importlib.util.spec_from_file_location(
    "tour_test_schema", Path(__file__).parent / "scripts/test_repair_seatengine_organizer_venues.py"
)
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
database = _schema.database


@pytest.fixture
def evidence(database):
    with database.cursor() as cur:
        for table in repair.CHILDREN:
            cur.execute(f"DELETE FROM {table}")
        cur.execute("""
            DELETE FROM shows;
            ALTER TABLE shows ADD COLUMN name text;
            ALTER TABLE shows ADD COLUMN last_scraped_by text;
            ALTER TABLE shows ADD COLUMN source_performance_id text;
            ALTER TABLE scraping_sources ADD COLUMN platform text DEFAULT 'seatengine';
            ALTER TABLE scraping_sources ADD COLUMN seatengine_id int DEFAULT 464;
            INSERT INTO clubs(id,name) VALUES(73,'Greenville Comedy Zone');
            INSERT INTO scraping_sources(id,club_id,source_url) VALUES(32,73,'greenvillecomedyzone.com/events');
            CREATE TEMP TABLE comedians(id int PRIMARY KEY,uuid text UNIQUE,name text,visible boolean,
                parent_comedian_id int REFERENCES comedians,block_reason text,block_added_at timestamptz,
                block_added_by text,total_shows int DEFAULT 4);
            ALTER TABLE lineup_items ADD CONSTRAINT lineup_comedian_fk FOREIGN KEY(comedian_id) REFERENCES comedians(uuid);
            CREATE TEMP TABLE favorite_comedians(id int PRIMARY KEY,comedian_id int REFERENCES comedians);
            INSERT INTO comedians(id,uuid,name,visible) VALUES(999,'real-comic','Darren Brand',true);
        """)
        ident = 1936878
        uuid, name = repair.TARGETS[ident]
        cur.execute("INSERT INTO comedians(id,uuid,name,visible) VALUES(%s,%s,%s,true)", (ident, uuid, name))
        cur.execute("INSERT INTO favorite_comedians VALUES(1,%s)", (ident,))
        associations = []
        for i, show_id in enumerate(sorted(repair.SHOW_IDS)):
            url = f"http://greenvillecomedyzone.com/shows/{384861+i}"
            cur.execute(
                "INSERT INTO shows(id,name,club_id,date,show_page_url,last_scraped_by,description) VALUES(%s,'Heavy Hitters of Comedy',73,'2027-04-09T23:00Z',%s,'seatengine','')",
                (show_id, url),
            )
            cur.execute("INSERT INTO lineup_items VALUES(%s,%s,%s,NULL)", (i + 1, show_id, uuid))
            cur.execute("INSERT INTO lineup_items VALUES(%s,%s,'real-comic','host')", (i + 11, show_id))
            cur.execute("INSERT INTO tickets(id,show_id,type,price) VALUES(%s,%s,'GA',20)", (i + 1, show_id))
            cur.execute("INSERT INTO tagged_shows VALUES(%s,1)", (show_id,))
            cur.execute("INSERT INTO saved_shows VALUES(%s,'user','2026-10-01T00:00Z')", (show_id,))
            cur.execute("INSERT INTO sent_notifications VALUES(%s,%s)", (i + 1, show_id))
            cur.execute("INSERT INTO ticket_purchase_click_events VALUES(%s,%s)", (i + 1, show_id))
            cur.execute(
                "INSERT INTO discovery_show_feature_snapshots VALUES(%s,%s,'v1','2026-10-01T00:00Z')", (i + 1, show_id)
            )
            associations.append(
                dict(
                    comedian_id=ident,
                    uuid=uuid,
                    comedian_name=name,
                    show_id=show_id,
                    show_name="Heavy Hitters of Comedy",
                    date="2027-04-09T23:00:00+00:00",
                    show_page_url=url,
                    club_id=73,
                    club_name="Greenville Comedy Zone",
                    last_scraped_by="seatengine",
                    source_performance_id=None,
                    description="",
                    sources=[
                        dict(
                            source_id=32,
                            platform="seatengine",
                            seatengine_id=464,
                            source_url="greenvillecomedyzone.com/events",
                        )
                    ],
                )
            )
        cur.execute("SELECT to_jsonb(t) FROM comedians t WHERE id=%s", (ident,))
        original = cur.fetchone()[0]
        cur.execute("SELECT to_jsonb(t) FROM lineup_items t WHERE comedian_id=%s", (uuid,))
        identities = [dict(comedian=original, lineups=[r[0] for r in cur.fetchall()])]
    return identities, associations


def test_apply_preserves_references_idempotency_and_exact_restore(database, evidence, tmp_path):
    backup = tmp_path / "private.json"
    with database.cursor() as cur:
        result = repair.disposition(cur, *evidence, backup)
        assert result["after"]["target_lineups"] == []
        assert len(result["after"]["lineup_items"]) == 4
        repair.verify_preservation(result["before"], result["after"], repair.validate_evidence(*evidence))
        assert result["after"]["other_references"] == result["before"]["other_references"]
        assert repair.disposition(cur, *evidence)["already_applied"]
        recovery = json.loads(Path(str(backup) + ".after.json").read_text())
        assert repair.rollback(cur, recovery)
        assert not repair.rollback(cur, recovery)
        assert not repair.disposition(cur, *evidence)["already_applied"]
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    assert stat.S_IMODE(Path(str(backup) + ".after.json").stat().st_mode) == 0o600
    assert "after" not in json.loads(backup.read_text())


@pytest.mark.parametrize(
    "drift", ["identity", "canonical", "role", "association", "show_url", "source", "historical_after", "lineup_fk"]
)
def test_refuses_drift_before_writes_or_rollback(database, evidence, drift):
    with database.cursor() as cur:
        if drift == "historical_after":
            result = repair.disposition(cur, *evidence)
            cur.execute("DELETE FROM favorite_comedians")
            with pytest.raises(ValueError, match="refusing rollback"):
                repair.rollback(cur, result)
            return
        changes = {
            "identity": "UPDATE comedians SET name='Other' WHERE id=1936878",
            "canonical": "UPDATE comedians SET parent_comedian_id=999 WHERE id=1936878",
            "role": "UPDATE lineup_items SET role='headliner' WHERE id=1",
            "association": "INSERT INTO lineup_items VALUES(99,5775541,'real-comic-2',NULL)",
            "show_url": "UPDATE shows SET show_page_url='https://wrong.example' WHERE id=5775541",
            "source": "UPDATE scraping_sources SET seatengine_id=999 WHERE id=32",
            "lineup_fk": "CREATE TEMP TABLE lineup_history(show_id int,comedian_id text,FOREIGN KEY(show_id,comedian_id) REFERENCES lineup_items ON DELETE CASCADE)",
        }
        if drift == "association":
            cur.execute("INSERT INTO shows(id) VALUES(99)")
            cur.execute("INSERT INTO lineup_items VALUES(99,99,%s,NULL)", (repair.TARGETS[1936878][0],))
        else:
            cur.execute(changes[drift])
        with pytest.raises(ValueError):
            repair.disposition(cur, *evidence)
        cur.execute("SELECT visible FROM comedians WHERE id=1936878")
        assert cur.fetchone()[0]


def test_backup_failure_precedes_writes(database, evidence, monkeypatch):
    def fail(*args):
        raise OSError("Recovery unavailable")

    monkeypatch.setattr(repair, "save_backup", fail)
    with database.cursor() as cur, pytest.raises(OSError):
        repair.disposition(cur, *evidence, backup_path="/unused")
    with database.cursor() as cur:
        cur.execute("SELECT count(*) FROM lineup_items")
        assert cur.fetchone()[0] == 8


@pytest.mark.parametrize("label_only", [False, True])
def test_repeat_ingestion_uses_real_hidden_name_filter_and_preserves_real_performers(label_only):
    from laughtrack.core.entities.comedian.handler import ComedianHandler
    from laughtrack.core.entities.comedian.model import Comedian
    from laughtrack.core.entities.show.handler import ShowHandler
    from sql.comedian_queries import ComedianQueries

    comic_handler = ComedianHandler.__new__(ComedianHandler)

    def query(sql, params, return_results=True):
        if sql == ComedianQueries.GET_HIDDEN_COMEDIAN_NAMES:
            assert "heavy hitters tour" in params[0]
            return [{"name": "Heavy Hitters Tour"}]
        assert sql == ComedianQueries.GET_DENIED_NAMES
        return []

    comic_handler.execute_with_cursor = MagicMock(side_effect=query)
    handler = ShowHandler.__new__(ShowHandler)
    handler.lineup_handler = MagicMock()
    handler.lineup_handler.get_lineup.return_value = {}
    handler.lineup_handler.get_comedians_from_show_names.return_value = {}
    handler.lineup_handler.batch_update_lineups.return_value = (4, 0)
    handler.comedian_handler = MagicMock()
    handler.comedian_handler._filter_denied_comedians.side_effect = comic_handler._filter_denied_comedians
    handler.comedian_handler._filter_false_positive_comedians.side_effect = list
    handler.comedian_handler.insert_comedians.return_value = []
    handler.calculate_and_update_popularity = MagicMock()
    names = [] if label_only else ["Darren Brand", "Marvin Hunter", "Burpie", "GiGi LeFlair", "Heavy Hitters Tour Jr"]
    for _ in range(2):
        show = SimpleNamespace(
            id=5775541,
            name="Heavy Hitters of Comedy",
            club_id=73,
            date="2027-04-09T23:00:00+00:00",
            show_page_url="http://greenvillecomedyzone.com/shows/384861",
            tickets=[{"type": "GA", "price": 20, "purchase_url": "https://example.com/ticket"}],
            description="Tour bill with several performers",
            lineup=[Comedian("Heavy Hitters Tour"), *[Comedian(n) for n in names]],
        )
        protected = copy.deepcopy({key: value for key, value in vars(show).items() if key != "lineup"})
        handler.comedian_handler.insert_comedians.reset_mock()
        handler.update_show_lineups([show])
        assert {key: value for key, value in vars(show).items() if key != "lineup"} == protected
        assert [c.name for c in show.lineup] == names
        persisted = handler.lineup_handler.batch_update_lineups.call_args.args[0]
        assert [c.name for c in persisted[0].lineup] == names
        if label_only:
            handler.comedian_handler.insert_comedians.assert_not_called()
        else:
            assert all(
                c.name != "Heavy Hitters Tour" for c in handler.comedian_handler.insert_comedians.call_args.args[0]
            )
    assert comic_handler.execute_with_cursor.call_count == 4
