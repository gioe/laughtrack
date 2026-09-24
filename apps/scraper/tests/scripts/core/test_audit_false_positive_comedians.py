"""Shared title rules exercised through the generated historical-audit SQL.

SQLite supplies SQL parsing and literal decoding here; its REGEXP callback uses
Python regex. PostgreSQL regex dialect compatibility is verified separately with
read-only production VALUES queries, not by making unit tests require a live DB.
"""

import re
import sqlite3

import pytest

from scripts.core import audit_false_positive_comedians as audit
from laughtrack.core.entities.comedian.false_positive_detector import detect_false_positive


@pytest.mark.parametrize(
    "name, rejected",
    [
        ("School Girls; OR, The African Mean Girls Play", True),
        ("School Girls:Or, The African Mean Girls", True),
        ("School Girls Or The African Mean Girls Play", True),
        ("  SCHOOL GIRLS OR THE AFRICAN MEAN GIRLS PLAY  ", True),
        ("Example The Musical", True),
        ("The Play That Goes Wrong", True),
        ("Randy Feltface: Gimmick", True),
        ("Mixology class", True),
        ("Craft & A Cocktail—Folk Art Snake Workshop", True),
        ("Community Night", True),
        ("\t Community Night \n", True),
        ("\tSheryl on September24th\t", True),
        ("The Weekend Show", True),
        ("Sheryl on September24th", True),
        ("Blue Man Group", False),
        ("Denim", False),
        ("The Qs", False),
        ("Kids in the Hall", False),
        ("Kid N Play", False),
        ("The Lady Bunny", False),
        ("First Class", False),
        ("Class Clown", False),
        ("D'Angelo", False),
        ("Jean-Luc Moreau", False),
        ("fae lily", False),
        ("Bradley Ray Rose (formally Brad Griep)", False),
    ],
)
def test_title_pattern_parity(name, rejected):
    # Translate only the PostgreSQL regex operator; execute the generated SQL
    # intact otherwise, including its escaping, trim, OR precedence and casing.
    predicate = audit._TITLE_PATTERN_CONDITIONS.replace(" ~ ", " REGEXP ")
    with sqlite3.connect(":memory:") as connection:
        connection.create_function("regexp", 2, lambda pattern, value: bool(re.search(pattern, value)))
        result = connection.execute(
            f"SELECT ({predicate}) FROM (SELECT ? AS name) c", (name,)
        ).fetchone()[0]
    assert bool(result) is rejected
    assert (detect_false_positive(name) is not None) is rejected


def test_shared_title_patterns_reach_all_structural_audit_paths():
    for query in (
        audit.STRUCTURAL_AUDIT_QUERY,
        audit.DELETABLE_UUIDS_QUERY,
        audit.CSV_DETAIL_QUERY,
        audit.MERGE_CANDIDATES_QUERY,
    ):
        assert audit._TITLE_PATTERN_CONDITIONS in query
    assert "THEN 'event_title_pattern'" in audit.STRUCTURAL_AUDIT_QUERY
    assert "c.name LIKE '%***%' THEN 'decoration_pattern'" in audit.STRUCTURAL_AUDIT_QUERY


def test_rule_sql_literals_preserve_apostrophes_and_backslashes():
    pattern = r"o'brien\s+workshop"
    with sqlite3.connect(":memory:") as connection:
        result = connection.execute(f"SELECT {audit._sql_literal(pattern)}").fetchone()[0]
    assert result == pattern
