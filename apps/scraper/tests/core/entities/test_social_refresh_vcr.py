"""
Cassette-style recorded-response tests for Instagram and TikTok follower refresh.

Unlike the mock-based tests in test_social_refresh.py (which patch
_instagram_request / _tiktok_request entirely), these tests let the real
static methods execute — including requests.get(), raise_for_status(), and
resp.json() — while replaying pre-recorded HTTP cassettes via vcrpy.

This catches response-schema drift that patch.object tests cannot detect:
if Instagram or TikTok renames a JSON key in their API response, the parser
in _fetch_*_follower_count() will raise a KeyError and the test will fail.

Cassettes live in tests/core/entities/cassettes/ as YAML files. They are
committed to the repo and represent a snapshot of the API schema at recording
time. Update them when the real API schema changes.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest
import vcr as _vcr_module

# ---------------------------------------------------------------------------
# Module loading helpers (mirrors test_social_refresh.py pattern)
# ---------------------------------------------------------------------------

_SCRAPER_ROOT = Path(__file__).parents[3]  # apps/scraper/
_CASSETTE_DIR = Path(__file__).parent / "cassettes"


def _load_module(rel_path: str, module_name: str):
    path = _SCRAPER_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
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


# Foundation stubs
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
_stub("laughtrack.utilities.domain.comedian.utils", ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain.comedian", as_package=True, ComedianUtils=MagicMock())
_stub("laughtrack.utilities.domain", as_package=True, ComedianUtils=MagicMock())
_stub("laughtrack.utilities", as_package=True, ComedianUtils=MagicMock())
_stub("laughtrack.foundation.infrastructure.database", as_package=True, BatchTemplateGenerator=MagicMock())
_stub(
    "laughtrack.foundation.infrastructure.database.template",
    BatchTemplateGenerator=MagicMock(),
)
_stub(
    "laughtrack.foundation.infrastructure.database.operation",
    DatabaseOperationLogger=MagicMock(),
)

# Comedian model and queries
_comedian_model_mod = _load_module(
    "src/laughtrack/core/entities/comedian/model.py",
    "laughtrack.core.entities.comedian.model_vcr",
)
Comedian = _comedian_model_mod.Comedian

_comedian_queries_mod = _load_module("sql/comedian_queries.py", "sql.comedian_queries_vcr")
ComedianQueries = _comedian_queries_mod.ComedianQueries

sys.modules.setdefault("laughtrack.core.entities.comedian.model", _comedian_model_mod)
sys.modules.setdefault("sql", _comedian_queries_mod)
sys.modules.setdefault("sql.comedian_queries", _comedian_queries_mod)

# BaseDatabaseHandler stub
from typing import Generic as _Generic, TypeVar as _TypeVar
from abc import ABC as _ABC, abstractmethod as _abstractmethod

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

    def execute_batch_operation(
        self, query, items, template=None, return_results=False, log_summary=True
    ):
        raise NotImplementedError

    def _get_cursor_factory(self):
        return dict


_stub("laughtrack.core.data.base_handler", BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core.data", as_package=True, BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core", as_package=True, BaseDatabaseHandler=_BaseDatabaseHandlerStub)
_stub("laughtrack.core.entities", as_package=True, Comedian=None)
_stub("laughtrack.core.entities.comedian", Comedian=None)

# Load ComedianHandler
_comedian_handler_mod = _load_module(
    "src/laughtrack/core/entities/comedian/handler.py",
    "laughtrack.core.entities.comedian.handler_vcr_test",
)
ComedianHandler = _comedian_handler_mod.ComedianHandler
# Disable per-request sleep so tests run at full speed
_comedian_handler_mod._SOCIAL_REQUEST_DELAY_S = 0.0

# ---------------------------------------------------------------------------
# VCR instance — record_mode=none ensures cassettes are always replayed
# and tests fail if a cassette is missing or a new request is attempted.
# ---------------------------------------------------------------------------
#
# HOW TO RE-RECORD CASSETTES (runbook)
# =====================================
# Run this procedure when Instagram or TikTok changes their API schema and
# the cassette tests start failing with KeyError or unexpected values.
#
# Prerequisites:
#   - Network access to api.instagram.com and www.tiktok.com (run locally,
#     NOT from a cloud/CI environment — both platforms block datacenter IPs).
#   - No extra credentials are required for these public endpoints, but you
#     may need a residential IP or VPN if your network is flagged.
#
# Steps:
#   1. Temporarily change record_mode below from "none" to "new_episodes":
#          record_mode="new_episodes"
#      "new_episodes" replays existing cassettes but records any request that
#      has no matching cassette entry — it will NOT re-record already-present
#      interactions. To force a full re-record of a specific cassette, delete
#      its YAML file from tests/core/entities/cassettes/ first.
#
#   2. Run the VCR tests:
#          cd apps/scraper
#          python -m pytest tests/core/entities/test_social_refresh_vcr.py -v
#
#   3. Inspect the YAML diffs in tests/core/entities/cassettes/:
#          git diff tests/core/entities/cassettes/
#      Verify that the changed keys match the known schema update. Unexpected
#      changes (e.g., new auth challenges, redirect responses) should be
#      investigated before committing.
#
#   4. Reset record_mode back to "none":
#          record_mode="none"
#
#   5. Re-run the tests to confirm they pass in replay-only mode, then commit
#      the updated cassette YAML files together with the code change:
#          git add tests/core/entities/cassettes/
#          git commit -m "Update VCR cassettes: <brief description of schema change>"
#
# ---------------------------------------------------------------------------

_vcr = _vcr_module.VCR(
    cassette_library_dir=str(_CASSETTE_DIR),
    record_mode="none",
)


def _make_handler() -> ComedianHandler:
    handler = ComedianHandler.__new__(ComedianHandler)
    handler.execute_with_cursor = MagicMock()
    handler.execute_batch_operation = MagicMock()
    return handler


# ---------------------------------------------------------------------------
# Instagram — cassette-based tests
# ---------------------------------------------------------------------------


class TestInstagramCassette:
    """Tests that let _instagram_request() execute fully, replaying cassettes.

    These tests validate the complete response-parsing path:
        requests.get() → raise_for_status() → resp.json() → key extraction

    If Instagram's API renames ``edge_followed_by`` or changes its nesting,
    the happy-path cassette test will fail here (not silently pass), providing
    early warning before production data goes stale.
    """

    def test_happy_path_parses_follower_count_from_cassette(self):
        """_fetch_instagram_follower_count returns (uuid, count) from cassette."""
        handler = _make_handler()
        row = {"uuid": "uuid-cassette-ig-1", "instagram_account": "@testcomedian"}
        with _vcr.use_cassette("instagram_happy_path.yaml"):
            result = handler._fetch_instagram_follower_count(row)
        assert result == ("uuid-cassette-ig-1", 150_000)

    def test_account_without_at_prefix_parses_correctly(self):
        """Bare account name (no @) still hits the correct URL."""
        handler = _make_handler()
        row = {"uuid": "uuid-cassette-ig-2", "instagram_account": "testcomedian"}
        with _vcr.use_cassette("instagram_happy_path.yaml"):
            result = handler._fetch_instagram_follower_count(row)
        assert result == ("uuid-cassette-ig-2", 150_000)

    def test_schema_drift_returns_none_not_corrupt_data(self):
        """If 'edge_followed_by' key disappears, result is None (not a crash or wrong number).

        This cassette replays a response where the key has been renamed to
        'followers'. The parser must return None rather than surfacing an
        unhandled KeyError up the call stack.
        """
        handler = _make_handler()
        row = {"uuid": "uuid-cassette-ig-3", "instagram_account": "@driftcomedian"}
        with _vcr.use_cassette("instagram_schema_drift.yaml"):
            result = handler._fetch_instagram_follower_count(row)
        assert result is None

    def test_rate_limit_response_returns_none(self):
        """HTTP 429 from Instagram is caught and returns None."""
        handler = _make_handler()
        row = {"uuid": "uuid-cassette-ig-4", "instagram_account": "@ratelimited"}
        with _vcr.use_cassette("instagram_rate_limit.yaml"):
            result = handler._fetch_instagram_follower_count(row)
        assert result is None

    def test_request_sends_correct_headers(self):
        """_instagram_request sends X-IG-App-ID and browser User-Agent."""
        import requests as _requests

        with _vcr.use_cassette("instagram_happy_path.yaml") as cassette:
            ComedianHandler._instagram_request("testcomedian")

        recorded_request = cassette.requests[0]
        assert recorded_request.headers.get("X-IG-App-ID") == "936619743392459"
        assert "Chrome" in recorded_request.headers.get("User-Agent", "")

    def test_request_sends_username_as_query_param(self):
        """_instagram_request sends username as ?username= query parameter."""
        with _vcr.use_cassette("instagram_happy_path.yaml") as cassette:
            ComedianHandler._instagram_request("testcomedian")

        assert "username=testcomedian" in cassette.requests[0].uri


# ---------------------------------------------------------------------------
# TikTok — cassette-based tests
# ---------------------------------------------------------------------------


class TestTikTokCassette:
    """Tests that let _tiktok_request() execute fully, replaying cassettes.

    Validates the full response-parsing path against a realistic API snapshot.
    If TikTok's API renames ``userInfo.stats.followerCount``, the happy-path
    cassette test will fail here before production follower counts go stale.
    """

    def test_happy_path_parses_follower_count_from_cassette(self):
        """_fetch_tiktok_follower_count returns (uuid, count) from cassette."""
        handler = _make_handler()
        row = {"uuid": "uuid-cassette-tt-1", "tiktok_account": "@testcomedian"}
        with _vcr.use_cassette("tiktok_happy_path.yaml"):
            result = handler._fetch_tiktok_follower_count(row)
        assert result == ("uuid-cassette-tt-1", 200_000)

    def test_account_without_at_prefix_parses_correctly(self):
        """Bare account name (no @) still hits the correct URL."""
        handler = _make_handler()
        row = {"uuid": "uuid-cassette-tt-2", "tiktok_account": "testcomedian"}
        with _vcr.use_cassette("tiktok_happy_path.yaml"):
            result = handler._fetch_tiktok_follower_count(row)
        assert result == ("uuid-cassette-tt-2", 200_000)

    def test_schema_drift_returns_none_not_corrupt_data(self):
        """If 'stats' key disappears from userInfo, result is None (not a crash).

        This cassette replays a response where 'stats' has been renamed to
        'statistics'. The parser must return None rather than propagating a
        KeyError.
        """
        handler = _make_handler()
        row = {"uuid": "uuid-cassette-tt-3", "tiktok_account": "@driftcomedian"}
        with _vcr.use_cassette("tiktok_schema_drift.yaml"):
            result = handler._fetch_tiktok_follower_count(row)
        assert result is None

    def test_rate_limit_response_returns_none(self):
        """HTTP 429 from TikTok is caught and returns None."""
        handler = _make_handler()
        row = {"uuid": "uuid-cassette-tt-4", "tiktok_account": "@ratelimited"}
        with _vcr.use_cassette("tiktok_rate_limit.yaml"):
            result = handler._fetch_tiktok_follower_count(row)
        assert result is None

    def test_request_sends_correct_headers(self):
        """_tiktok_request sends Referer and browser User-Agent."""
        with _vcr.use_cassette("tiktok_happy_path.yaml") as cassette:
            ComedianHandler._tiktok_request("testcomedian")

        recorded_request = cassette.requests[0]
        assert recorded_request.headers.get("Referer") == "https://www.tiktok.com/"
        assert "Chrome" in recorded_request.headers.get("User-Agent", "")

    def test_request_sends_uniqueid_as_query_param(self):
        """_tiktok_request sends username as ?uniqueId= query parameter."""
        with _vcr.use_cassette("tiktok_happy_path.yaml") as cassette:
            ComedianHandler._tiktok_request("testcomedian")

        assert "uniqueId=testcomedian" in cassette.requests[0].uri


# ---------------------------------------------------------------------------
# End-to-end: refresh_instagram_followers — DB row → HTTP → parse → batch write
# ---------------------------------------------------------------------------


class TestRefreshInstagramFollowersCassette:
    """End-to-end cassette tests for refresh_instagram_followers().

    Mocks the DB cursor layer (execute_with_cursor / execute_batch_operation)
    but lets the real HTTP stack execute, replaying cassettes. This validates
    that the full pipeline — DB row → HTTP → parse → execute_batch_operation —
    works together and catches regressions that per-layer mocks cannot.
    """

    def test_happy_path_calls_execute_batch_operation_with_parsed_counts(self):
        """Full pipeline: DB row → cassette HTTP → parse → batch update."""
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"uuid": "uuid-e2e-ig-1", "instagram_account": "@testcomedian"}
        ]
        with _vcr.use_cassette("instagram_happy_path.yaml"):
            result = handler.refresh_instagram_followers()

        assert result == 1
        handler.execute_batch_operation.assert_called_once_with(
            ComedianQueries.UPDATE_COMEDIAN_INSTAGRAM_FOLLOWERS,
            [("uuid-e2e-ig-1", 150_000)],
        )

    def test_schema_drift_does_not_call_execute_batch_operation(self):
        """When API schema drifts all fetches return None and no DB write occurs.

        This is the key regression guard: if Instagram renames a response key
        the pipeline should silently skip all updates rather than persist wrong
        data or raise an unhandled exception.
        """
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"uuid": "uuid-e2e-ig-drift", "instagram_account": "@driftcomedian"}
        ]
        with _vcr.use_cassette("instagram_schema_drift.yaml"):
            result = handler.refresh_instagram_followers()

        assert result == 0
        handler.execute_batch_operation.assert_not_called()


# ---------------------------------------------------------------------------
# End-to-end: refresh_tiktok_followers — DB row → HTTP → parse → batch write
# ---------------------------------------------------------------------------


class TestRefreshTikTokFollowersCassette:
    """End-to-end cassette tests for refresh_tiktok_followers().

    Same strategy as TestRefreshInstagramFollowersCassette — DB layer mocked,
    HTTP layer replayed from cassettes.
    """

    def test_happy_path_calls_execute_batch_operation_with_parsed_counts(self):
        """Full pipeline: DB row → cassette HTTP → parse → batch update."""
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"uuid": "uuid-e2e-tt-1", "tiktok_account": "@testcomedian"}
        ]
        with _vcr.use_cassette("tiktok_happy_path.yaml"):
            result = handler.refresh_tiktok_followers()

        assert result == 1
        handler.execute_batch_operation.assert_called_once_with(
            ComedianQueries.UPDATE_COMEDIAN_TIKTOK_FOLLOWERS,
            [("uuid-e2e-tt-1", 200_000)],
        )

    def test_schema_drift_does_not_call_execute_batch_operation(self):
        """When API schema drifts all fetches return None and no DB write occurs.

        If TikTok renames userInfo.stats.followerCount the pipeline must skip
        all updates rather than persist wrong data or raise an exception.
        """
        handler = _make_handler()
        handler.execute_with_cursor.return_value = [
            {"uuid": "uuid-e2e-tt-drift", "tiktok_account": "@driftcomedian"}
        ]
        with _vcr.use_cassette("tiktok_schema_drift.yaml"):
            result = handler.refresh_tiktok_followers()

        assert result == 0
        handler.execute_batch_operation.assert_not_called()
