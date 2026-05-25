"""Tests for the iTunes podcast discovery trigger on comedian insertion.

Run with: pytest tests/ -k itunes_trigger -q
"""

import sys
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from _entities_test_helpers import _load_module


# ---------------------------------------------------------------------------
# Load the same modules as test_comedian_handler.py so import paths align.
# We intentionally DO NOT stub the iTunes adapter module at import time —
# leaking a partial stub into sys.modules breaks collection of
# tests/scripts/core/test_search_itunes_podcasts.py, which imports symbols
# (UpsertResult) that wouldn't exist on the stub. Instead, the real adapter
# module is loaded inside each test via the handler's deferred import, and
# its functions are monkey-patched per test.
# ---------------------------------------------------------------------------

_comedian_model_mod = _load_module(
    "src/laughtrack/core/entities/comedian/model.py",
    "laughtrack.core.entities.comedian.model_direct",
)
Comedian = _comedian_model_mod.Comedian

_comedian_queries_mod = _load_module("sql/comedian_queries.py", "sql.comedian_queries_direct")

sys.modules.setdefault("laughtrack.core.entities.comedian.model", _comedian_model_mod)
sys.modules.setdefault("sql.comedian_queries", _comedian_queries_mod)

_comedian_handler_mod = _load_module(
    "src/laughtrack/core/entities/comedian/handler.py",
    "laughtrack.core.entities.comedian.handler_direct",
)
ComedianHandler = _comedian_handler_mod.ComedianHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stub_comedian(name: str, uuid: str = "stub-uuid") -> Comedian:
    c = Comedian.__new__(Comedian)
    c.name = name
    c.uuid = uuid
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


def _make_handler_with_inserted_row(inserted_row: dict) -> ComedianHandler:
    """Return a handler whose insert_comedians simulates one new comedian inserted."""
    handler = ComedianHandler.__new__(ComedianHandler)
    handler.execute_with_cursor = MagicMock()
    handler.execute_batch_operation = MagicMock(return_value=[inserted_row])

    @contextmanager
    def fake_transaction():
        fake_conn = MagicMock()
        fake_cur = MagicMock()
        fake_conn.cursor.return_value.__enter__.return_value = fake_cur
        fake_conn.cursor.return_value.__exit__.return_value = False
        yield fake_conn

    handler.transaction = fake_transaction
    return handler


@pytest.fixture
def itunes_module(monkeypatch):
    """Provide the real iTunes adapter module with discovery/persistence patched.

    Importing the real module triggers curl_cffi imports — already a project
    dependency, so this is safe in CI. The returned object exposes the patched
    MagicMocks for each entry point the trigger calls.
    """
    monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_ENABLED", "1")

    import laughtrack.core.itunes_podcast_discovery as itunes_mod

    discover_mock = MagicMock(return_value=([], 0))
    upsert_mock = MagicMock(return_value=None)
    load_deny_mock = MagicMock(return_value=(set(), set()))
    denied_mock = MagicMock(return_value=False)

    monkeypatch.setattr(itunes_mod, "discover_candidates_for_comedians", discover_mock)
    monkeypatch.setattr(itunes_mod, "upsert_candidate_with_conn", upsert_mock)
    monkeypatch.setattr(itunes_mod, "load_active_deny_list", load_deny_mock)
    monkeypatch.setattr(itunes_mod, "candidate_is_denied", denied_mock)

    return type(
        "ItunesMocks",
        (),
        {
            "module": itunes_mod,
            "discover": discover_mock,
            "upsert": upsert_mock,
            "load_deny": load_deny_mock,
            "denied": denied_mock,
            "Candidate": itunes_mod.ItunesPodcastCandidate,
            "DiscoveryComedian": itunes_mod.PodcastDiscoveryComedian,
        },
    )()


def _candidate(itunes_module, *, comedian_id=1, confidence=0.95, source_podcast_id="abc"):
    return itunes_module.Candidate(
        comedian_id=comedian_id,
        source_podcast_id=source_podcast_id,
        matched_name="stub",
        normalized_match="stub",
        confidence=confidence,
        title="Stub Podcast",
        author_name=None,
        feed_url=None,
        website_url=None,
        image_url=None,
        description=None,
        evidence={},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestItunesTriggerOnInsert:
    """Verify the iTunes podcast discovery trigger fires correctly from insert_comedians."""

    def test_insert_fires_itunes_discovery_once_with_comedian_id(self, itunes_module):
        """Inserting a new comedian fires the adapter exactly once, with the new comedian's id."""
        inserted_row = {"id": 7777, "uuid": "uuid-test-1", "name": "Stub Comedian"}
        handler = _make_handler_with_inserted_row(inserted_row)

        result = handler.insert_comedians([_make_stub_comedian("Stub Comedian", "uuid-test-1")])

        assert result == [inserted_row]
        assert itunes_module.discover.call_count == 1
        called_comedians = itunes_module.discover.call_args[0][0]
        assert len(called_comedians) == 1
        assert called_comedians[0].comedian_id == 7777
        assert called_comedians[0].name == "Stub Comedian"

    def test_no_inserted_rows_skips_trigger(self, itunes_module):
        """When insert returns no rows (all existed), the adapter is not called."""
        handler = ComedianHandler.__new__(ComedianHandler)
        handler.execute_with_cursor = MagicMock()
        handler.execute_batch_operation = MagicMock(return_value=[])

        result = handler.insert_comedians([_make_stub_comedian("All Already Existed", "uuid-existed")])

        assert result == []
        itunes_module.discover.assert_not_called()

    def test_adapter_failure_does_not_block_insertion(self, itunes_module):
        """A raise from the adapter is logged and swallowed — insert_comedians returns the inserted rows."""
        itunes_module.discover.side_effect = RuntimeError("iTunes is down")

        inserted_row = {"id": 9001, "uuid": "uuid-resilient", "name": "Resilient Comedian"}
        handler = _make_handler_with_inserted_row(inserted_row)

        result = handler.insert_comedians([_make_stub_comedian("Resilient Comedian", "uuid-resilient")])

        assert result == [inserted_row]
        itunes_module.discover.assert_called_once()
        itunes_module.upsert.assert_not_called()

    def test_persistence_failure_does_not_block_insertion(self, itunes_module):
        """A raise from upsert_candidate_with_conn is logged and swallowed."""
        cand = _candidate(itunes_module, comedian_id=42, source_podcast_id="abc", confidence=0.99)
        itunes_module.discover.return_value = ([cand], 0)
        itunes_module.upsert.side_effect = RuntimeError("DB exploded")

        inserted_row = {"id": 42, "uuid": "uuid-db-fail", "name": "DB Fail"}
        handler = _make_handler_with_inserted_row(inserted_row)

        result = handler.insert_comedians([_make_stub_comedian("DB Fail", "uuid-db-fail")])

        assert result == [inserted_row]
        itunes_module.discover.assert_called_once()

    def test_low_confidence_candidates_filtered_out(self, itunes_module, monkeypatch):
        """Candidates below the min-confidence threshold are dropped, not persisted."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_MIN_CONFIDENCE", "0.8")
        low = _candidate(itunes_module, comedian_id=1, source_podcast_id="low", confidence=0.5)
        itunes_module.discover.return_value = ([low], 0)

        inserted_row = {"id": 1, "uuid": "uuid-low", "name": "Low Confidence"}
        handler = _make_handler_with_inserted_row(inserted_row)

        handler.insert_comedians([_make_stub_comedian("Low Confidence", "uuid-low")])

        itunes_module.upsert.assert_not_called()

    def test_high_confidence_candidates_persisted(self, itunes_module, monkeypatch):
        """Candidates at or above the min-confidence threshold are upserted."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_MIN_CONFIDENCE", "0.8")
        high = _candidate(itunes_module, comedian_id=2, source_podcast_id="high", confidence=0.95)
        itunes_module.discover.return_value = ([high], 0)

        inserted_row = {"id": 2, "uuid": "uuid-high", "name": "High Confidence"}
        handler = _make_handler_with_inserted_row(inserted_row)

        handler.insert_comedians([_make_stub_comedian("High Confidence", "uuid-high")])

        assert itunes_module.upsert.call_count == 1

    def test_env_disable_skips_trigger(self, itunes_module, monkeypatch):
        """Setting LAUGHTRACK_ITUNES_ON_INSERT_ENABLED=0 fully disables the trigger."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_ENABLED", "0")

        inserted_row = {"id": 1234, "uuid": "uuid-disabled", "name": "Disabled"}
        handler = _make_handler_with_inserted_row(inserted_row)

        result = handler.insert_comedians([_make_stub_comedian("Disabled", "uuid-disabled")])

        assert result == [inserted_row]
        itunes_module.discover.assert_not_called()

    def test_row_missing_id_or_name_skips_trigger(self, itunes_module):
        """A returned row without 'id' or 'name' keys doesn't crash; trigger is a no-op."""
        # Mimics legacy callers / tests that mock a thin row.
        handler = _make_handler_with_inserted_row({"uuid": "uuid-thin-row"})

        result = handler.insert_comedians([_make_stub_comedian("Thin Row", "uuid-thin-row")])

        assert result == [{"uuid": "uuid-thin-row"}]
        itunes_module.discover.assert_not_called()

    @pytest.mark.parametrize(
        "env_var,bad_value",
        [
            ("LAUGHTRACK_ITUNES_ON_INSERT_MIN_CONFIDENCE", "not-a-float"),
            ("LAUGHTRACK_ITUNES_ON_INSERT_MAX_RESULTS", "ten"),
        ],
    )
    def test_malformed_env_var_does_not_break_insertion(
        self, itunes_module, monkeypatch, env_var, bad_value
    ):
        """A malformed config env var must not escape the swallow-all guarantee."""
        monkeypatch.setenv(env_var, bad_value)

        inserted_row = {"id": 999, "uuid": "uuid-bad-env", "name": "Bad Env"}
        handler = _make_handler_with_inserted_row(inserted_row)

        result = handler.insert_comedians([_make_stub_comedian("Bad Env", "uuid-bad-env")])

        # Insertion succeeded; the config parse error was logged and swallowed.
        assert result == [inserted_row]
        itunes_module.discover.assert_not_called()
