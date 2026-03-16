"""
Unit tests for ComedianHandler.

Covers:
- insert_comedians: DO NOTHING on conflict contract (stub names never overwrite existing data)
- _fetch_recency_scores: happy path, empty results, exception propagation
- update_comedian_popularity: recency map applied; absent comedians default to 0.0
"""

import importlib.util
import sys
from abc import ABC as _ABC, abstractmethod as _abstractmethod
from pathlib import Path
from types import ModuleType
from typing import Generic as _Generic, TypeVar as _TypeVar
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Load source modules directly from file, bypassing package __init__.py
# chains that require a live DB environment.
# ---------------------------------------------------------------------------
_SCRAPER_ROOT = Path(__file__).parents[3]  # apps/scraper/


def _load_module(rel_path: str, module_name: str):
    """Import a single .py file as a module without triggering __init__.py chains."""
    path = _SCRAPER_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    # Stub psycopg2 if needed before execution
    _ensure_psycopg2_stubbed()
    spec.loader.exec_module(mod)
    return mod


def _ensure_psycopg2_stubbed():
    if "psycopg2" not in sys.modules:
        psycopg2 = ModuleType("psycopg2")
        extras = ModuleType("psycopg2.extras")
        extras.DictRow = dict  # type: ignore[attr-defined]
        extras.execute_values = MagicMock()
        extensions = ModuleType("psycopg2.extensions")
        extensions.connection = object  # type: ignore[attr-defined]
        psycopg2.extras = extras  # type: ignore[attr-defined]
        psycopg2.extensions = extensions  # type: ignore[attr-defined]
        sys.modules["psycopg2"] = psycopg2
        sys.modules["psycopg2.extras"] = extras
        sys.modules["psycopg2.extensions"] = extensions


# Stub foundation modules that comedian model needs
def _stub(name: str, **attrs):
    m = ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


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
_stub("laughtrack.utilities.domain.comedian.utils", ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain.comedian", ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain", ComedianUtils=MagicMock())
_stub("laughtrack.utilities", ComedianUtils=MagicMock())

# Load comedian model directly (bypasses comedian __init__.py which pulls in handler)
_comedian_model_mod = _load_module("src/laughtrack/core/entities/comedian/model.py",
                                   "laughtrack.core.entities.comedian.model_direct")
Comedian = _comedian_model_mod.Comedian

# Load ComedianQueries directly (no deps)
_comedian_queries_mod = _load_module("sql/comedian_queries.py", "sql.comedian_queries_direct")
ComedianQueries = _comedian_queries_mod.ComedianQueries

# ---------------------------------------------------------------------------
# Additional stubs for ComedianHandler loading
# ---------------------------------------------------------------------------

# Register model and queries under canonical import paths so handler.py relative imports resolve
sys.modules.setdefault("laughtrack.core.entities.comedian.model", _comedian_model_mod)
sys.modules.setdefault("sql", _comedian_queries_mod)
sys.modules.setdefault("sql.comedian_queries", _comedian_queries_mod)

# Stub BatchTemplateGenerator (used by insert_comedians, not under test here)
_stub("laughtrack.foundation.infrastructure.database", BatchTemplateGenerator=MagicMock())
_stub("laughtrack.foundation.infrastructure.database.template", BatchTemplateGenerator=MagicMock())
_stub("laughtrack.foundation.infrastructure.database.operation", DatabaseOperationLogger=MagicMock())

# Stub BaseDatabaseHandler so handler.py loads without a live DB
_T_stub = _TypeVar("_T_stub")


class _BaseDatabaseHandlerStub(_Generic[_T_stub], _ABC):
    """Minimal stand-in for BaseDatabaseHandler used only during module loading."""

    def __init__(self) -> None:
        pass

    @_abstractmethod
    def get_entity_name(self) -> str: ...

    @_abstractmethod
    def get_entity_class(self): ...

    def execute_with_cursor(self, operation, params=None, return_results=False):
        raise NotImplementedError  # always patched in tests

    def execute_batch_operation(self, query, items, template=None, return_results=False, log_summary=True):
        raise NotImplementedError  # always patched in tests

    def _get_cursor_factory(self):
        return dict


_stub("laughtrack.core.data.base_handler", BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core.data", BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core", BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core.entities", Comedian=None)
_stub("laughtrack.core.entities.comedian", Comedian=None)

# Load ComedianHandler
_comedian_handler_mod = _load_module(
    "src/laughtrack/core/entities/comedian/handler.py",
    "laughtrack.core.entities.comedian.handler_direct",
)
ComedianHandler = _comedian_handler_mod.ComedianHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid_for(name: str) -> str:
    """Replicate the deterministic UUID logic for test assertions."""
    import hashlib
    normalized = name.lower().strip()
    return str(hashlib.md5(normalized.encode()).hexdigest())


def _make_stub(name: str) -> Comedian:
    """Create a name-only comedian stub as produced by lineup extraction."""
    c = Comedian.__new__(Comedian)
    # Set defaults matching the dataclass definition
    c.name = name
    c.uuid = None
    c.sold_out_shows = 0
    c.total_shows = 0
    c.instagram_followers = None
    c.tiktok_followers = None
    c.youtube_followers = None
    c.instagram_account = None
    c.tiktok_account = None
    c.youtube_account = None
    c.website = None
    c.linktree = None
    c.parent_comedian_id = None
    c.recency_score = 0.0
    return c


def _make_full_comedian(name: str) -> Comedian:
    """Create a comedian with social/follower data."""
    c = _make_stub(name)
    c.instagram_followers = 50_000
    c.tiktok_followers = 120_000
    c.sold_out_shows = 3
    c.total_shows = 10
    return c


# ---------------------------------------------------------------------------
# SQL-level contract
# ---------------------------------------------------------------------------

class TestBatchAddComediansSql:
    def test_uses_do_nothing_on_conflict(self):
        """Regression guard: BATCH_ADD_COMEDIANS must use DO NOTHING, not DO UPDATE."""
        sql = ComedianQueries.BATCH_ADD_COMEDIANS.upper()
        assert "DO NOTHING" in sql, "Expected ON CONFLICT DO NOTHING in BATCH_ADD_COMEDIANS"
        assert "DO UPDATE" not in sql, "DO UPDATE would overwrite existing comedian data"

    def test_inserts_only_base_fields(self):
        """The INSERT column list must not include social/follower fields."""
        import re
        match = re.search(r"INSERT INTO comedians\s*\(([^)]+)\)", ComedianQueries.BATCH_ADD_COMEDIANS, re.I)
        assert match, "Could not find INSERT column list"
        cols = [c.strip().lower() for c in match.group(1).split(",")]
        for social_field in ("instagram_followers", "tiktok_followers", "youtube_followers",
                             "instagram_account", "tiktok_account", "youtube_account"):
            assert social_field not in cols, (
                f"Social field '{social_field}' must not be in INSERT to avoid overwriting existing data"
            )


# ---------------------------------------------------------------------------
# Model-level contract
# ---------------------------------------------------------------------------

class TestComedianInsertTuple:
    def test_to_insert_tuple_excludes_social_fields(self):
        """to_insert_tuple() must only include (uuid, name, sold_out_shows, total_shows)."""
        comedian = _make_full_comedian("Amy Schumer")
        comedian.uuid = "test-uuid-123"
        t = comedian.to_insert_tuple()
        assert len(t) == 4
        assert t[0] == comedian.uuid
        assert t[1] == comedian.name
        assert t[2] == comedian.sold_out_shows
        assert t[3] == comedian.total_shows

    def test_stub_to_insert_tuple_has_zero_show_counts(self):
        """Stubs from lineup extraction have 0 show counts, so any additive update would be a no-op."""
        stub = _make_stub("Chris Rock")
        stub.uuid = "some-uuid"
        t = stub.to_insert_tuple()
        assert t[2] == 0, "sold_out_shows should be 0 for name-only stubs"
        assert t[3] == 0, "total_shows should be 0 for name-only stubs"

    def test_social_fields_not_in_insert_tuple(self):
        """Confirm social fields present on the model are excluded from to_insert_tuple."""
        comedian = _make_full_comedian("Dave Chappelle")
        comedian.uuid = "uuid-456"
        t = comedian.to_insert_tuple()
        # instagram_followers=50000 must NOT appear in the tuple
        assert comedian.instagram_followers not in t
        assert comedian.tiktok_followers not in t


# ---------------------------------------------------------------------------
# Helpers — ComedianHandler construction
# ---------------------------------------------------------------------------

def _make_handler() -> ComedianHandler:
    """Return a ComedianHandler with all DB methods replaced by MagicMocks."""
    handler = ComedianHandler.__new__(ComedianHandler)
    handler.execute_with_cursor = MagicMock()
    handler.execute_batch_operation = MagicMock()
    return handler


# ---------------------------------------------------------------------------
# _fetch_recency_scores
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# BATCH_UPDATE_COMEDIAN_SHOW_COUNTS — SQL contract
# ---------------------------------------------------------------------------

class TestBatchUpdateComedianShowCountsSql:
    def test_query_updates_both_columns(self):
        """Query must SET both total_shows and sold_out_shows."""
        sql = ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS.lower()
        assert "total_shows" in sql
        assert "sold_out_shows" in sql

    def test_query_uses_any_param_not_show_id_filter(self):
        """Query must use ANY(%s) for comedian_id filtering, not a show_id whitelist."""
        sql = ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS
        assert "ANY(%s)" in sql, "Expected ANY(%s) for comedian_id array parameter"
        assert "show_id = ANY" not in sql.lower(), (
            "Query must not filter by show_id — must aggregate across all shows"
        )

    def test_query_aggregates_from_lineup_items(self):
        """Query must join lineup_items to count per-comedian show totals."""
        sql = ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS.lower()
        assert "lineup_items" in sql

    def test_query_uses_bool_and_for_sold_out_detection(self):
        """BOOL_AND(sold_out) is the correct aggregate for all-tickets-sold-out."""
        sql = ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS.lower()
        assert "bool_and" in sql, "Expected BOOL_AND to determine show-level sold-out status"


# ---------------------------------------------------------------------------
# _refresh_comedian_show_counts
# ---------------------------------------------------------------------------

class TestRefreshComedianShowCounts:
    def test_calls_execute_with_cursor_with_correct_query(self):
        """_refresh_comedian_show_counts delegates to execute_with_cursor with BATCH_UPDATE_COMEDIAN_SHOW_COUNTS."""
        handler = _make_handler()
        handler.execute_with_cursor.return_value = None

        handler._refresh_comedian_show_counts(["uuid-1", "uuid-2"])

        handler.execute_with_cursor.assert_called_once_with(
            ComedianQueries.BATCH_UPDATE_COMEDIAN_SHOW_COUNTS,
            (["uuid-1", "uuid-2"],),
        )

    def test_exception_from_execute_with_cursor_propagates(self):
        """A DB error in execute_with_cursor bubbles up from _refresh_comedian_show_counts."""
        handler = _make_handler()
        handler.execute_with_cursor.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError, match="DB error"):
            handler._refresh_comedian_show_counts(["uuid-1"])


# ---------------------------------------------------------------------------
# update_comedian_popularity — show count refresh integration
# ---------------------------------------------------------------------------

class TestUpdateComedianPopularityRefreshShowCounts:
    def _make_comedian(self, uuid: str) -> Comedian:
        c = _make_stub(f"Comedian-{uuid}")
        c.uuid = uuid
        return c

    def _setup_handler(self, uuids, comedians, recency_map):
        handler = _make_handler()
        handler._get_comedian_uuids = MagicMock(return_value=uuids)
        handler._fetch_comedian_details = MagicMock(return_value=comedians)
        handler._fetch_recency_scores = MagicMock(return_value=recency_map)
        handler._refresh_comedian_show_counts = MagicMock()
        handler.execute_batch_operation = MagicMock(return_value=[{"id": "ok"}])
        return handler

    def test_refresh_show_counts_called_before_fetch_details(self):
        """_refresh_comedian_show_counts must be called before _fetch_comedian_details."""
        uuids = ["uuid-A"]
        comedians = [self._make_comedian("uuid-A")]
        handler = self._setup_handler(uuids, comedians, {})

        call_order = []
        handler._refresh_comedian_show_counts.side_effect = lambda *a, **kw: call_order.append("refresh")
        handler._fetch_comedian_details.side_effect = lambda *a, **kw: (call_order.append("fetch"), comedians)[1]

        handler.update_comedian_popularity()

        assert call_order == ["refresh", "fetch"], (
            "show counts must be refreshed before comedian details are fetched"
        )

    def test_refresh_show_counts_receives_target_uuids(self):
        """_refresh_comedian_show_counts is called with the resolved target UUIDs."""
        uuids = ["uuid-1", "uuid-2"]
        comedians = [self._make_comedian(u) for u in uuids]
        handler = self._setup_handler(uuids, comedians, {})

        handler.update_comedian_popularity()

        handler._refresh_comedian_show_counts.assert_called_once_with(uuids)

    def test_exception_from_refresh_show_counts_propagates(self):
        """A DB error in _refresh_comedian_show_counts bubbles up from update_comedian_popularity."""
        uuids = ["uuid-1"]
        comedians = [self._make_comedian("uuid-1")]
        handler = self._setup_handler(uuids, comedians, {})
        handler._refresh_comedian_show_counts.side_effect = RuntimeError("show count DB error")

        with pytest.raises(RuntimeError, match="show count DB error"):
            handler.update_comedian_popularity()


class TestFetchRecencyScores:
    def test_happy_path_returns_dict_of_float_scores(self):
        """execute_with_cursor returning rows → dict maps comedian_id to float recency_score."""
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"comedian_id": "uuid-1", "recency_score": 0.85},
            {"comedian_id": "uuid-2", "recency_score": 0.40},
        ]

        result = handler._fetch_recency_scores(["uuid-1", "uuid-2"])

        assert result == {"uuid-1": 0.85, "uuid-2": 0.40}
        assert all(isinstance(v, float) for v in result.values())

    def test_none_result_returns_empty_dict(self):
        """When execute_with_cursor returns None, result is an empty dict (no KeyError)."""
        handler = _make_handler()
        handler.execute_with_cursor.return_value = None

        result = handler._fetch_recency_scores(["uuid-1"])

        assert result == {}

    def test_exception_propagates_from_execute_with_cursor(self):
        """A DB error raised by execute_with_cursor bubbles up unchanged."""
        handler = _make_handler()
        handler.execute_with_cursor.side_effect = RuntimeError("DB connection lost")

        with pytest.raises(RuntimeError, match="DB connection lost"):
            handler._fetch_recency_scores(["uuid-1"])


# ---------------------------------------------------------------------------
# update_comedian_popularity — recency map integration
# ---------------------------------------------------------------------------

class TestUpdateComedianPopularity:
    def _make_comedian(self, uuid: str) -> Comedian:
        c = _make_stub(f"Comedian-{uuid}")
        c.uuid = uuid
        return c

    def _setup_handler(self, uuids, comedians, recency_map):
        """Return a handler with all helpers stubbed out."""
        handler = _make_handler()
        handler._get_comedian_uuids = MagicMock(return_value=uuids)
        handler._fetch_comedian_details = MagicMock(return_value=comedians)
        handler._fetch_recency_scores = MagicMock(return_value=recency_map)
        # execute_batch_operation must return truthy to pass the "no comedians updated" guard
        handler.execute_batch_operation = MagicMock(return_value=[{"id": "ok"}])
        return handler

    def test_recency_score_applied_to_comedian_from_map(self):
        """Comedians present in the recency map get recency_score set correctly."""
        uuids = ["uuid-A", "uuid-B"]
        comedians = [self._make_comedian("uuid-A"), self._make_comedian("uuid-B")]
        handler = self._setup_handler(uuids, comedians, {"uuid-A": 0.9, "uuid-B": 0.3})

        handler.update_comedian_popularity()

        assert comedians[0].recency_score == 0.9
        assert comedians[1].recency_score == 0.3

    def test_comedian_absent_from_recency_map_defaults_to_zero(self):
        """Comedians not in the recency map keep recency_score=0.0."""
        uuids = ["uuid-X", "uuid-Y"]
        comedians = [self._make_comedian("uuid-X"), self._make_comedian("uuid-Y")]
        # Only uuid-X has an entry; uuid-Y is absent
        handler = self._setup_handler(uuids, comedians, {"uuid-X": 0.7})

        handler.update_comedian_popularity()

        assert comedians[0].recency_score == 0.7
        assert comedians[1].recency_score == 0.0

    def test_exception_from_fetch_recency_scores_propagates(self):
        """A DB error in _fetch_recency_scores bubbles up from update_comedian_popularity."""
        uuids = ["uuid-1"]
        comedians = [self._make_comedian("uuid-1")]
        handler = self._setup_handler(uuids, comedians, {})
        handler._fetch_recency_scores.side_effect = RuntimeError("recency DB error")

        with pytest.raises(RuntimeError, match="recency DB error"):
            handler.update_comedian_popularity()
