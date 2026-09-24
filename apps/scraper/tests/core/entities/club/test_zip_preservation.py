"""Execute the portable metadata clauses in an isolated in-memory SQL database.

The production queries wrap these clauses in PostgreSQL source-registration CTEs.
Extract only their club-update clauses so this regression runs without credentials
or touching production; COALESCE, NULLIF, TRIM and UPSERT have shared semantics.
"""

import re
import sqlite3

import pytest

from sql.club_queries import ClubQueries

QUERIES = [
    ClubQueries.UPSERT_CLUB_BY_EVENTBRITE_VENUE,
    ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE,
    ClubQueries.UPSERT_CLUB_BY_SEATENGINE_V3_VENUE,
    ClubQueries.UPSERT_CLUB_BY_TICKETMASTER_VENUE,
    ClubQueries.UPSERT_DISCOVERED_VENUE,
]
PATHS = [(query, "name") for query in QUERIES] + [(ClubQueries.UPSERT_CLUB_BY_TICKETMASTER_VENUE, "source")]


def _update_zip(query, route, existing, incoming):
    with sqlite3.connect(":memory:") as db:
        db.execute("""CREATE TABLE clubs (
            name TEXT UNIQUE, zip_code TEXT, address TEXT, website TEXT,
            timezone TEXT, city TEXT, state TEXT, club_type TEXT
        )""")
        # These tests exercise metadata updates for an already verified venue.
        # Ticketmaster name conflicts intentionally refuse unknown geography.
        db.execute("INSERT INTO clubs (name, zip_code, city, state) VALUES ('Venue', ?, 'Boston', 'MA')", (existing,))
        if route == "name":
            conflict = re.search(r"ON CONFLICT \(name\) DO UPDATE SET(.*?)RETURNING", query, re.S).group(1)
            db.execute(
                "INSERT INTO clubs (name, zip_code, city, state) VALUES ('Venue', ?, 'Boston', 'MA') "
                "ON CONFLICT (name) DO UPDATE SET " + conflict,
                (incoming,),
            )
        else:
            updates = re.search(r"UPDATE clubs c\s+SET(.*?)FROM input_venue iv", query, re.S).group(1)
            db.execute("""CREATE TABLE input_venue (
                zip_code TEXT, address TEXT, timezone TEXT, city TEXT, state TEXT
            )""")
            db.execute("INSERT INTO input_venue (zip_code) VALUES (?)", (incoming,))
            db.execute("UPDATE clubs AS c SET " + updates + " FROM input_venue iv")
        return db.execute("SELECT zip_code FROM clubs").fetchone()[0]


@pytest.mark.parametrize(
    "query,route",
    PATHS,
    ids=["eventbrite", "seatengine", "seatengine-v3", "ticketmaster-name", "discovery", "ticketmaster-source"],
)
@pytest.mark.parametrize("incoming", [None, "", "   ", "10001"])
def test_preserve_existing_zip(query, route, incoming):
    assert _update_zip(query, route, "02116", incoming) == "02116"


@pytest.mark.parametrize(
    "query,route",
    PATHS,
    ids=["eventbrite", "seatengine", "seatengine-v3", "ticketmaster-name", "discovery", "ticketmaster-source"],
)
@pytest.mark.parametrize("existing", [None, "", "   "])
def test_fill_missing_zip(query, route, existing):
    assert _update_zip(query, route, existing, "02116") == "02116"


@pytest.mark.parametrize(
    "query,route",
    PATHS,
    ids=["eventbrite", "seatengine", "seatengine-v3", "ticketmaster-name", "discovery", "ticketmaster-source"],
)
@pytest.mark.parametrize("existing", [None, "", "   "])
@pytest.mark.parametrize("incoming", [None, "", "   "])
def test_blank_source_does_not_replace_existing_representation(query, route, existing, incoming):
    assert _update_zip(query, route, existing, incoming) == existing
