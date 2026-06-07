"""Parse-time validation for every SQL constant in apps/scraper/sql/.

TASK-2700 shipped ``COALESCE(NULLIF(ss.platform, ''), ...)`` in
``ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS``. ``ss.platform`` is the
``ScrapingPlatform`` enum, and Postgres cannot cast ``''`` to an enum domain —
the query parsed fine as a Python string but blew up at plan time on the prod
nightly. The existing substring assertions in
``tests/foundation/test_popularity_scorer.py`` cannot catch this class of bug
because they never let Postgres see the SQL.

This module runs ``PREPARE`` against a real Postgres for every SQL constant
exported from ``apps/scraper/sql/``. ``PREPARE`` forces the planner to parse,
resolve every column reference, and coerce every literal — including enum
casts — without executing the statement. Any parse-time error fails the test.

Skipped automatically when ``TEST_DATABASE_URL`` is unset (local dev without
Postgres). CI wires up a postgres service and the Prisma-generated schema
before invoking this module — see ``.github/workflows/scraper-ci.yml``.

To run locally::

    createdb test_sql_parse  # or use Docker
    npx -y prisma@6.5.0 migrate diff --from-empty \\
        --to-schema-datamodel apps/web/prisma/schema.prisma --script \\
        | psql test_sql_parse
    cd apps/scraper && TEST_DATABASE_URL=postgresql:///test_sql_parse \\
        python -m pytest tests/sql/ -v
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

try:
    import psycopg2
except ImportError:  # pragma: no cover - psycopg2 is a hard runtime dep
    psycopg2 = None

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

_CONSTANT_NAME_RE = re.compile(r"[A-Z][A-Z0-9_]*")

# SQL constants that reference tables not yet present in the canonical Prisma
# schema. Each caller already wraps these in try/except with a log-and-skip
# fallback (see ``comedian/handler.py::_filter_denied_comedians``), so the
# parse-time error is expected until the backing migration lands. Listing them
# here keeps the guard's signal-to-noise high without silently dropping them
# from the run — when the table is added, removing the entry re-enables strict
# parse-time validation.
KNOWN_UNRESOLVED_TABLES: Dict[str, str] = {
    "comedian_queries.ComedianQueries.UPSERT_DENY_LIST_NAMES": (
        "comedian_deny_list table is forward-looking; caller wraps in try/except"
    ),
    "comedian_queries.ComedianQueries.GET_DENIED_NAMES": (
        "comedian_deny_list table is forward-looking; caller wraps in try/except"
    ),
}


def _discover_sql_constants() -> List[Tuple[str, str]]:
    """Walk apps/scraper/sql/*.py and return every (qualified_name, sql_text).

    Each query file defines a ``XxxQueries`` class whose UPPER_SNAKE_CASE
    attributes hold raw SQL strings. Private fragments (names prefixed with
    ``_``, used to compose larger queries) are skipped because they are not
    standalone statements.
    """
    if not SQL_DIR.exists():
        return []
    constants: List[Tuple[str, str]] = []
    for py_file in sorted(SQL_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        module_name = py_file.stem
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for cls_name, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module_name:
                continue
            for attr_name in vars(cls):
                if not _CONSTANT_NAME_RE.fullmatch(attr_name):
                    continue
                value = getattr(cls, attr_name)
                if not isinstance(value, str) or not value.strip():
                    continue
                constants.append((f"{module_name}.{cls_name}.{attr_name}", value))
    return constants


SQL_CONSTANTS = _discover_sql_constants()


def _parse_parent_aliases(sql: str) -> Dict[str, str]:
    """Map every UPDATE/INSERT/DELETE table (and its alias, if any) to the table name.

    For ``UPDATE comedians AS c`` returns ``{"comedians": "comedians", "c": "comedians"}``.
    Used downstream to resolve ``c.popularity`` to ``comedians.popularity`` when
    inferring the type of a VALUES-clause column.
    """
    aliases: Dict[str, str] = {}
    pattern = re.compile(
        r"\b(?:UPDATE|INSERT\s+INTO|DELETE\s+FROM)\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?",
        re.IGNORECASE,
    )
    reserved = {"set", "where", "values", "select", "as", "on", "returning"}
    for m in pattern.finditer(sql):
        table = m.group(1).lower()
        aliases[table] = table
        if m.group(2):
            alias = m.group(2).lower()
            if alias not in reserved:
                aliases[alias] = table
    return aliases


def _infer_alias_col_type(
    sql: str,
    parent_aliases: Dict[str, str],
    alias: str,
    col: str,
    schema_columns: Dict[str, Dict[str, str]],
) -> str:
    """Best-effort type inference for ``<alias>.<col>`` from surrounding SQL context.

    Tries five strategies in order:

    1. ``SET <X> = <alias>.<col>`` (in an UPDATE) — should match parent.<X>.
    2. ``<table_alias>.<X> = <alias>.<col>`` (WHERE/JOIN) — look up via parent_aliases.
    3. ``<alias>.<col>::TYPE`` — the cast tells us the expected type.
    4. Direct match: parent_table has a column named exactly ``<col>``.
    5. Fallback to ``text`` — Postgres can coerce text→other-types when the
       column is bare ``%s`` and the surrounding SQL casts it explicitly.

    Returns a SQL type string like ``'integer'``, ``'text'``, ``'jsonb'``,
    ``'double precision'``, ``'timestamptz'``.
    """
    col_re = re.escape(col)
    alias_re = re.escape(alias)

    # Strategy 1 + 2: any "<word> = <alias>.<col>" or "<word>.<word2> = <alias>.<col>"
    for m in re.finditer(
        rf"(\w+)(?:\.(\w+))?\s*=\s*{alias_re}\.{col_re}\b", sql, re.IGNORECASE
    ):
        first, second = m.group(1).lower(), (m.group(2) or "").lower()
        if second:
            table = parent_aliases.get(first)
            if table and second in schema_columns.get(table, {}):
                return schema_columns[table][second]
            if second in schema_columns.get(first, {}):
                return schema_columns[first][second]
        else:
            for table in parent_aliases.values():
                if first in schema_columns.get(table, {}):
                    return schema_columns[table][first]

    # Strategy 3: explicit cast on <alias>.<col>
    cast_re = re.compile(
        rf"\b{alias_re}\.{col_re}\s*::\s*([a-zA-Z_][\w\s]*?(?:\[\])?)\s*(?=[,\s)]|$)",
        re.IGNORECASE,
    )
    m = cast_re.search(sql)
    if m:
        return m.group(1).strip().lower()

    # Strategy 4: parent table has column with same name
    for table in parent_aliases.values():
        if col in schema_columns.get(table, {}):
            return schema_columns[table][col]

    return "text"


def _build_typed_values(cols: List[str], types: List[str]) -> str:
    """Render ``NULL::TYPE1, NULL::TYPE2, ...`` for a VALUES row substitution."""
    return ", ".join(f"NULL::{t}" for t in types)


def _to_prepare_sql(sql: str, schema_columns: Dict[str, Dict[str, str]]) -> str:
    """Rewrite a psycopg2-style SQL string so ``PREPARE`` can plan it standalone.

    Four transforms, in order:

    1. ``(VALUES %s) AS alias(c1, c2, ...)`` (execute_values pattern) →
       ``(VALUES (NULL::T1, NULL::T2, ...)) AS alias(...)``. Types inferred
       from the surrounding SQL via ``_infer_alias_col_type``.
    2. ``INSERT INTO t (c1, c2, ...) VALUES %s`` → ``... VALUES (NULL::T1, ...)``.
       Types come straight from the INSERT's target columns.
    3. Remaining ``%s`` → sequential ``$1, $2, ...`` so PREPARE can infer
       parameter types from the surrounding expression context.
    4. Unescape psycopg2's ``%%`` back to a literal ``%``.

    The trailing semicolon is stripped because ``PREPARE foo AS stmt;``
    requires ``stmt`` to be a single complete statement without its terminator.
    """
    parent_aliases = _parse_parent_aliases(sql)

    def _values_alias_replacer(match: re.Match) -> str:
        alias = match.group(1)
        cols_csv = match.group(2)
        cols = [c.strip() for c in cols_csv.split(",")]
        types = [
            _infer_alias_col_type(sql, parent_aliases, alias, c, schema_columns)
            for c in cols
        ]
        return f"VALUES ({_build_typed_values(cols, types)})) AS {alias}({cols_csv})"

    sql = re.sub(
        r"VALUES\s+%s\s*\)\s+AS\s+(\w+)\s*\(\s*([^)]+?)\s*\)",
        _values_alias_replacer,
        sql,
        flags=re.IGNORECASE,
    )

    def _insert_values_replacer(match: re.Match) -> str:
        prefix = match.group(1)
        table = match.group(2).lower()
        cols_csv = match.group(3)
        cols = [c.strip() for c in cols_csv.split(",")]
        types = [
            schema_columns.get(table, {}).get(c, "text") for c in cols
        ]
        return f"{prefix}VALUES ({_build_typed_values(cols, types)})"

    sql = re.sub(
        r"(INSERT\s+INTO\s+(\w+)\s*\(\s*([^)]+?)\s*\)\s*)VALUES\s+%s",
        _insert_values_replacer,
        sql,
        flags=re.IGNORECASE,
    )

    counter = {"n": 0}

    def _next_dollar(_match: re.Match) -> str:
        counter["n"] += 1
        return f"${counter['n']}"

    sql = re.sub(r"%s", _next_dollar, sql)
    sql = sql.replace("%%", "%")
    return sql.strip().rstrip(";").strip()


def _load_schema_columns(conn) -> Dict[str, Dict[str, str]]:
    """Return ``{table_name: {column_name: data_type}}`` for the test schema.

    ``data_type`` is the textual ``information_schema`` type (e.g. ``'integer'``,
    ``'text'``, ``'jsonb'``, ``'double precision'``, ``'timestamp with time zone'``).
    Two cases need special handling because ``information_schema.data_type``
    erases element-level type info:

    - ``USER-DEFINED`` (enums and other custom types): use ``udt_name``, which
      carries the actual enum name so VALUES-row casts emit ``::<enum_name>``.
    - ``ARRAY``: ``udt_name`` carries the element type as ``_text``/``_int4``/
      ``_varchar``. Strip the leading underscore, normalize the pg internal
      name to its SQL form, and append ``[]`` so casts emit ``::text[]`` etc.
    """
    _PG_ARRAY_ELEMENT_ALIASES = {
        "int2": "smallint",
        "int4": "integer",
        "int8": "bigint",
        "float4": "real",
        "float8": "double precision",
        "bool": "boolean",
    }
    rows: Dict[str, Dict[str, str]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.table_name, c.column_name, c.data_type, c.udt_name
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
            """
        )
        for table, column, data_type, udt_name in cur.fetchall():
            t = table.lower()
            if data_type == "USER-DEFINED":
                resolved = udt_name
            elif data_type == "ARRAY":
                element = udt_name.lstrip("_")
                element = _PG_ARRAY_ELEMENT_ALIASES.get(element, element)
                resolved = f"{element}[]"
            else:
                resolved = data_type
            rows.setdefault(t, {})[column.lower()] = resolved
    return rows


@pytest.fixture(scope="session")
def pg_conn():
    """Open a session-scoped Postgres connection from ``TEST_DATABASE_URL``.

    When the env var is unset (local dev without a throwaway Postgres) the
    whole module is skipped with a pointer to the README instructions. CI
    always sets the var, so the guard runs there.
    """
    if psycopg2 is None:
        pytest.skip("psycopg2 not installed; cannot run SQL parse-time guard")
    if not TEST_DATABASE_URL:
        pytest.skip(
            "TEST_DATABASE_URL not set; skipping SQL parse-time guard. "
            "See the module docstring for local-dev setup."
        )
    conn = psycopg2.connect(TEST_DATABASE_URL)
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="session")
def schema_columns(pg_conn) -> Dict[str, Dict[str, str]]:
    """Cache ``information_schema.columns`` once per test session."""
    return _load_schema_columns(pg_conn)


def _parametrize_args() -> List:
    """Build the parametrize list, wrapping known-unresolved constants in xfail.

    ``strict=True`` is the audit anchor: when the backing migration for a
    forward-looking table finally lands, the test will PREPARE successfully,
    producing an XPASS that pytest reports as a hard failure. That forces the
    operator to remove the corresponding ``KNOWN_UNRESOLVED_TABLES`` entry
    instead of letting the escape hatch rot silently into perpetual XFAIL.
    """
    args = []
    for name, sql in SQL_CONSTANTS:
        if name in KNOWN_UNRESOLVED_TABLES:
            args.append(
                pytest.param(
                    name,
                    sql,
                    id=name,
                    marks=pytest.mark.xfail(
                        strict=True, reason=KNOWN_UNRESOLVED_TABLES[name]
                    ),
                )
            )
        else:
            args.append(pytest.param(name, sql, id=name))
    return args or [pytest.param("", "", id="no-sql-constants-discovered")]


@pytest.mark.parametrize("constant_name,sql_text", _parametrize_args())
def test_sql_constant_parses(
    pg_conn,
    schema_columns: Dict[str, Dict[str, str]],
    constant_name: str,
    sql_text: str,
) -> None:
    """Run PREPARE on the SQL constant — fails if Postgres reports any error.

    PREPARE makes the planner do its full work (column resolution, type
    coercion, enum cast validation, JOIN/CTE planning) without executing the
    statement. A regression like TASK-2700 (NULLIF on an enum) surfaces as
    ``psycopg2.errors.InvalidTextRepresentation`` here.
    """
    prepared_sql = _to_prepare_sql(sql_text, schema_columns)
    stmt = "sql_parse_check"

    with pg_conn.cursor() as cur:
        try:
            cur.execute(f"DEALLOCATE {stmt}")
            pg_conn.commit()
        except psycopg2.Error:
            pg_conn.rollback()

        try:
            cur.execute(f"PREPARE {stmt} AS {prepared_sql}")
        except psycopg2.Error as exc:
            pg_conn.rollback()
            pytest.fail(
                f"{constant_name} failed parse-time validation against Postgres:\n"
                f"  {type(exc).__name__}: {exc}\n\n"
                f"Generated SQL sent to PREPARE:\n{prepared_sql}"
            )
        pg_conn.commit()
        try:
            cur.execute(f"DEALLOCATE {stmt}")
            pg_conn.commit()
        except psycopg2.Error:
            pg_conn.rollback()
