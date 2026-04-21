"""
Unit tests for TicketHandler.insert_tickets.

Covers:
- SQL contract: BATCH_ADD_TICKETS must include purchase_url = EXCLUDED.purchase_url
- Upsert behaviour: calling insert_tickets twice with the same (show_id, type) but a
  different purchase_url passes the updated URL to execute_batch_operation on the
  second call (regression guard for TASK-709 upsert fix).
"""

import sys
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

        handler.execute_with_cursor.assert_called_once_with(
            TicketQueries.DELETE_INVALID_SCHEMA_ORG_TICKETS_FOR_SHOWS,
            ([42],),
        )
        inserted_tuples = handler.execute_batch_operation.call_args.args[1]
        assert len(inserted_tuples) == 1
        assert inserted_tuples[0][1] == "https://good.example/ticket"
        assert inserted_tuples[0][4] == "General Admission"
