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
"""

import threading
from typing import Callable, TypeVar

_T = TypeVar("_T")

_DB_WRITE_LOCK = threading.Lock()


def serialized_db_call(fn: Callable[..., _T], *args, **kwargs) -> _T:
    """Run ``fn(*args, **kwargs)`` while holding the process-wide DB write lock."""
    with _DB_WRITE_LOCK:
        return fn(*args, **kwargs)
