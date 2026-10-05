"""Execute national discovery SQL against temporary PostgreSQL tables."""

import os

import psycopg2
from psycopg2.extras import Json, RealDictCursor
import pytest

from sql.club_queries import ClubQueries


@pytest.fixture
def database():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL required for SeatEngine quarantine regression")
    connection = psycopg2.connect(dsn)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TEMP TABLE clubs (
                    id serial PRIMARY KEY, name text UNIQUE, address text, website text,
                    visible boolean, zip_code text, city text, state text,
                    phone_number text, popularity integer, timezone text,
                    latitude double precision, longitude double precision
                );
                CREATE TEMP TABLE scraping_sources (
                    club_id integer, platform text, scraper_key text, seatengine_id integer,
                    source_url text, priority integer, enabled boolean, metadata jsonb,
                    UNIQUE(club_id, platform, priority)
                );
            """)
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.parametrize(
    "enabled,metadata,protected",
    [
        (False, {"task_4070_disposition": {"reason": "multi_location_promoter_wrong_physical_identity"}}, True),
        (False, {"task_9999_disposition": {}}, True),
        (False, {"task_4070_note": {}}, False),
        (True, {"task_4070_disposition": {}}, False),
        (True, {}, False),
    ],
)
def test_national_refresh_preserves_disposition_quarantine(database, enabled, metadata, protected):
    with database.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""INSERT INTO clubs (id,name,address,visible,zip_code)
                          VALUES (855,'Laugh Tonight Comedy','',false,'')""")
        cursor.execute(
            """INSERT INTO scraping_sources VALUES
            (855,'seatengine','seatengine',424,'https://example.com',0,%s,%s)""",
            (enabled, Json(metadata)),
        )
        for _ in range(2):
            cursor.execute(
                ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE,
                (
                    "Laugh Tonight Comedy",
                    "Unverified account address",
                    "https://example.com",
                    "47305",
                    "Muncie",
                    "IN",
                    424,
                    "https://example.com",
                ),
            )
            result = cursor.fetchone()
            assert result is not None
            assert result["id"] == 855
            assert (result["address"], result["visible"], result["latitude"], result["longitude"]) == (
                "",
                False,
                None,
                None,
            )
            assert (result["zip_code"], result["city"], result["state"]) == (
                ("", None, None) if protected else ("47305", "Muncie", "IN")
            )
            cursor.execute("SELECT enabled,metadata FROM scraping_sources WHERE club_id=855")
            source = cursor.fetchone()
            assert source["enabled"] is (False if protected else True)
            assert source["metadata"] == metadata


def test_new_venue_and_known_zip_still_supported(database):
    with database.cursor(cursor_factory=RealDictCursor) as cursor:
        for incoming_zip in ("02116", "10001"):
            cursor.execute(
                ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE,
                (
                    "Physical venue",
                    "123 Main St",
                    "https://example.com",
                    incoming_zip,
                    "Boston",
                    "MA",
                    123,
                    "https://example.com",
                ),
            )
            result = cursor.fetchone()
            assert result["zip_code"] == "02116"
            assert result["city"] == "Boston"
            assert result["visible"] is True
