"""Unit tests for serialized_db_call's lock-cascade fail-fast (TASK-2553)."""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest

from laughtrack.foundation.infrastructure.database import write_lock
from laughtrack.foundation.infrastructure.database.write_lock import (
    LockHeldError,
    serialized_db_call,
)


def _hold_lock_in_background(release: threading.Event, acquired: threading.Event) -> threading.Thread:
    """Spawn a thread that acquires _DB_WRITE_LOCK and holds it until ``release`` is set."""

    def hold():
        with write_lock._DB_WRITE_LOCK:
            acquired.set()
            release.wait(timeout=10.0)

    t = threading.Thread(target=hold, daemon=True)
    t.start()
    return t


def test_serialized_db_call_returns_result_when_lock_uncontended():
    """Baseline: no contention, the wrapped callable runs and its result propagates."""
    sentinel = object()
    assert serialized_db_call(lambda: sentinel) is sentinel


def test_serialized_db_call_passes_args_and_kwargs():
    captured = {}

    def fn(a, b, *, c):
        captured["a"], captured["b"], captured["c"] = a, b, c
        return a + b + c

    assert serialized_db_call(fn, 1, 2, c=3) == 6
    assert captured == {"a": 1, "b": 2, "c": 3}


def test_serialized_db_call_releases_lock_on_exception():
    """If the wrapped callable raises, the lock must still be released so the
    next call doesn't time out behind the failed one."""

    def boom():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        serialized_db_call(boom)

    # If the lock was leaked, the next non-blocking acquire would fail. RLock
    # acquired by the same thread is reentrant, so we verify on a fresh thread.
    acquired_box = {"ok": False}

    def probe():
        acquired_box["ok"] = write_lock._DB_WRITE_LOCK.acquire(timeout=0.5)
        if acquired_box["ok"]:
            write_lock._DB_WRITE_LOCK.release()

    t = threading.Thread(target=probe)
    t.start()
    t.join()
    assert acquired_box["ok"], "lock leaked after exception in wrapped callable"


def test_serialized_db_call_raises_lock_held_error_when_prior_writer_stuck():
    """Cascade fail-fast: if another thread holds _DB_WRITE_LOCK beyond
    _LOCK_HOLD_TIMEOUT, serialized_db_call raises LockHeldError instead of
    blocking forever (the pre-fix behavior that produced the run 26762966336
    cascade)."""
    release = threading.Event()
    acquired = threading.Event()
    holder = _hold_lock_in_background(release, acquired)
    try:
        assert acquired.wait(timeout=2.0), "background holder failed to acquire lock"

        with patch.object(write_lock, "_LOCK_HOLD_TIMEOUT", 0.05):
            t0 = time.monotonic()
            with pytest.raises(LockHeldError, match="still held"):
                serialized_db_call(lambda: "never reached")
            elapsed = time.monotonic() - t0

        # Fail-fast: we waited ~0.05s, not the orchestrator's 300s.
        assert elapsed < 1.0, f"serialized_db_call blocked for {elapsed:.2f}s (expected < 1s)"
    finally:
        release.set()
        holder.join(timeout=5.0)


def test_serialized_db_call_does_not_invoke_fn_when_lock_held():
    """When LockHeldError fires, the wrapped callable must not run — otherwise
    a stuck DB write could still produce side effects on a partially-acquired
    state. Verifies the acquire-before-call ordering."""
    release = threading.Event()
    acquired = threading.Event()
    holder = _hold_lock_in_background(release, acquired)
    invocations = []

    def should_not_run():
        invocations.append(1)
        return "ran"

    try:
        assert acquired.wait(timeout=2.0)
        with patch.object(write_lock, "_LOCK_HOLD_TIMEOUT", 0.05):
            with pytest.raises(LockHeldError):
                serialized_db_call(should_not_run)
        assert invocations == [], "fn ran despite LockHeldError"
    finally:
        release.set()
        holder.join(timeout=5.0)


def test_same_thread_recursive_acquire_still_works():
    """RLock semantics: a callable that recursively calls serialized_db_call
    on the same thread must not deadlock against the outer acquisition."""
    inner_value = object()

    def inner():
        return inner_value

    def outer():
        return serialized_db_call(inner)

    assert serialized_db_call(outer) is inner_value
