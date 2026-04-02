"""
Unit tests for BaseDatabaseHandler.execute_batch_operation logging behaviour.

Specifically verifies the fix for the spurious "No X were processed" WARNING
that fired when an INSERT...RETURNING returned an empty list because all rows
already existed (ON CONFLICT DO NOTHING). The fix distinguishes three cases:

  1. RETURNING query, >0 rows returned  → INFO via log_simple_batch_operation
  2. RETURNING query, 0 rows returned   → INFO "0 new X inserted — all already existed"
  3. Non-RETURNING query (UPDATE/DELETE) → log_simple_batch_operation with cursor.rowcount
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Bootstrap helpers — load source without triggering __init__.py chains
# ---------------------------------------------------------------------------

_SCRAPER_ROOT = Path(__file__).parents[3]  # apps/scraper/


def _ensure_psycopg2_stubbed():
    if "psycopg2" not in sys.modules:
        psycopg2 = ModuleType("psycopg2")
        extras = ModuleType("psycopg2.extras")
        extras.DictRow = dict
        extras.execute_values = MagicMock()
        extensions = ModuleType("psycopg2.extensions")
        extensions.connection = object
        psycopg2.extras = extras
        psycopg2.extensions = extensions
        sys.modules["psycopg2"] = psycopg2
        sys.modules["psycopg2.extras"] = extras
        sys.modules["psycopg2.extensions"] = extensions


def _stub(name, as_package=False, **attrs):
    m = ModuleType(name)
    if as_package:
        pkg_path = str(_SCRAPER_ROOT / "src" / name.replace(".", "/"))
        m.__path__ = [pkg_path]
        m.__package__ = name
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


def _load_module(rel_path, module_name):
    path = _SCRAPER_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    _ensure_psycopg2_stubbed()
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Stubs required before loading base_handler
# ---------------------------------------------------------------------------

_ensure_psycopg2_stubbed()

_mock_logger = MagicMock()
_mock_db_op_logger = MagicMock()

_stub("laughtrack.foundation.infrastructure.logger.logger", Logger=_mock_logger)
_stub("laughtrack.foundation.infrastructure.logger", as_package=True, Logger=_mock_logger)
_stub("laughtrack.foundation.infrastructure", as_package=True)
_stub("laughtrack.foundation.infrastructure.database", as_package=True)
_stub(
    "laughtrack.foundation.infrastructure.database.operation",
    DatabaseOperationLogger=_mock_db_op_logger,
)
_stub("laughtrack.foundation.models.types", T=None, JSONDict=dict)
_stub("laughtrack.foundation.models", as_package=True)
_stub("laughtrack.foundation", as_package=True)

# Stub adapters.db so base_handler.py's import resolves — include all names
# re-exported by the real module so downstream collectors (e.g. grove34) don't
# get an ImportError when this stub is already in sys.modules.
_stub(
    "laughtrack.adapters.db",
    create_connection=MagicMock(),
    create_connection_with_transaction=MagicMock(),
    get_connection=MagicMock(),
    get_transaction=MagicMock(),
    db=MagicMock(),
)
_stub("laughtrack.adapters", as_package=True)
_stub("laughtrack", as_package=True)

# Load base_handler under a unique name to avoid conflicts with other test files
_base_handler_mod = _load_module(
    "src/laughtrack/core/data/base_handler.py",
    "laughtrack.core.data.base_handler_test_isolated",
)
BaseDatabaseHandler = _base_handler_mod.BaseDatabaseHandler


# ---------------------------------------------------------------------------
# Concrete subclass for testing
# ---------------------------------------------------------------------------

class _ConcreteHandler(BaseDatabaseHandler):
    def get_entity_name(self):
        return "widget"

    def get_entity_class(self):
        return dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_conn(execute_values_return, rowcount=0):
    """Return a context-manager mock for create_connection() that wires
    execute_values to return *execute_values_return* and cursor.rowcount
    to *rowcount*."""
    cursor = MagicMock()
    cursor.rowcount = rowcount
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.__enter__ = lambda s: conn
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor

    # execute_values is patched at the module level
    return conn, cursor


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExecuteBatchOperationLogging:
    """Verify logging decisions inside execute_batch_operation."""

    def setup_method(self):
        """Reset mocks before each test."""
        _mock_logger.reset_mock()
        _mock_db_op_logger.reset_mock()

    def _run(self, return_results, execute_values_return, rowcount=0):
        handler = _ConcreteHandler()
        conn, cursor = _make_mock_conn(execute_values_return, rowcount)

        # execute_values is imported directly into base_handler via
        # "from psycopg2.extras import execute_values" — patch the name
        # in the loaded module's namespace, not on psycopg2.extras itself.
        with (
            patch.object(handler, "create_connection", return_value=conn),
            patch.object(
                _base_handler_mod,
                "execute_values",
                return_value=execute_values_return,
            ),
        ):
            result = handler.execute_batch_operation(
                "INSERT INTO widgets VALUES %s RETURNING id",
                [("a",), ("b",)],
                return_results=return_results,
            )
        return result

    # --- Case 1: RETURNING query, rows were inserted -------------------------

    def test_returning_with_rows_calls_log_simple_batch_operation(self):
        """When RETURNING returns rows, log_simple_batch_operation is called with count."""
        rows = [{"id": 1}, {"id": 2}]
        self._run(return_results=True, execute_values_return=rows)

        _mock_db_op_logger.log_simple_batch_operation.assert_called_once_with(
            operation="insert", items_count=2, entity_type="widget"
        )
        _mock_logger.warn.assert_not_called()

    # --- Case 2: RETURNING query, all rows already existed -------------------

    def test_returning_empty_logs_info_not_warning(self):
        """When RETURNING returns [] (ON CONFLICT DO NOTHING), log INFO — not WARNING."""
        self._run(return_results=True, execute_values_return=[])

        # Must NOT call log_simple_batch_operation (which would warn for count=0)
        _mock_db_op_logger.log_simple_batch_operation.assert_not_called()
        _mock_logger.warn.assert_not_called()

        # Must log at INFO level with an explanatory message from the zero-row branch
        _mock_logger.info.assert_called_once_with(
            "insert operation: 0 new widget processed — all already existed"
        )

    # --- Case 3: Non-RETURNING query (UPDATE/DELETE) -------------------------

    def test_non_returning_uses_rowcount(self):
        """return_results=False routes through log_simple_batch_operation using cursor.rowcount.
        The helper always passes an INSERT query, so operation='insert' in the assertion.
        The UPDATE/DELETE distinction is in the caller — the rowcount path is the same."""
        self._run(return_results=False, execute_values_return=None, rowcount=3)

        _mock_db_op_logger.log_simple_batch_operation.assert_called_once_with(
            operation="insert", items_count=3, entity_type="widget"
        )

    def test_non_returning_zero_rowcount_still_warns(self):
        """UPDATE with 0 affected rows still calls log_simple_batch_operation (may warn)."""
        self._run(return_results=False, execute_values_return=None, rowcount=0)

        _mock_db_op_logger.log_simple_batch_operation.assert_called_once_with(
            operation="insert", items_count=0, entity_type="widget"
        )

    # --- Case 2b: RETURNING query, execute_values returns None ---------------

    def test_returning_none_logs_info_not_warning(self):
        """When execute_values returns None with return_results=True, treat as 0 rows."""
        self._run(return_results=True, execute_values_return=None)

        _mock_db_op_logger.log_simple_batch_operation.assert_not_called()
        _mock_logger.warn.assert_not_called()
        _mock_logger.info.assert_called_once_with(
            "insert operation: 0 new widget processed — all already existed"
        )
