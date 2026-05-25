"""Tests for the iTunes podcast discovery trigger on comedian insertion.

Run with: pytest tests/ -k itunes_trigger -q
"""

import concurrent.futures
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

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
    # Force inline execution so per-test mock assertions are deterministic;
    # the background-dispatch path is exercised separately below.
    monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_BACKGROUND", "0")

    import laughtrack.core.itunes_podcast_discovery as itunes_mod

    discover_mock = MagicMock(return_value=([], []))
    upsert_mock = MagicMock(return_value=None)
    record_attempt_mock = MagicMock(return_value=None)
    load_deny_mock = MagicMock(return_value=(set(), set()))
    denied_mock = MagicMock(return_value=False)

    monkeypatch.setattr(itunes_mod, "discover_candidates_for_comedian", discover_mock)
    monkeypatch.setattr(itunes_mod, "upsert_candidate_with_conn", upsert_mock)
    monkeypatch.setattr(itunes_mod, "record_discovery_attempt", record_attempt_mock)
    monkeypatch.setattr(itunes_mod, "load_active_deny_list", load_deny_mock)
    monkeypatch.setattr(itunes_mod, "candidate_is_denied", denied_mock)

    return type(
        "ItunesMocks",
        (),
        {
            "module": itunes_mod,
            "discover": discover_mock,
            "upsert": upsert_mock,
            "record_attempt": record_attempt_mock,
            "load_deny": load_deny_mock,
            "denied": denied_mock,
            "Candidate": itunes_mod.ItunesPodcastCandidate,
            "DiscoveryComedian": itunes_mod.PodcastDiscoveryComedian,
            "Failure": itunes_mod.ItunesSearchFailure,
        },
    )()


@pytest.fixture(autouse=True)
def _clear_deny_list_cache():
    """Reset the process-wide deny-list cache around every test.

    The cache is a module-level singleton, so without this a value populated by
    one test would leak into the next and skew load_active_deny_list call counts.
    """
    _comedian_handler_mod._deny_list_cache.clear()
    yield
    _comedian_handler_mod._deny_list_cache.clear()


@pytest.fixture(autouse=True)
def _reset_itunes_pool_state():
    """Reset the module-level bounded pool + in-flight counter around every test.

    The executor is created lazily once and reused process-wide, and the
    in-flight counter is a module global. Without a reset, a pool built with one
    test's MAX_WORKERS would serve the next, and a leaked in-flight count would
    skew saturation-warning assertions.
    """
    _comedian_handler_mod._itunes_executor = None
    _comedian_handler_mod._itunes_inflight = 0
    _comedian_handler_mod._itunes_saturation_warned = False
    yield
    ex = _comedian_handler_mod._itunes_executor
    if ex is not None:
        ex.shutdown(wait=False, cancel_futures=True)
    _comedian_handler_mod._itunes_executor = None
    _comedian_handler_mod._itunes_inflight = 0
    _comedian_handler_mod._itunes_saturation_warned = False


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
        called_comedian = itunes_module.discover.call_args[0][0]
        assert called_comedian.comedian_id == 7777
        assert called_comedian.name == "Stub Comedian"
        itunes_module.record_attempt.assert_called_once()
        assert itunes_module.record_attempt.call_args.kwargs["status"] == "no_candidates"

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
        itunes_module.record_attempt.assert_called_once()
        assert itunes_module.record_attempt.call_args.kwargs["status"] == "failed"
        itunes_module.upsert.assert_not_called()

    def test_persistence_failure_does_not_block_insertion(self, itunes_module):
        """A raise from upsert_candidate_with_conn is logged and swallowed."""
        cand = _candidate(itunes_module, comedian_id=42, source_podcast_id="abc", confidence=0.99)
        itunes_module.discover.return_value = ([cand], [])
        itunes_module.upsert.side_effect = RuntimeError("DB exploded")

        inserted_row = {"id": 42, "uuid": "uuid-db-fail", "name": "DB Fail"}
        handler = _make_handler_with_inserted_row(inserted_row)

        result = handler.insert_comedians([_make_stub_comedian("DB Fail", "uuid-db-fail")])

        assert result == [inserted_row]
        itunes_module.discover.assert_called_once()
        assert itunes_module.record_attempt.call_count == 2
        assert itunes_module.record_attempt.call_args.kwargs["status"] == "failed"

    def test_low_confidence_candidates_filtered_out(self, itunes_module, monkeypatch):
        """Candidates below the min-confidence threshold are dropped, not persisted."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_MIN_CONFIDENCE", "0.8")
        low = _candidate(itunes_module, comedian_id=1, source_podcast_id="low", confidence=0.5)
        itunes_module.discover.return_value = ([low], [])

        inserted_row = {"id": 1, "uuid": "uuid-low", "name": "Low Confidence"}
        handler = _make_handler_with_inserted_row(inserted_row)

        handler.insert_comedians([_make_stub_comedian("Low Confidence", "uuid-low")])

        itunes_module.upsert.assert_not_called()
        itunes_module.record_attempt.assert_called_once()
        assert itunes_module.record_attempt.call_args.kwargs["status"] == "no_candidates"

    def test_high_confidence_candidates_persisted(self, itunes_module, monkeypatch):
        """Candidates at or above the min-confidence threshold are upserted."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_MIN_CONFIDENCE", "0.8")
        high = _candidate(itunes_module, comedian_id=2, source_podcast_id="high", confidence=0.95)
        itunes_module.discover.return_value = ([high], [])

        inserted_row = {"id": 2, "uuid": "uuid-high", "name": "High Confidence"}
        handler = _make_handler_with_inserted_row(inserted_row)

        handler.insert_comedians([_make_stub_comedian("High Confidence", "uuid-high")])

        assert itunes_module.upsert.call_count == 1
        itunes_module.record_attempt.assert_called_once()
        assert itunes_module.record_attempt.call_args.kwargs["status"] == "candidates_found"
        assert itunes_module.record_attempt.call_args.kwargs["candidates_found"] == 1

    def test_search_failure_records_failed_attempt(self, itunes_module):
        """A per-term iTunes failure records a failed discovery attempt."""
        failure = itunes_module.Failure(
            search_term="Search Fail",
            status_code=500,
            message="iTunes HTTP 500",
        )
        itunes_module.discover.return_value = ([], [failure])

        inserted_row = {"id": 43, "uuid": "uuid-search-fail", "name": "Search Fail"}
        handler = _make_handler_with_inserted_row(inserted_row)

        handler.insert_comedians([_make_stub_comedian("Search Fail", "uuid-search-fail")])

        itunes_module.record_attempt.assert_called_once()
        assert itunes_module.record_attempt.call_args.kwargs["status"] == "failed"
        assert itunes_module.record_attempt.call_args.kwargs["error_count"] == 1

    def test_403_search_failure_records_blocked_attempt(self, itunes_module):
        """A 403 without eligible candidates records a blocked discovery attempt."""
        failure = itunes_module.Failure(
            search_term="Blocked Search",
            status_code=403,
            message="iTunes HTTP 403",
        )
        itunes_module.discover.return_value = ([], [failure])

        inserted_row = {"id": 44, "uuid": "uuid-blocked", "name": "Blocked Search"}
        handler = _make_handler_with_inserted_row(inserted_row)

        handler.insert_comedians([_make_stub_comedian("Blocked Search", "uuid-blocked")])

        itunes_module.record_attempt.assert_called_once()
        assert itunes_module.record_attempt.call_args.kwargs["status"] == "blocked"
        assert itunes_module.record_attempt.call_args.kwargs["error_count"] == 1

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
            ("LAUGHTRACK_ITUNES_ON_INSERT_REQUEST_DELAY", "fast"),
            ("LAUGHTRACK_ITUNES_ON_INSERT_DENY_LIST_TTL", "soon"),
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


class _NeverDoneFuture:
    """Stand-in Future that never completes, so its done-callback never fires.

    Lets a test grow the module's in-flight counter deterministically: each
    submission increments it and nothing decrements it back down.
    """

    def add_done_callback(self, fn):
        self._cb = fn


class _RecordingExecutor:
    """Fake bounded pool that records submissions without running them."""

    def __init__(self):
        self.submissions: list = []

    def submit(self, target, *args):
        self.submissions.append((target, args))
        return _NeverDoneFuture()


class TestItunesTriggerBackgroundDispatch:
    """Verify the trigger dispatches discovery to the bounded pool off the hot path."""

    def test_background_mode_submits_to_pool_without_blocking(
        self, itunes_module, monkeypatch
    ):
        """With backgrounding enabled, insert_comedians submits the worker to the
        bounded pool and returns before discover() is invoked synchronously."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_BACKGROUND", "1")

        recorder = _RecordingExecutor()
        monkeypatch.setattr(_comedian_handler_mod, "_get_itunes_executor", lambda: recorder)

        inserted_row = {"id": 4242, "uuid": "uuid-bg", "name": "Background Comic"}
        handler = _make_handler_with_inserted_row(inserted_row)

        result = handler.insert_comedians([_make_stub_comedian("Background Comic", "uuid-bg")])

        # insert_comedians returned the inserted row immediately; the worker was
        # handed to the pool but the recorder never executed it.
        assert result == [inserted_row]
        assert len(recorder.submissions) == 1
        target, args = recorder.submissions[0]
        assert target == handler._run_itunes_discovery_for_inserted
        assert args == ([inserted_row],)
        itunes_module.discover.assert_not_called()

    def test_background_pool_actually_runs_discovery_end_to_end(
        self, itunes_module, monkeypatch
    ):
        """End-to-end: with the real bounded pool, the worker eventually invokes
        the iTunes adapter — the hot path simply doesn't wait on it."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_BACKGROUND", "1")

        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="test-itunes"
        )
        # Capture the Future the dispatcher creates so the test can wait on it.
        submitted: list = []
        real_submit = executor.submit

        def capturing_submit(*args, **kwargs):
            fut = real_submit(*args, **kwargs)
            submitted.append(fut)
            return fut

        executor.submit = capturing_submit
        monkeypatch.setattr(_comedian_handler_mod, "_get_itunes_executor", lambda: executor)

        inserted_row = {"id": 5151, "uuid": "uuid-bg-real", "name": "Real BG Comic"}
        handler = _make_handler_with_inserted_row(inserted_row)

        try:
            result = handler.insert_comedians([_make_stub_comedian("Real BG Comic", "uuid-bg-real")])

            assert result == [inserted_row]
            assert len(submitted) == 1
            submitted[0].result(timeout=5)
            assert itunes_module.discover.call_count == 1
            called_comedian = itunes_module.discover.call_args[0][0]
            assert called_comedian.comedian_id == 5151
        finally:
            executor.shutdown(wait=True)

    def test_background_mode_skips_pool_when_disabled(self, itunes_module, monkeypatch):
        """Kill-switch precedence: ENABLED=0 means no submission, regardless of
        BACKGROUND."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_ENABLED", "0")
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_BACKGROUND", "1")

        recorder = _RecordingExecutor()
        monkeypatch.setattr(_comedian_handler_mod, "_get_itunes_executor", lambda: recorder)

        inserted_row = {"id": 6262, "uuid": "uuid-killed", "name": "Killed"}
        handler = _make_handler_with_inserted_row(inserted_row)

        result = handler.insert_comedians([_make_stub_comedian("Killed", "uuid-killed")])

        assert result == [inserted_row]
        assert recorder.submissions == []
        itunes_module.discover.assert_not_called()

    def test_dispatch_failure_does_not_block_insertion(self, itunes_module, monkeypatch):
        """A raise from pool submission is logged and swallowed — insertion still
        returns the inserted rows."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_BACKGROUND", "1")

        class _BoomExecutor:
            def submit(self, *a, **kw):
                raise RuntimeError("pool is shut down")

        monkeypatch.setattr(
            _comedian_handler_mod, "_get_itunes_executor", lambda: _BoomExecutor()
        )

        inserted_row = {"id": 7373, "uuid": "uuid-boom", "name": "Boom"}
        handler = _make_handler_with_inserted_row(inserted_row)

        result = handler.insert_comedians([_make_stub_comedian("Boom", "uuid-boom")])

        # Submission failed, but the insert succeeded and the in-flight counter
        # was rolled back (no permanent drift toward a false saturation warning).
        assert result == [inserted_row]
        assert _comedian_handler_mod._itunes_inflight == 0


class TestBoundedPoolConcurrencyCap:
    """Verify the module-level pool is a shared singleton sized by env config."""

    def test_executor_is_singleton(self, monkeypatch):
        """_get_itunes_executor returns the same pool across calls (and handlers)."""
        first = _comedian_handler_mod._get_itunes_executor()
        second = _comedian_handler_mod._get_itunes_executor()
        assert first is second

    def test_executor_respects_max_workers_env(self, monkeypatch):
        """The pool is sized from LAUGHTRACK_ITUNES_ON_INSERT_MAX_WORKERS."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_MAX_WORKERS", "3")
        executor = _comedian_handler_mod._get_itunes_executor()
        assert executor._max_workers == 3

    def test_max_workers_clamped_and_default_on_bad_value(self, monkeypatch):
        """Values < 1 clamp to 1; a non-integer falls back to the default of 4."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_MAX_WORKERS", "0")
        assert _comedian_handler_mod._itunes_on_insert_max_workers() == 1
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_MAX_WORKERS", "not-an-int")
        assert _comedian_handler_mod._itunes_on_insert_max_workers() == 4

    def test_inflight_warning_logged_when_threshold_exceeded(self, monkeypatch):
        """Submitting past the threshold logs a saturation warning; staying at or
        below it does not."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_INFLIGHT_WARN", "1")

        recorder = _RecordingExecutor()
        monkeypatch.setattr(_comedian_handler_mod, "_get_itunes_executor", lambda: recorder)

        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            # First submission: in-flight rises to 1 (== threshold) — no warning.
            _comedian_handler_mod._submit_itunes_worker(lambda: None)
            mock_logger.warn.assert_not_called()
            # Second submission: in-flight rises to 2 (> threshold) — warning fires.
            _comedian_handler_mod._submit_itunes_worker(lambda: None)
            assert mock_logger.warn.call_count == 1
            assert "in flight" in mock_logger.warn.call_args[0][0]

    def test_inflight_warning_edge_triggered_and_rearms(self, monkeypatch):
        """The warning fires once per saturation episode (not per submit) and
        re-arms after the backlog drains back to the threshold."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_INFLIGHT_WARN", "1")

        recorder = _RecordingExecutor()
        monkeypatch.setattr(_comedian_handler_mod, "_get_itunes_executor", lambda: recorder)
        submit = _comedian_handler_mod._submit_itunes_worker
        done = _comedian_handler_mod._on_itunes_worker_done

        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            submit(lambda: None)  # in-flight 1 (== threshold) — no warning
            submit(lambda: None)  # in-flight 2 (> threshold) — warning #1
            submit(lambda: None)  # in-flight 3 (still saturated) — edge-triggered, no new warning
            assert mock_logger.warn.call_count == 1

            # Drain the backlog: in-flight 3 -> 2 -> 1 (re-arms at <= threshold) -> 0.
            done(None)
            done(None)
            done(None)

            submit(lambda: None)  # in-flight 1 (== threshold) — no warning
            submit(lambda: None)  # in-flight 2 (> threshold) — warning #2 (re-armed)
            assert mock_logger.warn.call_count == 2

    def test_inflight_warning_disabled_when_threshold_zero(self, monkeypatch):
        """Threshold 0 disables the saturation warning entirely."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_INFLIGHT_WARN", "0")

        recorder = _RecordingExecutor()
        monkeypatch.setattr(_comedian_handler_mod, "_get_itunes_executor", lambda: recorder)

        with patch.object(_comedian_handler_mod, "Logger") as mock_logger:
            for _ in range(5):
                _comedian_handler_mod._submit_itunes_worker(lambda: None)
            mock_logger.warn.assert_not_called()


class TestDenyListCache:
    """Verify the active podcast deny list is cached across insert batches.

    The persistence path is only reached when at least one eligible (>= min
    confidence) candidate exists, so each test seeds discover with a high-
    confidence candidate to force the deny-list lookup to run.
    """

    def _insert(self, handler_id: int, itunes_module) -> None:
        """Run one insert batch that produces a single high-confidence candidate."""
        cand = _candidate(
            itunes_module, comedian_id=handler_id, source_podcast_id=f"pod-{handler_id}", confidence=0.95
        )
        itunes_module.discover.return_value = ([cand], [])
        inserted_row = {"id": handler_id, "uuid": f"uuid-{handler_id}", "name": f"Comic {handler_id}"}
        handler = _make_handler_with_inserted_row(inserted_row)
        handler.insert_comedians([_make_stub_comedian(f"Comic {handler_id}", f"uuid-{handler_id}")])

    def test_deny_list_queried_once_within_ttl(self, itunes_module, monkeypatch):
        """Two insert batches inside the TTL window hit the DB for the deny list once."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_DENY_LIST_TTL", "60")

        self._insert(1, itunes_module)
        self._insert(2, itunes_module)

        # Both batches reached the persistence path (2 upserts) but the deny
        # list was loaded from the DB only once — the second read was cached.
        assert itunes_module.upsert.call_count == 2
        assert itunes_module.load_deny.call_count == 1

    def test_deny_list_requeried_after_ttl_expires(self, itunes_module, monkeypatch):
        """TTL=0 disables caching: every batch re-queries the deny list."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_DENY_LIST_TTL", "0")

        self._insert(1, itunes_module)
        self._insert(2, itunes_module)

        assert itunes_module.upsert.call_count == 2
        assert itunes_module.load_deny.call_count == 2

    def test_cache_shared_across_handler_instances(self, itunes_module, monkeypatch):
        """The cache is process-wide: a value loaded by one handler serves another."""
        monkeypatch.setenv("LAUGHTRACK_ITUNES_ON_INSERT_DENY_LIST_TTL", "60")

        # Two distinct handler instances (separate inserted rows / handlers).
        self._insert(10, itunes_module)
        self._insert(20, itunes_module)

        assert itunes_module.load_deny.call_count == 1
