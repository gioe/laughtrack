"""Real PostgreSQL checks for preservation, drift refusal and rollback."""

import json
import os
import stat

import psycopg2
import pytest

from scripts.archive import quarantine_district_dome_2026_10_06 as repair
from sql.club_queries import ClubQueries


@pytest.fixture
def database():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL required")
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TEMP TABLE clubs(id serial PRIMARY KEY,name text UNIQUE,address text,website text,
                  visible boolean,club_type text,description text,status text,zip_code text,city text,state text,
                  timezone text,google_place_id text,phone_number text,popularity int);
                CREATE TEMP TABLE scraping_sources(id serial PRIMARY KEY,club_id int REFERENCES clubs,
                  platform text,scraper_key text,seatengine_id int,source_url text,priority int DEFAULT 0,
                  enabled boolean,metadata jsonb,updated_at timestamptz DEFAULT now(),UNIQUE(club_id,platform,priority));
                CREATE TEMP TABLE shows(id int PRIMARY KEY,club_id int REFERENCES clubs,name text,date timestamptz,
                  show_page_url text,is_cancelled boolean);
                CREATE TEMP TABLE tickets(id int PRIMARY KEY,show_id int REFERENCES shows,price numeric);
                CREATE TEMP TABLE tagged_shows(show_id int REFERENCES shows,tag_id int,PRIMARY KEY(show_id,tag_id));
                CREATE TEMP TABLE ticket_purchase_click_events(id int PRIMARY KEY,show_id int REFERENCES shows,
                  club_id int REFERENCES clubs,anonymous_visitor_id text);
                CREATE TEMP TABLE scraper_runs(id int PRIMARY KEY,club_id int REFERENCES clubs,status text);
                INSERT INTO clubs(id,name,address,website,visible,club_type,description,status,zip_code,city,state,
                  timezone,google_place_id) VALUES (554,'District Dome','21001 N Tatum Blvd, Phoenix, AZ 85050, USA',
                  'https://www.districtdome.com',true,'comedy_club','Carry On at Wren & Wolf','active','85050',
                  'Phoenix','AZ','America/Phoenix','ChIJ_y7Ne-BwK4cR7wtdsKrbYgw'),
                  (600,'Carry On','Other address','https://carryonphx.com',false,'non_comedy','Other description',
                  'active','85004','Phoenix','AZ','America/Phoenix','other-place');
                INSERT INTO scraping_sources(id,club_id,platform,scraper_key,seatengine_id,source_url,enabled,metadata)
                  VALUES(87,554,'seatengine','seatengine',534,'https://www.districtdome.com',true,'{"keep":true}'),
                  (336,600,'seatengine','seatengine',584,'https://carryonphx.com',false,'{"task_4066_disposition":{}}');
                INSERT INTO shows VALUES(522028,554,'Carry On Airlines: Flight 111824','2027-06-05T00:30Z',
                  'https://www.districtdome.com/shows/291128',false);
                INSERT INTO tickets SELECT n,522028,n*10 FROM generate_series(1,11) n;
                INSERT INTO tagged_shows SELECT 522028,n FROM generate_series(1,3) n;
                INSERT INTO ticket_purchase_click_events SELECT n,522028,554,'visitor-'||n FROM generate_series(1,28) n;
                INSERT INTO scraper_runs VALUES(1,554,'success');
            """)
        yield conn
    finally:
        conn.rollback()
        conn.close()


def capture(cur):
    return repair.snapshot(cur, repair.relationships(cur))


def test_preserve_idempotence_private_backup_and_exact_rollback(database, tmp_path):
    backup = tmp_path / "backup.json"
    with database.cursor() as cur:
        before = capture(cur)
        other_before = repair.rows(cur, "clubs", "id", [600]), repair.rows(cur, "scraping_sources", "id", [336])
        result = repair.repair(cur, before, backup)
        after = result["after"]
        assert not result["already_applied"]
        assert after["shows"] == before["shows"]
        assert after["references"] == before["references"]
        assert not after["club"][0]["visible"]
        assert after["club"][0]["club_type"] == "non_comedy"
        assert after["club"][0]["zip_code"] == "85050"
        assert not after["sources"][0]["enabled"]
        assert after["sources"][0]["metadata"]["keep"]
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600
        assert repair.repair(cur, before)["already_applied"]
        assert repair.rollback(cur, json.loads(backup.read_text()))
        assert repair.normalized(capture(cur)) == repair.normalized(before)
        assert not repair.rollback(cur, json.loads(backup.read_text()))
        assert other_before == (
            repair.rows(cur, "clubs", "id", [600]),
            repair.rows(cur, "scraping_sources", "id", [336]),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE clubs SET zip_code='85054' WHERE id=554",
        "UPDATE scraping_sources SET seatengine_id=999 WHERE id=87",
        "UPDATE shows SET date=date+interval '1 day' WHERE id=522028",
        "UPDATE tickets SET price=999 WHERE id=1",
        "INSERT INTO ticket_purchase_click_events VALUES(29,522028,554,'new')",
        "UPDATE scraper_runs SET status='failure' WHERE id=1",
    ],
)
def test_before_image_drift_refuses_all_writes(database, mutation):
    with database.cursor() as cur:
        before = capture(cur)
        cur.execute(mutation)
        changed = capture(cur)
        with pytest.raises(ValueError, match="Before-image drift"):
            repair.repair(cur, before)
        assert capture(cur) == changed


def test_backup_failure_prevents_mutation(database, tmp_path):
    backup = tmp_path / "existing.json"
    backup.write_text("do not replace")
    with database.cursor() as cur:
        before = capture(cur)
        with pytest.raises(FileExistsError):
            repair.repair(cur, before, backup)
        assert capture(cur) == before
        assert backup.read_text() == "do not replace"


def test_rollback_refuses_new_references(database, tmp_path):
    backup = tmp_path / "backup.json"
    with database.cursor() as cur:
        repair.repair(cur, capture(cur), backup)
        cur.execute("INSERT INTO scraper_runs VALUES(2,554,'new')")
        after = capture(cur)
        with pytest.raises(ValueError, match="After-state drift"):
            repair.rollback(cur, json.loads(backup.read_text()))
        assert capture(cur) == after


def test_actual_discovery_sql_retains_quarantine_postal_fix_and_inventory(database):
    with database.cursor() as cur:
        after = repair.repair(cur, capture(cur))["after"]
        for _ in range(2):
            cur.execute(
                ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE,
                (
                    "District Dome",
                    "Wrong upstream address",
                    "https://www.districtdome.com",
                    "85054",
                    "Phoenix",
                    "AZ",
                    534,
                    "https://www.districtdome.com",
                ),
            )
            assert cur.fetchone() is not None
            assert repair.normalized(capture(cur)) == repair.normalized(after)
