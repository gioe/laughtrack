"""Real aggregate address shapes must resolve without guessing or overwriting."""

import re
import sqlite3

import pytest

from scripts.core import backfill_club_timezones as backfill
from sql.club_queries import ClubQueries


@pytest.mark.parametrize(
    "state,address,expected",
    [
        (None, "340 East Patrick Street, Frederick, MD 21701 (event held in Suite 100)", "America/New_York"),
        (None, "2000 Main St., Ferndale, Washington 98248", "America/Los_Angeles"),
        (None, "1 Industrial Way Unit 13, Portland, Maine 04103", "America/New_York"),
        (None, "21730 Red Rum Drive, Suite #142, Ashburn, VA, 20147", "America/New_York"),
        (None, "200 Southridge Dr #1013, Okotoks, AB T1S 0N8", "America/Edmonton"),
        (None, "706 Main St, Moncton, NB E1C 1E4", "America/Moncton"),
        ("CA", "1 Main St, Albany, NY 12207", None),
        ("TX", "1 Main St, El Paso, TX 79901", None),
        (None, "1329 Gardiners Rd Suite 109, Kingston, ON K7P 0L8,", None),
        (None, "626 Nth 3rd Ave.", None),
    ],
)
def test_timezone_evidence_and_preservation(state, address, expected):
    row = backfill.ClubRow(1, "Venue", state, address, None, None)
    assert backfill.derive_timezone(row, client=None, geocode=False).timezone == expected

    # Execute the production NULL-guarded update clause in a scratch SQL engine.
    # This models a verified timezone arriving between selection and update.
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE clubs (id INTEGER, timezone TEXT)")
        db.execute("INSERT INTO clubs VALUES (1, 'America/Denver')")
        db.execute("CREATE TABLE evidence (id INTEGER, timezone TEXT)")
        db.execute("INSERT INTO evidence VALUES (1, ?)", (expected,))
        sql = re.sub(
            r"FROM \(VALUES %s\) AS v\(id, timezone\)", "FROM evidence AS v", ClubQueries.BATCH_UPDATE_CLUB_TIMEZONES
        )
        sql = sql.replace("RETURNING c.id", "RETURNING id")
        db.execute(sql)
        assert db.execute("SELECT timezone FROM clubs").fetchone()[0] == "America/Denver"


@pytest.mark.parametrize(
    "state,address,country,expected",
    [
        ("CA", "1 Main St, Los Angeles, CA 90001, USA", "US", "America/Los_Angeles"),
        ("CA", "1 Main St, Los Angeles, CA 90001", "Canada", None),
        ("CA", "1 Main St, Los Angeles, CA 90001, USA", "Canada", None),
        (None, "1 Main St, Halifax, NS B3J 1A1, Canada", None, "America/Halifax"),
        (None, "1 Main St, Charlottetown, PE C1A 1A1", None, "America/Halifax"),
        ("FL", "1 Main St, Pensacola, FL 32501", "US", None),
        ("CA", "1 Main St", "GB", None),
        ("CA", "1 Main St, London, UK", None, None),
        ("CA", "1 Main St, London, United Kingdom", None, None),
    ],
)
def test_country_and_split_zone_evidence(state, address, country, expected):
    row = backfill.ClubRow(1, "Venue", state, address, None, None, country)
    assert backfill.derive_timezone(row, client=None, geocode=False).timezone == expected


@pytest.mark.parametrize(
    "province,postal,city,expected",
    [
        ("NB", "E1C 1E4", "Moncton", "America/Moncton"),
        ("AB", "T1S 0N8", "Okotoks", "America/Edmonton"),
        ("ON", "K7P 0L8", "Kingston", None),
    ],
)
def test_extractor_canadian_country_code(province, postal, city, expected):
    from laughtrack.scrapers.implementations.next_stop_comedy.extractor import _full_address
    from laughtrack.utilities.domain.club.timezone_lookup import timezone_from_evidence

    address = _full_address(
        {
            "streetAddress": "706 Main St",
            "addressLocality": city,
            "addressRegion": province,
            "postalCode": postal,
            "addressCountry": "CA",
        }
    )
    assert address.endswith(", CA")
    assert timezone_from_evidence(None, address)[1] == expected
    assert timezone_from_evidence(None, address, "US")[1] is None


def test_california_without_country_is_not_canada():
    from laughtrack.utilities.domain.club.timezone_lookup import timezone_from_evidence

    assert timezone_from_evidence(None, "1 Main St, Los Angeles, CA")[1] == "America/Los_Angeles"
