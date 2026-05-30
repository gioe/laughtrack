"""
Unit tests for TicketHandler.insert_tickets.

Covers:
- SQL contract: BATCH_ADD_TICKETS must include purchase_url = EXCLUDED.purchase_url
- Upsert behaviour: calling insert_tickets twice with the same (show_id, type) but a
  different purchase_url passes the updated URL to execute_batch_operation on the
  second call (regression guard for TASK-709 upsert fix).
"""

import sys
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from _entities_test_helpers import (
    _load_module,
    _stub,
    _ensure_psycopg2_stubbed,
    _BaseDatabaseHandlerStub,
)


# Foundation stubs — use as_package=True for all intermediate packages so that submodule
# imports (e.g. laughtrack.foundation.infrastructure.database.template) still resolve via
# the real filesystem when this test file is collected before other test files that load
# real packages. Leaf modules (files, not directories) do not need as_package.
_stub("laughtrack.foundation.protocols.database_entity", DatabaseEntity=object)
_stub("laughtrack.foundation.protocols", as_package=True, DatabaseEntity=object)
_stub("laughtrack.foundation.infrastructure.logger.logger", Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure.logger", as_package=True, Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure.database.operation", DatabaseOperationLogger=MagicMock())
_stub("laughtrack.foundation.infrastructure.database", as_package=True, DatabaseOperationLogger=MagicMock())
_stub("laughtrack.foundation.infrastructure", as_package=True, Logger=MagicMock())
_stub("laughtrack.adapters.db", create_connection=MagicMock())
_stub("laughtrack.adapters", as_package=True, create_connection=MagicMock())

_stub("laughtrack.core.data.base_handler", BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core.data", as_package=True, BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core", as_package=True, BaseDatabaseHandler=_BaseDatabaseHandlerStub)

# Load PriceRange (required by Ticket.price_tag property)
_price_range_mod = _load_module(
    "src/laughtrack/foundation/models/price_range.py",
    "laughtrack.foundation.models.price_range",
)
sys.modules.setdefault("laughtrack.foundation.models.price_range", _price_range_mod)

_stub_fm = _stub("laughtrack.foundation.models", as_package=True,
                 price_range=_price_range_mod, PriceRange=_price_range_mod.PriceRange)
_stub("laughtrack.foundation", as_package=True)

# Load Ticket model
_ticket_model_mod = _load_module(
    "src/laughtrack/core/entities/ticket/model.py",
    "laughtrack.core.entities.ticket.model_direct",
)
Ticket = _ticket_model_mod.Ticket
sys.modules.setdefault("laughtrack.core.entities.ticket.model", _ticket_model_mod)
sys.modules.setdefault("laughtrack.core.entities.ticket", _ticket_model_mod)

# Stub TicketUtils so handler.py loads; its deduplication logic is exercised via the real module.
# Use as_package=True for hierarchy stubs so Python can still find sibling submodules on disk
# (e.g. laughtrack.utilities.domain.show.*) when other test files are collected in the same run.
_ticket_utils_stub = MagicMock()
_ticket_utils_stub.deduplicate_tickets.side_effect = lambda tickets: tickets
_stub("laughtrack.utilities.domain.ticket.utils", as_package=False, TicketUtils=_ticket_utils_stub)
_stub("laughtrack.utilities.domain.ticket", as_package=True, TicketUtils=_ticket_utils_stub)
_stub("laughtrack.utilities.domain", as_package=True, TicketUtils=_ticket_utils_stub)
_stub("laughtrack.utilities", as_package=True, TicketUtils=_ticket_utils_stub)

# Load TicketQueries
_ticket_queries_mod = _load_module("sql/ticket_queries.py", "sql.ticket_queries_direct")
TicketQueries = _ticket_queries_mod.TicketQueries
# Direct assignment — override any MagicMock stub placed by earlier test files
# (e.g. test_lineup_handler stubs sql.ticket_queries for ShowHandler loading).
sys.modules["sql.ticket_queries"] = _ticket_queries_mod
# Do NOT register "sql" as a plain module — it is a real package on the pythonpath
# (apps/scraper/sql/) and must remain importable for sibling test files.

# Load TicketHandler
_ticket_handler_mod = _load_module(
    "src/laughtrack/core/entities/ticket/handler.py",
    "laughtrack.core.entities.ticket.handler_direct",
)
TicketHandler = _ticket_handler_mod.TicketHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeShow:
    """Minimal stand-in for Show used by insert_tickets."""
    def __init__(self, show_id: int, tickets):
        self.id = show_id
        self.tickets = tickets


def _make_ticket(purchase_url: str, price: float = 25.0, sold_out: bool = False) -> Ticket:
    return Ticket(price=price, purchase_url=purchase_url, sold_out=sold_out)


# ---------------------------------------------------------------------------
# SQL-level contract
# ---------------------------------------------------------------------------

class TestBatchAddTicketsSql:
    def test_overwrites_purchase_url_on_conflict(self):
        """Regression guard: ON CONFLICT clause must include purchase_url = EXCLUDED.purchase_url."""
        sql = TicketQueries.BATCH_ADD_TICKETS
        assert "purchase_url = EXCLUDED.purchase_url" in sql, (
            "BATCH_ADD_TICKETS must update purchase_url on conflict — "
            "regression from TASK-709 upsert fix"
        )

    def test_conflict_target_is_show_id_and_type(self):
        """ON CONFLICT must key on (show_id, type) to match the unique constraint."""
        sql = TicketQueries.BATCH_ADD_TICKETS
        assert "ON CONFLICT (show_id, type)" in sql

    def test_cleanup_query_targets_schema_org_ticket_types(self):
        sql = TicketQueries.DELETE_INVALID_SCHEMA_ORG_TICKETS_FOR_SHOWS
        assert "DELETE FROM tickets" in sql
        assert "show_id = ANY(%s)" in sql
        assert "schema.org" in sql


# ---------------------------------------------------------------------------
# Upsert behaviour
# ---------------------------------------------------------------------------

class TestInsertTicketsPurchaseUrlUpsert:
    """
    Criterion 2315: calling insert_tickets twice with the same (show_id, type) but
    a different purchase_url must pass the updated URL to execute_batch_operation.
    """

    @pytest.fixture(autouse=True)
    def _stub_transaction(self, monkeypatch):
        """Stub the single-transaction wrapper insert_tickets opens (TASK-2410).

        Without this, ``with self.transaction()`` calls the real
        create_connection(), which raises "Database configuration not found or
        incomplete" in CI (no DATABASE_* env). These tests assert the SQL
        contract via the per-operation execute_* mocks; the shared-transaction
        behaviour itself is covered by TestInsertTicketsSingleTransaction.
        """

        @contextmanager
        def _noop_transaction(_self):
            yield MagicMock(name="tx_conn")

        monkeypatch.setattr(TicketHandler, "transaction", _noop_transaction)

    def test_second_call_passes_updated_purchase_url(self):
        """execute_batch_operation receives the new purchase_url on the second insert."""
        show_id = 42
        original_url = "https://tickets.example.com/show/42?v=1"
        updated_url = "https://tickets.example.com/show/42?v=2"

        handler = TicketHandler()
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(return_value=None)

        # First insert — original URL
        show_v1 = _FakeShow(show_id, [_make_ticket(original_url)])
        handler.insert_tickets([show_v1])

        first_call_tuples = handler.execute_batch_operation.call_args_list[0].args[1]
        assert first_call_tuples[0][1] == original_url, "First insert should use the original URL"

        # Second insert — updated URL (simulates a re-scrape returning a changed purchase link)
        show_v2 = _FakeShow(show_id, [_make_ticket(updated_url)])
        handler.insert_tickets([show_v2])

        second_call_tuples = handler.execute_batch_operation.call_args_list[1].args[1]
        assert second_call_tuples[0][1] == updated_url, (
            "Second insert must pass the updated purchase_url — "
            "ON CONFLICT clause should overwrite it in the DB"
        )

    def test_both_calls_use_batch_add_tickets_query(self):
        """insert_tickets always calls execute_batch_operation with BATCH_ADD_TICKETS."""
        handler = TicketHandler()
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(return_value=None)

        show = _FakeShow(10, [_make_ticket("https://example.com/buy")])
        handler.insert_tickets([show])
        handler.insert_tickets([show])

        for c in handler.execute_batch_operation.call_args_list:
            assert c.args[0] == TicketQueries.BATCH_ADD_TICKETS

    def test_no_op_when_shows_have_no_tickets(self):
        """insert_tickets should return without calling execute_batch_operation when all shows have empty ticket lists."""
        handler = TicketHandler()
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(return_value=None)

        show = _FakeShow(42, [])
        handler.insert_tickets([show])

        handler.execute_batch_operation.assert_not_called()

    def test_tuple_order_matches_query_columns(self):
        """to_tuple() must emit (show_id, purchase_url, price, sold_out, type) — matching INSERT column order."""
        ticket = _make_ticket("https://example.com/t", price=30.0, sold_out=True)
        ticket.show_id = 7
        t = ticket.to_tuple()
        show_id, purchase_url, price, sold_out, ticket_type = t
        assert show_id == 7
        assert purchase_url == "https://example.com/t"
        assert price == 30.0
        assert sold_out is True
        assert ticket_type == "General Admission"

    def test_invalid_schema_org_ticket_rows_are_pruned_before_insert(self):
        handler = TicketHandler()
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(return_value=None)

        invalid = Ticket(
            price=25.0,
            purchase_url="https://bad.example/ticket",
            sold_out=False,
            type="http://schema.org/InStock",
        )
        valid = Ticket(
            price=30.0,
            purchase_url="https://good.example/ticket",
            sold_out=False,
            type="General Admission",
        )
        show = _FakeShow(42, [invalid, valid])

        handler.insert_tickets([show])

        # Two execute_with_cursor calls: schema.org cleanup, then stale-ticket sweep.
        cursor_calls = handler.execute_with_cursor.call_args_list
        assert cursor_calls[0].args == (
            TicketQueries.DELETE_INVALID_SCHEMA_ORG_TICKETS_FOR_SHOWS,
            ([42],),
        )
        inserted_tuples = handler.execute_batch_operation.call_args.args[1]
        assert len(inserted_tuples) == 1
        assert inserted_tuples[0][1] == "https://good.example/ticket"
        assert inserted_tuples[0][4] == "General Admission"

    def test_cleanup_query_survives_execute_formatting_path(self):
        """
        The schema.org cleanup query must survive DB-API style formatting.

        Raw '%' wildcards in a query that also contains %s placeholders raise
        before the statement reaches Postgres. Exercise insert_tickets() through
        an execute_with_cursor side effect that formats the query so this fails
        if the SQL regresses to unescaped wildcards.
        """
        handler = TicketHandler()
        handler.execute_batch_operation = MagicMock(return_value=None)

        formatted_queries = []

        def _execute_with_cursor(query, params, return_results=False, **_kwargs):
            # ``**_kwargs`` swallows the ``conn=`` kwarg passed by insert_tickets
            # under the single-transaction path (TASK-2410).
            formatted_queries.append(query % params)
            return None

        handler.execute_with_cursor = MagicMock(side_effect=_execute_with_cursor)

        invalid = Ticket(
            price=25.0,
            purchase_url="https://bad.example/ticket",
            sold_out=False,
            type="http://schema.org/InStock",
        )
        valid = Ticket(
            price=30.0,
            purchase_url="https://good.example/ticket",
            sold_out=False,
            type="General Admission",
        )
        show = _FakeShow(42, [invalid, valid])

        handler.insert_tickets([show])

        # Two formatted queries: schema.org cleanup + stale-ticket sweep.
        assert len(formatted_queries) == 2
        assert "http://schema.org/%" in formatted_queries[0]
        assert "https://schema.org/%" in formatted_queries[0]
        inserted_tuples = handler.execute_batch_operation.call_args.args[1]
        assert len(inserted_tuples) == 1
        assert inserted_tuples[0][1] == "https://good.example/ticket"


# ---------------------------------------------------------------------------
# Stale-ticket sweep (TASK-2397)
# ---------------------------------------------------------------------------

class TestStaleTicketSweep:
    """
    Regression: re-inserting a show with a smaller tier set must remove the
    types that are no longer in the incoming batch. Before TASK-2397, the
    BATCH_ADD upsert on (show_id, type) left previously-inserted types orphaned
    in the DB. The handler now issues DELETE_STALE_TICKETS_FOR_SHOWS before the
    upsert, keyed by the set of (show_id, type) pairs in the new batch.
    """

    @pytest.fixture(autouse=True)
    def _stub_transaction(self, monkeypatch):
        """Stub the single-transaction wrapper insert_tickets opens (TASK-2410).

        Without this, ``with self.transaction()`` calls the real
        create_connection(), which raises "Database configuration not found or
        incomplete" in CI (no DATABASE_* env). The sweep SQL is asserted via the
        per-operation execute_* mocks in each test.
        """

        @contextmanager
        def _noop_transaction(_self):
            yield MagicMock(name="tx_conn")

        monkeypatch.setattr(TicketHandler, "transaction", _noop_transaction)

    def test_shrinking_tier_set_sweeps_orphaned_types(self):
        """Show inserted with 4 tier types then re-inserted with 2 — the keep set sent to the DELETE sweep contains only the 2 surviving types."""
        show_id = 1956627  # mirrors the show ID from the TASK-2387 regression that surfaced this bug

        def _ticket(t: str) -> Ticket:
            return Ticket(price=25.0, purchase_url=f"https://example.com/{t}", sold_out=False, type=t)

        handler = TicketHandler()
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(return_value=None)

        # First insert: 4 tier types.
        show_v1 = _FakeShow(show_id, [
            _ticket("Fri 7:30pm"),
            _ticket("Fri 9:30pm"),
            _ticket("Sat 7:30pm"),
            _ticket("Sat 9:30pm"),
        ])
        handler.insert_tickets([show_v1])

        # Re-insert with only 2 tier types — simulates Tixr bundle splitter
        # re-attaching a smaller subset to the show after re-scrape.
        show_v2 = _FakeShow(show_id, [
            _ticket("Fri 7:30pm"),
            _ticket("Fri 9:30pm"),
        ])
        handler.insert_tickets([show_v2])

        # Locate the sweep call from the second insert. Each insert_tickets()
        # call emits two execute_with_cursor calls: schema.org cleanup, then
        # stale sweep. The second insert's sweep is the 4th overall call.
        cursor_calls = handler.execute_with_cursor.call_args_list
        assert len(cursor_calls) == 4

        second_sweep = cursor_calls[3]
        assert second_sweep.args[0] == TicketQueries.DELETE_STALE_TICKETS_FOR_SHOWS
        affected_show_ids, keep_show_ids, keep_types = second_sweep.args[1]
        assert affected_show_ids == [show_id]
        assert keep_show_ids == [show_id, show_id]
        assert keep_types == ["Fri 7:30pm", "Fri 9:30pm"]

        # The BATCH_ADD on the second insert must carry only the 2 surviving
        # tickets — combined with the sweep, the DB ends with exactly 2 rows.
        second_insert_tuples = handler.execute_batch_operation.call_args_list[1].args[1]
        assert len(second_insert_tuples) == 2
        assert {t[4] for t in second_insert_tuples} == {"Fri 7:30pm", "Fri 9:30pm"}

    def test_sweep_query_uses_unnest_keep_set(self):
        """The sweep query must NOT EXISTS-filter against an unnest(int[], text[]) keep set so a single round trip covers all incoming (show_id, type) pairs."""
        sql = TicketQueries.DELETE_STALE_TICKETS_FOR_SHOWS
        assert "DELETE FROM tickets" in sql
        assert "show_id = ANY(%s)" in sql
        assert "NOT EXISTS" in sql
        assert "unnest(%s::int[], %s::text[])" in sql

    def test_sweep_runs_per_show_in_multi_show_batch(self):
        """Two shows in one batch — sweep includes both show_ids and parallel arrays of their (show_id, type) keep pairs."""
        handler = TicketHandler()
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(return_value=None)

        show_a = _FakeShow(101, [
            Ticket(price=20.0, purchase_url="https://a.example/ga", sold_out=False, type="GA"),
        ])
        show_b = _FakeShow(202, [
            Ticket(price=50.0, purchase_url="https://b.example/vip", sold_out=False, type="VIP"),
            Ticket(price=30.0, purchase_url="https://b.example/ga", sold_out=False, type="GA"),
        ])
        handler.insert_tickets([show_a, show_b])

        # Sweep is the second execute_with_cursor call (after schema.org cleanup).
        sweep_call = handler.execute_with_cursor.call_args_list[1]
        assert sweep_call.args[0] == TicketQueries.DELETE_STALE_TICKETS_FOR_SHOWS
        affected_show_ids, keep_show_ids, keep_types = sweep_call.args[1]
        assert affected_show_ids == [101, 202]
        # keep_show_ids / keep_types preserve insertion order from deduplicate_tickets.
        assert list(zip(keep_show_ids, keep_types)) == [
            (101, "GA"),
            (202, "VIP"),
            (202, "GA"),
        ]

    def test_no_sweep_when_all_incoming_tickets_are_invalid_schema_org(self):
        """If every incoming ticket is filtered out as invalid schema.org, insert_tickets returns before scheduling a sweep — existing tickets for the show are left alone."""
        handler = TicketHandler()
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(return_value=None)

        show = _FakeShow(77, [
            Ticket(price=10.0, purchase_url="https://bad.example/1", sold_out=False, type="http://schema.org/InStock"),
            Ticket(price=15.0, purchase_url="https://bad.example/2", sold_out=False, type="https://schema.org/SoldOut"),
        ])
        handler.insert_tickets([show])

        # Only the schema.org cleanup runs; no sweep, no batch insert.
        assert handler.execute_with_cursor.call_count == 1
        assert handler.execute_with_cursor.call_args_list[0].args[0] == (
            TicketQueries.DELETE_INVALID_SCHEMA_ORG_TICKETS_FOR_SHOWS
        )
        handler.execute_batch_operation.assert_not_called()


# ---------------------------------------------------------------------------
# Single-transaction wrapping (TASK-2410)
# ---------------------------------------------------------------------------

class TestInsertTicketsSingleTransaction:
    """
    insert_tickets must run the schema.org cleanup, stale-ticket sweep, and
    BATCH_ADD upsert inside one DB transaction so a mid-flow failure leaves
    the show's ticket rows unchanged (TASK-2410).
    """

    def test_all_operations_share_one_connection(self):
        """All three SQL calls receive the same ``conn=`` from handler.transaction()."""
        handler = TicketHandler()
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(return_value=None)

        sentinel_conn = MagicMock(name="tx_conn")

        @contextmanager
        def _fake_transaction():
            yield sentinel_conn

        handler.transaction = _fake_transaction  # type: ignore[assignment]

        show = _FakeShow(42, [_make_ticket("https://example.com/buy")])
        handler.insert_tickets([show])

        # 2 cursor calls (schema.org cleanup + stale sweep) + 1 batch call,
        # every one with conn=sentinel_conn.
        assert handler.execute_with_cursor.call_count == 2
        for call in handler.execute_with_cursor.call_args_list:
            assert call.kwargs.get("conn") is sentinel_conn

        assert handler.execute_batch_operation.call_count == 1
        assert handler.execute_batch_operation.call_args.kwargs.get("conn") is sentinel_conn

    def test_rollback_on_batch_add_failure(self):
        """When BATCH_ADD fails after the sweep, the transaction rolls back —
        the prior DELETE statements never commit, so the show keeps its
        previous ticket rows instead of being left with zero tickets."""
        handler = TicketHandler()
        tx_conn = MagicMock(name="tx_conn")

        @contextmanager
        def _real_transaction():
            try:
                yield tx_conn
                tx_conn.commit()
            except Exception:
                tx_conn.rollback()
                raise

        handler.transaction = _real_transaction  # type: ignore[assignment]
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(
            side_effect=RuntimeError("BATCH_ADD failed")
        )

        show = _FakeShow(42, [_make_ticket("https://example.com/buy")])

        with pytest.raises(RuntimeError, match="BATCH_ADD failed"):
            handler.insert_tickets([show])

        # Cleanup + sweep both ran (and would have committed individually under
        # the pre-2410 connection-per-statement model).
        assert handler.execute_with_cursor.call_count == 2
        assert handler.execute_batch_operation.call_count == 1

        # Under the single-transaction wrap the connection rolls back, never commits.
        tx_conn.rollback.assert_called_once()
        tx_conn.commit.assert_not_called()

    def test_commit_on_clean_success(self):
        """Clean exit through the with-block commits the wrapping transaction."""
        handler = TicketHandler()
        tx_conn = MagicMock(name="tx_conn")

        @contextmanager
        def _real_transaction():
            try:
                yield tx_conn
                tx_conn.commit()
            except Exception:
                tx_conn.rollback()
                raise

        handler.transaction = _real_transaction  # type: ignore[assignment]
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(return_value=None)

        show = _FakeShow(42, [_make_ticket("https://example.com/buy")])
        handler.insert_tickets([show])

        tx_conn.commit.assert_called_once()
        tx_conn.rollback.assert_not_called()

    @pytest.mark.parametrize(
        "failing_cursor_call_index, label",
        [
            (0, "schema_org_cleanup"),
            (1, "stale_ticket_sweep"),
        ],
    )
    def test_rollback_when_execute_with_cursor_raises(self, failing_cursor_call_index, label):
        """Regression guard: if either DELETE (schema.org cleanup or the
        TASK-2397 stale-ticket sweep) fails, the wrapping transaction must
        roll back so a future refactor can't accidentally move one of the
        DELETEs outside the single transaction without a test catching it."""
        handler = TicketHandler()
        tx_conn = MagicMock(name="tx_conn")

        @contextmanager
        def _real_transaction():
            try:
                yield tx_conn
                tx_conn.commit()
            except Exception:
                tx_conn.rollback()
                raise

        handler.transaction = _real_transaction  # type: ignore[assignment]

        cursor_call_count = {"n": 0}

        def _maybe_raise(*_args, **_kwargs):
            current = cursor_call_count["n"]
            cursor_call_count["n"] += 1
            if current == failing_cursor_call_index:
                raise RuntimeError(f"{label} DELETE failed")
            return None

        handler.execute_with_cursor = MagicMock(side_effect=_maybe_raise)
        handler.execute_batch_operation = MagicMock(return_value=None)

        show = _FakeShow(42, [_make_ticket("https://example.com/buy")])

        with pytest.raises(RuntimeError, match=f"{label} DELETE failed"):
            handler.insert_tickets([show])

        # Transaction rolled back, did not commit.
        tx_conn.rollback.assert_called_once()
        tx_conn.commit.assert_not_called()

        # If the sweep was the failing call, the schema.org cleanup ran first;
        # if the cleanup was the failing call, no further SQL ran.
        assert handler.execute_with_cursor.call_count == failing_cursor_call_index + 1
        handler.execute_batch_operation.assert_not_called()

    def test_early_return_after_schema_org_cleanup_still_commits(self):
        """When every incoming ticket is filtered out as invalid schema.org,
        insert_tickets returns from inside the transaction block — the
        cleanup DELETE that already ran must commit, not roll back."""
        handler = TicketHandler()
        tx_conn = MagicMock(name="tx_conn")

        @contextmanager
        def _real_transaction():
            try:
                yield tx_conn
                tx_conn.commit()
            except Exception:
                tx_conn.rollback()
                raise

        handler.transaction = _real_transaction  # type: ignore[assignment]
        handler.execute_with_cursor = MagicMock(return_value=None)
        handler.execute_batch_operation = MagicMock(return_value=None)

        show = _FakeShow(77, [
            Ticket(price=10.0, purchase_url="https://bad.example/1", sold_out=False, type="http://schema.org/InStock"),
        ])
        handler.insert_tickets([show])

        # Only schema.org cleanup ran — no sweep, no batch insert.
        assert handler.execute_with_cursor.call_count == 1
        handler.execute_batch_operation.assert_not_called()

        # ...but the cleanup commits via the wrapping transaction's clean exit.
        tx_conn.commit.assert_called_once()
        tx_conn.rollback.assert_not_called()
