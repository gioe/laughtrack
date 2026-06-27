"""DB-backed tests for the club_aliases normalization single-source-of-truth.

TASK-3462 moved the alias dedup-key normalization entirely into Postgres: the
``lt_normalize_alias_key(text)`` function plus the
``club_aliases_set_normalized`` BEFORE INSERT/UPDATE trigger (migration
``20260625140000_club_aliases_normalize_trigger``). The scraper unit suite mocks
the DB, so nothing there exercises that SQL — these tests lock it against future
drift (TASK-3463).

Runs against a real Postgres given by ``TEST_DATABASE_URL`` (the same harness the
SQL parse-time guard uses; scraper-ci provides an ephemeral Postgres). Skipped
automatically when ``TEST_DATABASE_URL`` is unset, so the normal unit-test run
(local ``tusk commit`` gate) does not require a database.

The function/trigger are NOT part of ``schema.prisma``'s datamodel — they live
only in the migration SQL — so the fixture applies that migration file directly.
The trigger assertions run against a ``TEMP TABLE LIKE club_aliases`` with the
real trigger attached, which copies club_aliases' columns + unique index but
NOT its foreign key to ``clubs`` (``LIKE`` never copies FKs), so the test needs
no seeded ``clubs`` row.

    cd apps/scraper && TEST_DATABASE_URL=postgresql:///some_test_db \\
        .venv/bin/python3 -m pytest tests/sql/test_club_aliases_normalize_trigger.py
"""

import os
from pathlib import Path

import pytest

try:
    import psycopg2
except ImportError:  # pragma: no cover - psycopg2 is a hard runtime dep
    psycopg2 = None

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

# apps/scraper/tests/sql/<this file> -> parents[4] is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_MIGRATION_SQL = (
    _REPO_ROOT
    / "apps/web/prisma/migrations"
    / "20260625140000_club_aliases_normalize_trigger"
    / "migration.sql"
)


def _create_trigger_test_table(cur, table_name: str) -> None:
    cur.execute(f"CREATE TEMP TABLE {table_name} (LIKE club_aliases INCLUDING ALL)")
    # The Prisma-generated schema marks updated_at NOT NULL but does not give it
    # a database default. These trigger tests intentionally omit timestamp
    # columns so they only exercise alias normalization behavior.
    cur.execute(f"ALTER TABLE {table_name} ALTER COLUMN updated_at SET DEFAULT NOW()")


@pytest.fixture(scope="module")
def conn():
    if psycopg2 is None:
        pytest.skip("psycopg2 not installed; cannot run club_aliases trigger tests")
    if not TEST_DATABASE_URL:
        pytest.skip(
            "TEST_DATABASE_URL not set; skipping club_aliases trigger DB test. "
            "Set it to a throwaway Postgres to run locally."
        )
    connection = psycopg2.connect(TEST_DATABASE_URL)
    connection.autocommit = True
    try:
        with connection.cursor() as cur:
            # In scraper-ci the real club_aliases table already exists (the schema
            # is applied from schema.prisma). Locally this minimal definition lets
            # the migration's trigger attach. Either way the migration below is the
            # source of truth for the function + trigger.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS club_aliases (
                    id SERIAL PRIMARY KEY,
                    club_id INTEGER NOT NULL,
                    alias_name TEXT NOT NULL,
                    normalized_alias_name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    normalized_city TEXT NOT NULL,
                    normalized_state TEXT NOT NULL,
                    source TEXT,
                    verified BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS club_aliases_normalized_location_key
                ON club_aliases (normalized_alias_name, normalized_city, normalized_state)
                """
            )
            # Apply the real migration (idempotent: CREATE OR REPLACE FUNCTION,
            # DROP TRIGGER IF EXISTS + CREATE TRIGGER, dedup DELETE + backfill
            # UPDATE which no-op on an empty table). This is the artifact under test.
            cur.execute(_MIGRATION_SQL.read_text())
        yield connection
    finally:
        connection.close()


@pytest.mark.parametrize(
    "raw, expected",
    [
        # No st/ft/mt abbreviation expansion — the exact drift that broke alias
        # matching in TASK-3458 and that this SSOT prevents.
        ("Comedy Club - St. Louis", "comedy club st louis"),
        ("Funny Bone - Ft. Lauderdale", "funny bone ft lauderdale"),
        # '&' -> ' and ', punctuation collapses to single spaces, lower-cased.
        ("Joe & Mike's, Mt. Vernon", "joe and mike s mt vernon"),
        ("  Multiple   Spaces--Here  ", "multiple spaces here"),
    ],
)
def test_lt_normalize_alias_key(conn, raw, expected):
    with conn.cursor() as cur:
        cur.execute("SELECT lt_normalize_alias_key(%s)", (raw,))
        assert cur.fetchone()[0] == expected


def test_trigger_fills_normalized_columns_and_dedups(conn):
    with conn.cursor() as cur:
        # TEMP TABLE LIKE club_aliases copies columns + the unique index but not
        # the FK to clubs, so we can insert without seeding a clubs row.
        _create_trigger_test_table(cur, "t_club_aliases")
        cur.execute(
            """
            CREATE TRIGGER t_club_aliases_set_normalized
            BEFORE INSERT OR UPDATE ON t_club_aliases
            FOR EACH ROW EXECUTE FUNCTION club_aliases_set_normalized()
            """
        )

        # Insert supplying ONLY raw alias_name/city/state — the trigger fills
        # normalized_alias_name/normalized_city/normalized_state (NOT NULL).
        cur.execute(
            """
            INSERT INTO t_club_aliases (club_id, alias_name, city, state)
            VALUES (%s, %s, %s, %s)
            """,
            (4242, "Funny Bone Comedy Club - St. Louis", "St. Louis", "MO"),
        )
        cur.execute(
            """
            SELECT normalized_alias_name, normalized_city, normalized_state
            FROM t_club_aliases WHERE club_id = 4242
            """
        )
        assert cur.fetchone() == ("funny bone comedy club st louis", "st louis", "mo")

        # A punctuation-only variant collapses to the SAME normalized key, so the
        # unique index rejects it — proving the dedup key works end to end.
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute(
                """
                INSERT INTO t_club_aliases (club_id, alias_name, city, state)
                VALUES (%s, %s, %s, %s)
                """,
                (4242, "Funny Bone Comedy Club  --  St Louis", "St Louis", "MO"),
            )


def test_trigger_overwrites_supplied_normalized_values(conn):
    """A writer that supplies wrong normalized_* values must not win — the trigger
    recomputes them, which is what makes the column a true single source of truth."""
    with conn.cursor() as cur:
        _create_trigger_test_table(cur, "t_club_aliases_ow")
        cur.execute(
            """
            CREATE TRIGGER t_club_aliases_ow_set_normalized
            BEFORE INSERT OR UPDATE ON t_club_aliases_ow
            FOR EACH ROW EXECUTE FUNCTION club_aliases_set_normalized()
            """
        )
        cur.execute(
            """
            INSERT INTO t_club_aliases_ow
                (club_id, alias_name, normalized_alias_name, city, state,
                 normalized_city, normalized_state)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (7, "The Lab", "WRONG", "Austin", "TX", "WRONG", "WRONG"),
        )
        cur.execute(
            "SELECT normalized_alias_name, normalized_city, normalized_state "
            "FROM t_club_aliases_ow WHERE club_id = 7"
        )
        assert cur.fetchone() == ("the lab", "austin", "tx")
