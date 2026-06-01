"""Process-wide DB write serialization that crosses event-loop boundaries.

The scraping orchestrator (``_scrape_clubs_concurrently``) and per-club scrapers
run on different asyncio event loops. The orchestrator drives its own loop;
each scraper is invoked via ``loop.run_in_executor(None, _scrape_with_context, ...)``
which calls ``scraper.scrape()`` synchronously inside a worker thread, where the
scraper re-enters asyncio via ``asyncio.run(scrape_async())`` and therefore runs
on a *different* loop than the orchestrator.

An :class:`asyncio.Lock` is bound to the loop that created it and cannot be
acquired from another loop, so it cannot serialize DB writes that happen on
both the orchestrator's loop and a worker-thread scraper's loop. A
:class:`threading.Lock` is loop-agnostic — any thread can acquire it — which is
what we need to serialize multi-venue ``upsert_for_eventbrite_venue`` writes
(running on scraper-side worker threads) against the orchestrator's
``insert_club_result`` writes (running on the main loop).

Use this from inside ``loop.run_in_executor`` so the lock is acquired on the
executor thread; the calling event loop stays free to schedule other tasks
while waiting for the lock.

Cascade fail-fast (TASK-2553): the lock is acquired with a bounded wait
(``_LOCK_HOLD_TIMEOUT``) and raises :class:`LockHeldError` on timeout.
``asyncio.wait_for(loop.run_in_executor(...))`` cancels only the *await*; the
underlying executor thread keeps running and keeps holding the RLock if its DB
call genuinely hangs. Without a bounded wait, every subsequent persist would
sit in ``_DB_WRITE_LOCK.acquire()`` until its own ``_DB_WRITE_TIMEOUT``
(300s) fired — turning one stuck writer into N consecutive timeouts (the
cascade documented in run 26762966336). The bounded wait converts that into
one 300s timeout + (N-1) fast LockHeldError failures, which the caller's
existing exception branch stamps onto ``result.error`` so the per-club metric
still flips ok→error.

Caller-visible side effect: EventbriteScraper organizer-mode upserts
(scrapers/implementations/api/eventbrite/scraper.py::_upsert_one) also call
``serialized_db_call`` from per-venue coroutines run under ``asyncio.gather``.
TASK-2554 bounded each ``_upsert_one`` await with its own ``asyncio.wait_for``
(``_EB_UPSERT_TIMEOUT``) so a single hung executor thread can no longer hold
the gather() open past the EB scraper's parent per-club timeout — when the
wait_for fires, the venue is named in the error log and the gather completes
with empty results for that venue. The executor thread may still hold this
RLock (CPython threads are not safely cancelable), but the ``_LOCK_HOLD_TIMEOUT``
fail-fast above converts that into LockHeldError for subsequent contenders
instead of unbounded waits. "Organizer-mode venue X missing" in a nightly
summary should look for the venue-named timeout log line first.
"""

import os
import threading
import time
from typing import Callable, TypeVar

_T = TypeVar("_T")

# Cascade-detection threshold for serialized_db_call. Legitimate large-batch
# upserts finish in tens of seconds (per the orchestrator's _DB_WRITE_TIMEOUT
# comment in core/services/scraping/__init__.py), so 30s gives ~3x headroom
# before declaring the prior writer stuck. Well below the orchestrator's 300s
# per-call timeout, so the fail-fast fires inside the executor thread before
# the orchestrator's asyncio.wait_for would. Module-level for tests.
#
# TASK-2557: read at use-time via _lock_hold_timeout() so the
# ``LOCK_HOLD_TIMEOUT`` env var can tune the threshold for nightly runs
# without a code change, mirroring the MAX_CONCURRENT_CLUBS pattern in
# core/services/scraping/__init__.py. Patching this module attribute still
# changes the effective bound (it is the fallback), so existing tests keep
# working.
_LOCK_HOLD_TIMEOUT = 30.0


def _lock_hold_timeout() -> float:
    """Resolve the lock-hold timeout, preferring the ``LOCK_HOLD_TIMEOUT``
    env var and falling back to ``_LOCK_HOLD_TIMEOUT``.

    Read at use-time so nightly runs can tune via env without restart and
    tests can patch either the module attribute or the env var.
    """
    return float(os.environ.get("LOCK_HOLD_TIMEOUT", _LOCK_HOLD_TIMEOUT))


# RLock (not Lock) so a wrapped callable that recursively invokes
# serialized_db_call on the same thread does not deadlock. The lock's job is
# cross-thread serialization of DB writes; intra-thread recursion is harmless
# because the GIL serializes Python-level execution within a single thread.
_DB_WRITE_LOCK = threading.RLock()


class LockHeldError(RuntimeError):
    """Raised when ``serialized_db_call`` cannot acquire ``_DB_WRITE_LOCK``
    within the resolved hold-timeout (``LOCK_HOLD_TIMEOUT`` env var or the
    ``_LOCK_HOLD_TIMEOUT`` default) — signals a stuck prior writer
    (typically a hung DB call whose executor thread asyncio.wait_for could
    not cancel). The message surfaces both the measured wait and the
    configured threshold so operators can tune ``LOCK_HOLD_TIMEOUT`` from
    real data rather than guess-and-check."""


def serialized_db_call(fn: Callable[..., _T], *args, **kwargs) -> _T:
    """Run ``fn(*args, **kwargs)`` while holding the process-wide DB write lock.

    Raises :class:`LockHeldError` if the lock cannot be acquired within the
    resolved hold-timeout (``LOCK_HOLD_TIMEOUT`` env var or
    ``_LOCK_HOLD_TIMEOUT`` default). The caller's persist-exception branch
    (see ``_scrape_clubs_concurrently``) stamps ``result.error`` accordingly
    so the per-club metric flips ok→error.
    """
    timeout = _lock_hold_timeout()
    started_at = time.monotonic()
    acquired = _DB_WRITE_LOCK.acquire(timeout=timeout)
    waited = time.monotonic() - started_at
    if not acquired:
        raise LockHeldError(
            f"_DB_WRITE_LOCK still held after {waited:.2f}s "
            f"(LOCK_HOLD_TIMEOUT={timeout:.2f}s); "
            f"prior writer thread is stuck (likely a hung DB call that "
            f"asyncio.wait_for could not cancel)"
        )
    try:
        return fn(*args, **kwargs)
    finally:
        _DB_WRITE_LOCK.release()
