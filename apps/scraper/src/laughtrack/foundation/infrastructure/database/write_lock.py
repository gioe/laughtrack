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
"""

import threading
from typing import Callable, TypeVar

_T = TypeVar("_T")

# Cascade-detection threshold for serialized_db_call. Legitimate large-batch
# upserts finish in tens of seconds (per the orchestrator's _DB_WRITE_TIMEOUT
# comment in core/services/scraping/__init__.py), so 30s gives ~3x headroom
# before declaring the prior writer stuck. Well below the orchestrator's 300s
# per-call timeout, so the fail-fast fires inside the executor thread before
# the orchestrator's asyncio.wait_for would. Module-level for tests.
_LOCK_HOLD_TIMEOUT = 30.0

# RLock (not Lock) so a wrapped callable that recursively invokes
# serialized_db_call on the same thread does not deadlock. The lock's job is
# cross-thread serialization of DB writes; intra-thread recursion is harmless
# because the GIL serializes Python-level execution within a single thread.
_DB_WRITE_LOCK = threading.RLock()


class LockHeldError(RuntimeError):
    """Raised when ``serialized_db_call`` cannot acquire ``_DB_WRITE_LOCK``
    within ``_LOCK_HOLD_TIMEOUT`` seconds — signals a stuck prior writer
    (typically a hung DB call whose executor thread asyncio.wait_for could
    not cancel)."""


def serialized_db_call(fn: Callable[..., _T], *args, **kwargs) -> _T:
    """Run ``fn(*args, **kwargs)`` while holding the process-wide DB write lock.

    Raises :class:`LockHeldError` if the lock cannot be acquired within
    ``_LOCK_HOLD_TIMEOUT`` seconds. The caller's persist-exception branch
    (see ``_scrape_clubs_concurrently``) stamps ``result.error`` accordingly
    so the per-club metric flips ok→error.
    """
    acquired = _DB_WRITE_LOCK.acquire(timeout=_LOCK_HOLD_TIMEOUT)
    if not acquired:
        raise LockHeldError(
            f"_DB_WRITE_LOCK still held after {_LOCK_HOLD_TIMEOUT}s; "
            f"prior writer thread is stuck (likely a hung DB call that "
            f"asyncio.wait_for could not cancel)"
        )
    try:
        return fn(*args, **kwargs)
    finally:
        _DB_WRITE_LOCK.release()
