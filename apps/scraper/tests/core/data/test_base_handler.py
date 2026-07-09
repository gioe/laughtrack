"""
Unit tests for BaseDatabaseHandler.execute_batch_operation logging behaviour.

Specifically verifies the fix for the spurious "No X were processed" WARNING
that fired when an INSERT...RETURNING returned an empty list because all rows
already existed (ON CONFLICT DO NOTHING). The fix distinguishes three cases:

  1. RETURNING query, >0 rows returned  → INFO via log_simple_batch_operation
  2. RETURNING query, 0 rows returned   → INFO "0 new X inserted — all already existed"
  3. Non-RETURNING query (UPDATE/DELETE) → log_simple_batch_operation with cursor.rowcount
"""

from unittest.mock import MagicMock, patch

import pytest

from _core_data_test_helpers import (
    BaseDatabaseHandler,
    DatabaseOperationLogger,
    _base_handler_mod,
    _mock_db_op_logger,
    _mock_logger,
)


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
        return self._run_query(
            "INSERT INTO widgets VALUES %s RETURNING id",
            return_results=return_results,
            execute_values_return=execute_values_return,
            rowcount=rowcount,
        )

    def _run_query(self, query, return_results, execute_values_return, rowcount=0):
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
                query,
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
            operation="insert", items_count=2, entity_type="widget", input_count=2
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
            operation="insert", items_count=3, entity_type="widget", input_count=2
        )

    def test_non_returning_zero_rowcount_still_warns(self):
        """UPDATE with 0 affected rows still calls log_simple_batch_operation (may warn)."""
        self._run(return_results=False, execute_values_return=None, rowcount=0)

        _mock_db_op_logger.log_simple_batch_operation.assert_called_once_with(
            operation="insert", items_count=0, entity_type="widget", input_count=2
        )

    def test_insert_on_conflict_do_nothing_zero_rowcount_logs_info_not_warning(self):
        """A duplicate-only INSERT ... DO NOTHING batch is a normal no-op, not a warning."""
        self._run_query(
            "INSERT INTO widgets VALUES %s ON CONFLICT DO NOTHING",
            return_results=False,
            execute_values_return=None,
            rowcount=0,
        )

        _mock_db_op_logger.log_simple_batch_operation.assert_not_called()
        _mock_logger.warn.assert_not_called()
        _mock_logger.info.assert_called_once_with(
            "insert operation: 0 new widget processed — all already existed"
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


class TestDatabaseOperationLogger:
    """Direct coverage for zero-processed warning suppression."""

    def setup_method(self):
        """Reset mocks before each test."""
        _mock_logger.reset_mock()

    def test_empty_input_zero_processed_suppresses_warning(self):
        DatabaseOperationLogger.log_simple_batch_operation(
            operation="insert",
            items_count=0,
            entity_type="tag",
            input_count=0,
        )

        _mock_logger.warn.assert_not_called()
        _mock_logger.info.assert_not_called()

    def test_non_empty_input_zero_processed_still_warns(self):
        DatabaseOperationLogger.log_simple_batch_operation(
            operation="insert",
            items_count=0,
            entity_type="tag",
            input_count=4,
        )

        _mock_logger.warn.assert_called_once_with("insert operation: No tag were processed")


class TestAcquireConnectionFallbackClose:
    """Regression coverage for TASK-2411: _acquire_connection's no-conn fallback
    must close the freshly-opened connection on both success and exception.

    psycopg2's connection __exit__ only commits / rolls back the transaction —
    it does not close the connection. Without the try/finally: new_conn.close()
    wrapper around the inner `with new_conn:`, every handler call without an
    externally-provided conn would leak a connection.
    """

    def _make_bare_conn(self):
        """Minimal context-manager mock for create_connection() — no cursor wiring."""
        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        return conn

    def test_fallback_closes_connection_on_success(self):
        handler = _ConcreteHandler()
        conn = self._make_bare_conn()

        with patch.object(handler, "create_connection", return_value=conn):
            with handler._acquire_connection(None) as active:
                assert active is conn

        conn.close.assert_called_once_with()

    def test_fallback_closes_connection_on_exception(self):
        handler = _ConcreteHandler()
        conn = self._make_bare_conn()

        class _Boom(Exception):
            pass

        with patch.object(handler, "create_connection", return_value=conn):
            with pytest.raises(_Boom):
                with handler._acquire_connection(None) as active:
                    assert active is conn
                    raise _Boom("simulated handler failure")

        conn.close.assert_called_once_with()
        # The inner `with new_conn:` must also see the exception so psycopg2
        # rolls back the transaction before close() runs.
        conn.__exit__.assert_called_once()
        exc_type, exc_val, _tb = conn.__exit__.call_args.args
        assert exc_type is _Boom
        assert isinstance(exc_val, _Boom)
