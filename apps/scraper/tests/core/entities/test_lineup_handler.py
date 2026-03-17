"""
Unit tests for LineupHandler and ShowHandler lineup pipeline wiring.

Covers:
- get_lineup(): returns {} when no existing lineup rows exist (no ValueError)
- get_comedians_from_show_names(): returns {} when no comedian names match (no ValueError)
- ShowHandler._update_shows_and_related(): calls update_show_lineups after tickets and tags
"""

import importlib.util
import sys
from abc import ABC as _ABC, abstractmethod as _abstractmethod
from pathlib import Path
from types import ModuleType
from typing import Generic as _Generic, TypeVar as _TypeVar
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Load source modules directly, bypassing __init__.py chains that need a live DB
# ---------------------------------------------------------------------------
_SCRAPER_ROOT = Path(__file__).parents[3]  # apps/scraper/


def _load_module(rel_path: str, module_name: str):
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = _SCRAPER_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(module_name, mod)
    _ensure_psycopg2_stubbed()
    spec.loader.exec_module(mod)
    return mod


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
        sys.modules.setdefault("psycopg2", psycopg2)
        sys.modules.setdefault("psycopg2.extras", extras)
        sys.modules.setdefault("psycopg2.extensions", extensions)


def _stub(name: str, as_package: bool = False, **attrs):
    m = ModuleType(name)
    if as_package:
        m.__path__ = []  # makes Python treat it as a package
        m.__package__ = name
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


# ---------------------------------------------------------------------------
# Stubs required for loading lineup/handler.py and show/handler.py
# ---------------------------------------------------------------------------
_stub("laughtrack.foundation.protocols.database_entity", DatabaseEntity=object)
_stub("laughtrack.foundation.protocols", DatabaseEntity=object)
_stub("laughtrack.foundation.infrastructure.logger.logger", Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure.logger", Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure", Logger=MagicMock())
_stub("laughtrack.foundation.utilities.popularity.scorer", PopularityScorer=MagicMock())
_stub("laughtrack.foundation.utilities.popularity", PopularityScorer=MagicMock())
_stub("laughtrack.foundation.utilities.string", StringUtils=MagicMock())
_stub("laughtrack.foundation.utilities", StringUtils=MagicMock())
_stub("laughtrack.foundation", DatabaseEntity=object)
_stub("laughtrack.foundation.infrastructure.database.template", BatchTemplateGenerator=MagicMock())
_stub("laughtrack.foundation.infrastructure.database.operation", DatabaseOperationLogger=MagicMock())
_stub("laughtrack.foundation.models.operation_result", DatabaseOperationResult=MagicMock)
_stub("laughtrack.utilities.domain.comedian.utils", ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain.comedian", ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain.show.utils", ShowUtils=MagicMock())
_stub("laughtrack.utilities.domain.show", ShowUtils=MagicMock())
_stub("laughtrack.utilities.domain", ComedianUtils=MagicMock())
_stub("laughtrack.utilities", ComedianUtils=MagicMock())

# Stub BaseDatabaseHandler
_T_stub = _TypeVar("_T_stub")


class _BaseDatabaseHandlerStub(_Generic[_T_stub], _ABC):
    def __init__(self) -> None:
        pass

    @_abstractmethod
    def get_entity_name(self) -> str: ...

    @_abstractmethod
    def get_entity_class(self): ...

    def execute_with_cursor(self, operation, params=None, return_results=False):
        raise NotImplementedError

    def execute_batch_operation(self, query, items, template=None, return_results=False, log_summary=True):
        raise NotImplementedError

    def _get_cursor_factory(self):
        return dict


_stub("laughtrack.core.data.base_handler", BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core.data", BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core", BaseDatabaseHandler=_BaseDatabaseHandlerStub)

# Comedian model and handler stubs — must be package-style so submodule imports work
_comedian_pkg = _stub("laughtrack.core.entities.comedian", Comedian=MagicMock())
_comedian_model_stub = _stub("laughtrack.core.entities.comedian.model", Comedian=MagicMock())
_comedian_handler_stub_mod = _stub("laughtrack.core.entities.comedian.handler", ComedianHandler=MagicMock())

# SQL query stubs
_lineup_queries_stub = _stub("sql.lineup_queries", LineupQueries=MagicMock())
_show_queries_stub = _stub("sql.show_queries", ShowQueries=MagicMock())
_comedian_queries_stub = _stub("sql.comedian_queries", ComedianQueries=MagicMock())
_tag_queries_stub = _stub("sql.tag_queries", TagQueries=MagicMock())
_ticket_queries_stub = _stub("sql.ticket_queries", TicketQueries=MagicMock())
_stub("sql", LineupQueries=MagicMock())

# Handler stubs (needed for ShowHandler.__init__ dependencies)
_stub("laughtrack.core.entities.tag.handler", TagHandler=MagicMock())
_stub("laughtrack.core.entities.tag", as_package=True, TagHandler=MagicMock())
_stub("laughtrack.core.entities.ticket.handler", TicketHandler=MagicMock())
_stub("laughtrack.core.entities.ticket", as_package=True, TicketHandler=MagicMock())
_stub("laughtrack.core.entities.show.model", Show=MagicMock())
_stub("laughtrack.core.entities.show", as_package=True, Show=MagicMock())
# lineup package + model (needed for relative import `from .model import LineupItem`)
_stub("laughtrack.core.entities.lineup.model", LineupItem=MagicMock())
_stub("laughtrack.core.entities.lineup", as_package=True)
_stub("laughtrack.core.entities", as_package=True, Comedian=None)

# Load LineupHandler — register under both canonical and direct names
_lineup_handler_mod = _load_module(
    "src/laughtrack/core/entities/lineup/handler.py",
    "laughtrack.core.entities.lineup.handler_direct",
)
# Also register under canonical name so show/handler.py can import it
sys.modules.setdefault("laughtrack.core.entities.lineup.handler", _lineup_handler_mod)
LineupHandler = _lineup_handler_mod.LineupHandler

# Load ShowHandler
_show_handler_mod = _load_module(
    "src/laughtrack/core/entities/show/handler.py",
    "laughtrack.core.entities.show.handler_direct",
)
ShowHandler = _show_handler_mod.ShowHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_lineup_handler() -> LineupHandler:
    """Return a LineupHandler with all DB methods patched."""
    h = LineupHandler.__new__(LineupHandler)
    h.execute_with_cursor = MagicMock()
    h.execute_batch_operation = MagicMock()
    return h


def _make_show_handler() -> ShowHandler:
    """Return a ShowHandler with sub-handlers replaced by mocks."""
    h = ShowHandler.__new__(ShowHandler)
    h.ticket_handler = MagicMock()
    h.tag_handler = MagicMock()
    h.lineup_handler = MagicMock()
    h.comedian_handler = MagicMock()
    return h


# ---------------------------------------------------------------------------
# Tests: LineupHandler.get_lineup — empty results → {}
# ---------------------------------------------------------------------------

class TestGetLineupEmptyResults:
    def test_returns_empty_dict_when_no_rows(self):
        h = _make_lineup_handler()
        h.execute_with_cursor.return_value = []

        result = h.get_lineup([1, 2, 3])

        assert result == {}

    def test_returns_empty_dict_when_execute_returns_none(self):
        h = _make_lineup_handler()
        h.execute_with_cursor.return_value = None

        result = h.get_lineup([1, 2, 3])

        assert result == {}

    def test_does_not_raise_valueerror_on_empty(self):
        h = _make_lineup_handler()
        h.execute_with_cursor.return_value = []

        # Should not raise
        h.get_lineup([99])


# ---------------------------------------------------------------------------
# Tests: LineupHandler.get_comedians_from_show_names — empty results → {}
# ---------------------------------------------------------------------------

class TestGetComediansFromShowNamesEmptyResults:
    def test_returns_empty_dict_when_no_rows(self):
        h = _make_lineup_handler()
        h.execute_batch_operation.return_value = []

        result = h.get_comedians_from_show_names([("The Dirty Show",)])

        assert result == {}

    def test_returns_empty_dict_when_execute_returns_none(self):
        h = _make_lineup_handler()
        h.execute_batch_operation.return_value = None

        result = h.get_comedians_from_show_names([("Generic Show",)])

        assert result == {}

    def test_does_not_raise_valueerror_on_empty(self):
        h = _make_lineup_handler()
        h.execute_batch_operation.return_value = []

        # Should not raise
        h.get_comedians_from_show_names([("No Match",)])


# ---------------------------------------------------------------------------
# Tests: get_lineup() happy path — mapping logic
# ---------------------------------------------------------------------------

class TestGetLineupHappyPath:
    def test_maps_show_id_to_comedian_list(self):
        """Verify the dict comprehension correctly maps show_id → [Comedian, ...]."""
        h = _make_lineup_handler()
        mock_comedian = MagicMock()

        h.execute_with_cursor.return_value = [
            {"show_id": 42, "lineup": [{"name": "Alice"}, {"name": "Bob"}]},
        ]

        with patch.object(_lineup_handler_mod.Comedian, "from_db_row", return_value=mock_comedian):
            result = h.get_lineup([42])

        assert 42 in result
        assert len(result[42]) == 2
        assert result[42][0] is mock_comedian

    def test_multiple_shows_returned(self):
        h = _make_lineup_handler()
        comedian_a, comedian_b = MagicMock(), MagicMock()

        h.execute_with_cursor.return_value = [
            {"show_id": 1, "lineup": [{"name": "Alice"}]},
            {"show_id": 2, "lineup": [{"name": "Bob"}]},
        ]

        with patch.object(_lineup_handler_mod.Comedian, "from_db_row", side_effect=[comedian_a, comedian_b]):
            result = h.get_lineup([1, 2])

        assert set(result.keys()) == {1, 2}


# ---------------------------------------------------------------------------
# Tests: get_comedians_from_show_names() happy path — mapping logic
# ---------------------------------------------------------------------------

class TestGetComediansFromShowNamesHappyPath:
    def test_maps_show_name_to_comedian_list(self):
        h = _make_lineup_handler()
        mock_comedian = MagicMock()

        h.execute_batch_operation.return_value = [
            {"show_name": "Comedy Night"},
        ]

        with patch.object(_lineup_handler_mod.Comedian, "from_db_row", return_value=mock_comedian):
            result = h.get_comedians_from_show_names([("Comedy Night",)])

        assert "Comedy Night" in result
        assert result["Comedy Night"] == [mock_comedian]

    def test_groups_multiple_comedians_under_same_show_name(self):
        h = _make_lineup_handler()
        c1, c2 = MagicMock(), MagicMock()

        h.execute_batch_operation.return_value = [
            {"show_name": "Late Night"},
            {"show_name": "Late Night"},
        ]

        with patch.object(_lineup_handler_mod.Comedian, "from_db_row", side_effect=[c1, c2]):
            result = h.get_comedians_from_show_names([("Late Night",)])

        assert len(result["Late Night"]) == 2
        assert result["Late Night"] == [c1, c2]


# ---------------------------------------------------------------------------
# Tests: ShowHandler._update_shows_and_related — calls update_show_lineups
# ---------------------------------------------------------------------------

class TestUpdateShowsAndRelatedCallsLineup:
    def test_calls_update_show_lineups_after_tickets_and_tags(self):
        h = _make_show_handler()
        call_order = []

        h.ticket_handler.insert_tickets.side_effect = lambda *a, **kw: call_order.append("tickets")
        h.tag_handler.process_show_tags.side_effect = lambda *a, **kw: call_order.append("tags")

        shows = [MagicMock(), MagicMock()]
        results = [MagicMock(), MagicMock()]

        # Patch ShowUtils.update_shows_with_results to return our shows
        with patch.object(
            _show_handler_mod.ShowUtils,
            "update_shows_with_results",
            return_value=shows,
        ):
            with patch.object(h, "update_show_lineups") as mock_lineup:
                mock_lineup.side_effect = lambda *a, **kw: call_order.append("lineups")
                h._update_shows_and_related(shows, results)

        assert "lineups" in call_order, "update_show_lineups was not called"
        assert call_order.index("tickets") < call_order.index("lineups"), \
            "tickets must be processed before lineups"
        assert call_order.index("tags") < call_order.index("lineups"), \
            "tags must be processed before lineups"

    def test_update_show_lineups_receives_updated_shows(self):
        h = _make_show_handler()
        updated = [MagicMock(id=1), MagicMock(id=2)]

        with patch.object(
            _show_handler_mod.ShowUtils,
            "update_shows_with_results",
            return_value=updated,
        ):
            with patch.object(h, "update_show_lineups") as mock_lineup:
                result = h._update_shows_and_related([MagicMock()], [MagicMock()])
                mock_lineup.assert_called_once_with(updated)
                assert result == updated, "_update_shows_and_related must return the updated shows list"
