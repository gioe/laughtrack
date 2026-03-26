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
        pkg_path = str(_SCRAPER_ROOT / "src" / name.replace(".", "/"))
        m.__path__ = [pkg_path]
        m.__package__ = name
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


# ---------------------------------------------------------------------------
# Stubs required for loading lineup/handler.py and show/handler.py
# ---------------------------------------------------------------------------
_stub("laughtrack.foundation.protocols.database_entity", DatabaseEntity=object)
_stub("laughtrack.foundation.protocols", as_package=True, DatabaseEntity=object)
_stub("laughtrack.foundation.infrastructure.logger.logger", Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure.logger", as_package=True, Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure", as_package=True, Logger=MagicMock())
_stub("laughtrack.foundation.utilities.popularity.scorer", PopularityScorer=MagicMock())
_stub("laughtrack.foundation.utilities.popularity", as_package=True, PopularityScorer=MagicMock())
_stub("laughtrack.foundation.utilities.string", StringUtils=MagicMock())
_stub("laughtrack.foundation.utilities", as_package=True, StringUtils=MagicMock())
_stub("laughtrack.foundation", as_package=True, DatabaseEntity=object)
_stub("laughtrack.foundation.infrastructure.database.template", BatchTemplateGenerator=MagicMock())
_stub("laughtrack.foundation.infrastructure.database.operation", DatabaseOperationLogger=MagicMock())
_stub("laughtrack.foundation.models.operation_result", DatabaseOperationResult=MagicMock)
_stub("laughtrack.utilities.domain.comedian.utils", ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain.comedian", as_package=True, ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain.show.utils", ShowUtils=MagicMock())
_stub("laughtrack.utilities.domain.show", as_package=True, ShowUtils=MagicMock())
_stub("laughtrack.utilities.domain", as_package=True, ComedianUtils=MagicMock())
_stub("laughtrack.utilities", as_package=True, ComedianUtils=MagicMock())

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
_stub("laughtrack.core.data", as_package=True, BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core", as_package=True, BaseDatabaseHandler=_BaseDatabaseHandlerStub)

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
                mock_lineup.side_effect = lambda *a, **kw: (call_order.append("lineups"), (0, 0))[1]
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
            with patch.object(h, "update_show_lineups", return_value=(3, 7)) as mock_lineup:
                result_shows, comedians_inserted, lineup_items_added = h._update_shows_and_related(
                    [MagicMock()], [MagicMock()]
                )
                mock_lineup.assert_called_once_with(updated)
                assert result_shows == updated, "_update_shows_and_related must return the updated shows list"
                assert comedians_inserted == 3
                assert lineup_items_added == 7


# ---------------------------------------------------------------------------
# Tests: LineupHandler.batch_update_lineups — lineup mutation (add/remove)
# ---------------------------------------------------------------------------

class TestBatchUpdateLineupsLineupMutation:
    def _make_handler(self):
        h = _make_lineup_handler()
        h.batch_add_lineup_items = MagicMock()
        h.batch_delete_lineup_items = MagicMock()
        return h

    def test_batch_add_lineup_items_called_with_correct_items_when_comedian_added(self):
        """batch_add_lineup_items receives the LineupItem for each newly added comedian."""
        h = self._make_handler()

        new_comedian = MagicMock()
        new_comedian.uuid = "uuid-new"

        show = MagicMock()
        show.id = 1
        show.lineup = [new_comedian]

        sentinel = object()
        with patch.object(_lineup_handler_mod.LineupItem, "create_lineup_item", return_value=sentinel) as mock_create:
            result = h.batch_update_lineups(
                shows=[show],
                current_lineups={},  # empty — comedian is new
            )

        mock_create.assert_called_once_with(1, "uuid-new")
        h.batch_add_lineup_items.assert_called_once_with([sentinel])
        h.batch_delete_lineup_items.assert_not_called()
        assert result == (1, 0), "should return (items_added=1, items_removed=0)"

    def test_batch_delete_lineup_items_called_with_correct_items_when_comedian_removed(self):
        """batch_delete_lineup_items receives the LineupItem for each departed comedian."""
        h = self._make_handler()

        old_comedian = MagicMock()
        old_comedian.uuid = "uuid-old"

        show = MagicMock()
        show.id = 5
        show.lineup = []  # comedian has left

        sentinel = object()
        with patch.object(_lineup_handler_mod.LineupItem, "create_lineup_item", return_value=sentinel) as mock_create:
            result = h.batch_update_lineups(
                shows=[show],
                current_lineups={5: [old_comedian]},
            )

        mock_create.assert_called_once_with(5, "uuid-old")
        h.batch_delete_lineup_items.assert_called_once_with([sentinel])
        h.batch_add_lineup_items.assert_not_called()
        assert result == (0, 1), "should return (items_added=0, items_removed=1)"

    def test_neither_add_nor_delete_called_when_lineup_unchanged(self):
        """No mutation calls when the new lineup matches the current lineup exactly."""
        h = self._make_handler()

        comedian = MagicMock()
        comedian.uuid = "uuid-same"

        current_comedian = MagicMock()
        current_comedian.uuid = "uuid-same"

        show = MagicMock()
        show.id = 9
        show.lineup = [comedian]

        result = h.batch_update_lineups(
            shows=[show],
            current_lineups={9: [current_comedian]},
        )

        h.batch_add_lineup_items.assert_not_called()
        h.batch_delete_lineup_items.assert_not_called()
        assert result == (0, 0), "should return (items_added=0, items_removed=0)"


# ---------------------------------------------------------------------------
# Tests: DatabaseOperationResult — new comedian/lineup count fields
# ---------------------------------------------------------------------------

# Stubs needed for operation_result.py's transitive imports
_stub("laughtrack.foundation.models.types", DuplicateKeyDetails=MagicMock())
_stub("laughtrack.foundation.models", DuplicateKeyDetails=MagicMock(), as_package=True)

_operation_result_mod = _load_module(
    "src/laughtrack/foundation/models/operation_result.py",
    "laughtrack.foundation.models.operation_result_direct",
)
_RealDatabaseOperationResult = _operation_result_mod.DatabaseOperationResult


class TestDatabaseOperationResultComedianLineupFields:
    def test_comedians_inserted_defaults_to_zero(self):
        r = _RealDatabaseOperationResult()
        assert r.comedians_inserted == 0

    def test_lineup_items_added_defaults_to_zero(self):
        r = _RealDatabaseOperationResult()
        assert r.lineup_items_added == 0

    def test_add_sums_comedians_inserted(self):
        a = _RealDatabaseOperationResult(comedians_inserted=3)
        b = _RealDatabaseOperationResult(comedians_inserted=5)
        result = a + b
        assert result.comedians_inserted == 8

    def test_add_sums_lineup_items_added(self):
        a = _RealDatabaseOperationResult(lineup_items_added=10)
        b = _RealDatabaseOperationResult(lineup_items_added=7)
        result = a + b
        assert result.lineup_items_added == 17

    def test_add_preserves_existing_fields(self):
        a = _RealDatabaseOperationResult(inserts=2, comedians_inserted=1, lineup_items_added=4)
        b = _RealDatabaseOperationResult(inserts=3, comedians_inserted=2, lineup_items_added=6)
        result = a + b
        assert result.inserts == 5
        assert result.comedians_inserted == 3
        assert result.lineup_items_added == 10


# ---------------------------------------------------------------------------
# Tests: update_show_lineups — denied comedians stripped from show.lineup
# ---------------------------------------------------------------------------

def _make_comedian_stub(name: str, uuid: str):
    """Return a minimal comedian-like object with name and uuid."""
    c = MagicMock()
    c.name = name
    c.uuid = uuid
    return c


def _make_show_stub(show_id: int, comedians):
    """Return a minimal show-like object with id, name, and lineup list."""
    s = MagicMock()
    s.id = show_id
    s.name = f"Show {show_id}"
    s.lineup = list(comedians)
    return s


class TestUpdateShowLineupsStripsdeniedComedians:
    """update_show_lineups must remove deny-listed comedians from show.lineup
    before calling batch_update_lineups to prevent FK violations."""

    def _make_handler_for_lineup_update(self):
        h = _make_show_handler()
        h.lineup_handler.get_lineup.return_value = {}
        h.lineup_handler.get_comedians_from_show_names.return_value = {}
        h.lineup_handler.batch_update_lineups.return_value = (0, 0)
        h.comedian_handler.insert_comedians.return_value = []
        h.calculate_and_update_popularity = MagicMock()
        return h

    def test_denied_comedian_absent_from_lineup_when_batch_update_called(self):
        """show.lineup must not contain the denied comedian when batch_update_lineups runs."""
        allowed = _make_comedian_stub("Allowed Comic", "uuid-allowed")
        denied = _make_comedian_stub("Denied Comic", "uuid-denied")
        show = _make_show_stub(1, [allowed, denied])

        h = self._make_handler_for_lineup_update()
        h._extract_valid_show_ids = MagicMock(return_value=[1])
        h._process_comedian_additions = MagicMock()

        # _filter_denied_comedians returns only the allowed comedian
        h.comedian_handler._filter_denied_comedians.return_value = [allowed]
        # false-positive filter passes allowed through unchanged
        h.comedian_handler._filter_false_positive_comedians.return_value = [allowed]

        lineup_at_call_time = []

        def capture_lineup(shows, db_lineups):
            lineup_at_call_time.extend(list(shows[0].lineup))
            return (1, 0)

        h.lineup_handler.batch_update_lineups.side_effect = capture_lineup

        with patch.object(_show_handler_mod.ShowUtils, "collect_comedian_uuids", return_value=[]):
            h.update_show_lineups([show])

        names_at_call = [c.name for c in lineup_at_call_time]
        assert "Denied Comic" not in names_at_call, (
            "Denied comedian must be stripped from show.lineup before batch_update_lineups"
        )
        assert "Allowed Comic" in names_at_call, (
            "Allowed comedian must still be present in show.lineup"
        )

    def test_non_denied_comedians_still_linked_when_some_denied(self):
        """batch_update_lineups is still called with non-denied comedians intact."""
        allowed_a = _make_comedian_stub("Comic A", "uuid-a")
        allowed_b = _make_comedian_stub("Comic B", "uuid-b")
        denied = _make_comedian_stub("Junk Token", "uuid-junk")
        show = _make_show_stub(2, [allowed_a, denied, allowed_b])

        h = self._make_handler_for_lineup_update()
        h._extract_valid_show_ids = MagicMock(return_value=[2])
        h._process_comedian_additions = MagicMock()
        h.comedian_handler._filter_denied_comedians.return_value = [allowed_a, allowed_b]
        h.comedian_handler._filter_false_positive_comedians.return_value = [allowed_a, allowed_b]
        h.comedian_handler.insert_comedians.return_value = [{"uuid": "uuid-a"}]

        lineup_names = []

        def capture(shows, db_lineups):
            lineup_names.extend(c.name for c in shows[0].lineup)
            return (2, 0)

        h.lineup_handler.batch_update_lineups.side_effect = capture

        with patch.object(_show_handler_mod.ShowUtils, "collect_comedian_uuids", return_value=[]):
            h.update_show_lineups([show])

        assert "Comic A" in lineup_names
        assert "Comic B" in lineup_names
        assert "Junk Token" not in lineup_names

    def test_no_lineup_stripping_when_no_comedians_denied(self):
        """When all comedians are allowed, batch_update_lineups sees the full lineup unchanged."""
        c1 = _make_comedian_stub("Comic One", "uuid-1")
        c2 = _make_comedian_stub("Comic Two", "uuid-2")
        show = _make_show_stub(3, [c1, c2])

        h = self._make_handler_for_lineup_update()
        h._extract_valid_show_ids = MagicMock(return_value=[3])
        h._process_comedian_additions = MagicMock()
        # All comedians allowed — filter returns the same list
        h.comedian_handler._filter_denied_comedians.return_value = [c1, c2]
        h.comedian_handler._filter_false_positive_comedians.return_value = [c1, c2]

        lineup_names = []

        def capture(shows, db_lineups):
            lineup_names.extend(c.name for c in shows[0].lineup)
            return (2, 0)

        h.lineup_handler.batch_update_lineups.side_effect = capture

        with patch.object(_show_handler_mod.ShowUtils, "collect_comedian_uuids", return_value=[]):
            h.update_show_lineups([show])

        assert "Comic One" in lineup_names
        assert "Comic Two" in lineup_names


# ---------------------------------------------------------------------------
# Tests: update_show_lineups — false-positive comedians stripped from show.lineup
# ---------------------------------------------------------------------------

class TestUpdateShowLineupsStripsFalsePositiveComedians:
    """update_show_lineups must remove false-positive comedians from show.lineup
    before calling batch_update_lineups to prevent FK violations.

    Regression test for comedian_id=99d0c876e6d2827b8c565659651c8233:
    the comedian was filtered by insert_comedians() internally (false positive)
    but not stripped from show.lineup, causing a lineup_items FK violation on
    every Eventbrite scrape run.
    """

    def _make_handler_for_lineup_update(self):
        h = _make_show_handler()
        h.lineup_handler.get_lineup.return_value = {}
        h.lineup_handler.get_comedians_from_show_names.return_value = {}
        h.lineup_handler.batch_update_lineups.return_value = (0, 0)
        h.comedian_handler.insert_comedians.return_value = []
        h.calculate_and_update_popularity = MagicMock()
        return h

    def test_false_positive_comedian_absent_from_lineup_when_batch_update_called(self):
        """show.lineup must not contain the false-positive comedian when batch_update_lineups runs."""
        allowed = _make_comedian_stub("Real Comedian", "uuid-real")
        fp = _make_comedian_stub("Improv Showcase", "uuid-fp")  # contains structural keyword
        show = _make_show_stub(1, [allowed, fp])

        h = self._make_handler_for_lineup_update()
        h._extract_valid_show_ids = MagicMock(return_value=[1])
        h._process_comedian_additions = MagicMock()
        # deny filter passes both through
        h.comedian_handler._filter_denied_comedians.return_value = [allowed, fp]
        # false-positive filter removes the structural-keyword name
        h.comedian_handler._filter_false_positive_comedians.return_value = [allowed]

        lineup_at_call_time = []

        def capture_lineup(shows, db_lineups):
            lineup_at_call_time.extend(list(shows[0].lineup))
            return (1, 0)

        h.lineup_handler.batch_update_lineups.side_effect = capture_lineup

        with patch.object(_show_handler_mod.ShowUtils, "collect_comedian_uuids", return_value=[]):
            h.update_show_lineups([show])

        names_at_call = [c.name for c in lineup_at_call_time]
        assert "Improv Showcase" not in names_at_call, (
            "False-positive comedian must be stripped from show.lineup before batch_update_lineups"
        )
        assert "Real Comedian" in names_at_call, (
            "Real comedian must still be present in show.lineup"
        )

    def test_real_comedians_intact_when_some_false_positive(self):
        """batch_update_lineups is called with non-false-positive comedians intact."""
        c1 = _make_comedian_stub("Comic A", "uuid-a")
        c2 = _make_comedian_stub("Comic B", "uuid-b")
        fp = _make_comedian_stub("Westside Comedy Theater", "uuid-fp")  # theater keyword
        show = _make_show_stub(2, [c1, fp, c2])

        h = self._make_handler_for_lineup_update()
        h._extract_valid_show_ids = MagicMock(return_value=[2])
        h._process_comedian_additions = MagicMock()
        h.comedian_handler._filter_denied_comedians.return_value = [c1, fp, c2]
        h.comedian_handler._filter_false_positive_comedians.return_value = [c1, c2]

        lineup_names = []

        def capture(shows, db_lineups):
            lineup_names.extend(c.name for c in shows[0].lineup)
            return (2, 0)

        h.lineup_handler.batch_update_lineups.side_effect = capture

        with patch.object(_show_handler_mod.ShowUtils, "collect_comedian_uuids", return_value=[]):
            h.update_show_lineups([show])

        assert "Comic A" in lineup_names
        assert "Comic B" in lineup_names
        assert "Westside Comedy Theater" not in lineup_names
