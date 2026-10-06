"""Real PostgreSQL preservation, drift and rollback coverage for TASK-4115."""

import importlib.util
import json
import stat
from pathlib import Path

import pytest

from scripts.archive import disposition_whiplash_performer_labels_2026_10_06 as repair

_spec = importlib.util.spec_from_file_location(
    "performer_test_schema", Path(__file__).with_name("test_repair_seatengine_organizer_venues.py")
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
            ALTER TABLE scraping_sources ADD COLUMN seatengine_id int DEFAULT 650;
            CREATE TEMP TABLE comedians(id int PRIMARY KEY,uuid text UNIQUE,name text,visible boolean,
                parent_comedian_id int REFERENCES comedians,block_reason text,block_added_at timestamptz,
                block_added_by text,total_shows int DEFAULT 123);
            ALTER TABLE lineup_items ADD CONSTRAINT lineup_comedian_fk FOREIGN KEY(comedian_id) REFERENCES comedians(uuid);
            CREATE TEMP TABLE favorite_comedians(id int PRIMARY KEY,comedian_id int REFERENCES comedians);
            INSERT INTO comedians(id,uuid,name,visible) VALUES(999,'real-comic','Real Person',true);
        """)
        associations = []
        originals = []
        show_id = 1
        for ident, (uuid, name) in repair.TARGETS.items():
            hidden = ident == 518570
            cur.execute(
                "INSERT INTO comedians(id,uuid,name,visible,block_reason,block_added_at,block_added_by) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    ident,
                    uuid,
                    name,
                    not hidden,
                    "not a comic" if hidden else None,
                    "2026-07-01T12:00Z" if hidden else None,
                    "original-user" if hidden else None,
                ),
            )
            cur.execute("INSERT INTO favorite_comedians VALUES(%s,%s)", (ident, ident))
            for _ in range(38 if ident == 2447993 else 1):
                cur.execute(
                    "INSERT INTO shows(id,name,club_id,date,show_page_url,last_scraped_by,description) VALUES(%s,%s,600,'2036-01-01T20:00Z',%s,'seatengine','')",
                    (show_id, name, f"https://example.com/shows/{show_id}"),
                )
                cur.execute("INSERT INTO lineup_items VALUES(%s,%s,%s,NULL)", (show_id, show_id, uuid))
                cur.execute("INSERT INTO lineup_items VALUES(%s,%s,'real-comic','host')", (1000 + show_id, show_id))
                cur.execute("INSERT INTO tickets(id,show_id,type,price) VALUES(%s,%s,'GA',20)", (show_id, show_id))
                associations.append(
                    dict(
                        comedian_id=ident,
                        uuid=uuid,
                        comedian_name=name,
                        show_id=show_id,
                        show_name=name,
                        date="2036-01-01T20:00:00+00:00",
                        show_page_url=f"https://example.com/shows/{show_id}",
                        club_id=600,
                        club_name="Account",
                        last_scraped_by="seatengine",
                        source_performance_id=None,
                        description="",
                        sources=[
                            dict(
                                source_id=259,
                                platform="seatengine",
                                seatengine_id=650,
                                source_url="https://example.com",
                            )
                        ],
                    )
                )
                show_id += 1
            cur.execute("SELECT to_jsonb(t) FROM comedians t WHERE id=%s", (ident,))
            original = cur.fetchone()[0]
            cur.execute("SELECT to_jsonb(t) FROM lineup_items t WHERE comedian_id=%s", (uuid,))
            originals.append(dict(comedian=original, lineups=[row[0] for row in cur.fetchall()]))
    return originals, associations


def test_hide_detach_preserve_restore_and_reapply(database, evidence, tmp_path):
    identities, associations = evidence
    backup = tmp_path / "private.json"
    with database.cursor() as cur:
        result = repair.disposition(cur, identities, associations, backup)
        assert len(result["before"]["target_lineups"]) == 40
        assert result["after"]["target_lineups"] == []
        assert len(result["after"]["lineup_items"]) == 40
        assert result["after"]["tickets"] == result["before"]["tickets"]
        assert result["after"]["real_comedians"] == result["before"]["real_comedians"]
        assert result["after"]["other_references"] == result["before"]["other_references"]
        summer = lambda state: next(row for row in state["comedians"] if row["id"] == 518570)
        assert summer(result["after"]) == summer(result["before"])
        assert repair.disposition(cur, identities, associations)["already_applied"]
        assert repair.rollback(cur, result) is True
        assert repair.rollback(cur, result) is False
        assert not repair.disposition(cur, identities, associations)["already_applied"]
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    assert "after" not in json.loads(backup.read_text())


@pytest.mark.parametrize(
    "drift", ["association", "role", "identity", "canonical", "show_url", "source", "favorite_after"]
)
def test_drift_refused(database, evidence, drift):
    identities, associations = evidence
    with database.cursor() as cur:
        if drift == "favorite_after":
            result = repair.disposition(cur, identities, associations)
            cur.execute("DELETE FROM favorite_comedians WHERE id=518570")
            with pytest.raises(ValueError, match="refusing rollback"):
                repair.rollback(cur, result)
            return
        if drift == "association":
            cur.execute("INSERT INTO shows(id) VALUES(99)")
            cur.execute("INSERT INTO lineup_items VALUES(99,99,%s,NULL)", (repair.TARGETS[2353268][0],))
        elif drift == "role":
            cur.execute("UPDATE lineup_items SET role='headliner' WHERE id=1")
        elif drift == "identity":
            cur.execute("UPDATE comedians SET name='Different identity' WHERE id=2353268")
        elif drift == "canonical":
            cur.execute("UPDATE comedians SET parent_comedian_id=999 WHERE id=2353268")
        elif drift == "show_url":
            cur.execute("UPDATE shows SET show_page_url='https://wrong.example' WHERE id=1")
        else:
            cur.execute("UPDATE scraping_sources SET seatengine_id=999")
        with pytest.raises(ValueError):
            repair.disposition(cur, identities, associations)
        cur.execute("SELECT visible FROM comedians WHERE id=2353268")
        assert cur.fetchone()[0] is True


def test_backup_failure_precedes_disposition(database, evidence, monkeypatch):
    def fail(*args):
        raise OSError("Recovery unavailable")

    monkeypatch.setattr(repair, "save_backup", fail)
    with database.cursor() as cur, pytest.raises(OSError):
        repair.disposition(cur, *evidence, backup_path="/unused")
    with database.cursor() as cur:
        cur.execute("SELECT count(*) FROM lineup_items")
        assert cur.fetchone()[0] == 80
