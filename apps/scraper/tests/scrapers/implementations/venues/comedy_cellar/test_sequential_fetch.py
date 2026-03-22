"""
Unit tests for ComedyCellarScraper._fetch_all_raw_data sequential override.

Verifies:
1. Dates are processed sequentially (not concurrently) — one at a time.
2. rate_limiter.await_if_needed is called once per target.
3. A failed date returns (None, target) without aborting the remaining run.
4. Result order matches input target order.
"""
import asyncio
import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.comedy_cellar.scraper import (
    ComedyCellarScraper,
)


def _club() -> Club:
    return Club(
        id=99,
        name="Comedy Cellar",
        address="",
        website="https://www.comedycellar.com",
        scraping_url="https://www.comedycellar.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )


class _FakeData:
    """Minimal stand-in for ComedyCellarDateData."""

    def __init__(self, target: str):
        self.target = target


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scraper() -> ComedyCellarScraper:
    return ComedyCellarScraper(_club())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dates_fetched_sequentially(monkeypatch):
    """
    _fetch_all_raw_data must process one target at a time.

    We verify sequential ordering by recording entry/exit timestamps.
    If fetches ran concurrently the windows would overlap; sequentially
    they cannot because each coroutine suspends (via asyncio.sleep(0))
    before the next one starts.
    """
    scraper = _make_scraper()
    targets = ["2025-01-01", "2025-01-02", "2025-01-03"]
    order: list[str] = []

    async def fake_get_data(target):
        order.append(f"start:{target}")
        await asyncio.sleep(0)  # yield — if concurrent, interleaving would appear here
        order.append(f"end:{target}")
        return _FakeData(target)

    monkeypatch.setattr(scraper, "get_data", fake_get_data)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", lambda t: asyncio.sleep(0))
    # Bypass error_handler retry wrapper — call get_data directly
    monkeypatch.setattr(
        scraper.error_handler,
        "execute_with_retry",
        lambda fn, label: fn(),
    )

    await scraper._fetch_all_raw_data(targets)

    # Sequential pattern: start-A, end-A, start-B, end-B, ...
    assert order == [
        "start:2025-01-01",
        "end:2025-01-01",
        "start:2025-01-02",
        "end:2025-01-02",
        "start:2025-01-03",
        "end:2025-01-03",
    ], f"Non-sequential fetch order detected: {order}"


@pytest.mark.asyncio
async def test_rate_limiter_called_once_per_target(monkeypatch):
    """rate_limiter.await_if_needed must be invoked exactly once for each target."""
    scraper = _make_scraper()
    targets = ["2025-02-01", "2025-02-02", "2025-02-03"]
    rate_limit_calls: list[str] = []

    async def fake_await_if_needed(target):
        rate_limit_calls.append(target)

    async def fake_get_data(target):
        return _FakeData(target)

    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", fake_await_if_needed)
    monkeypatch.setattr(scraper, "get_data", fake_get_data)
    monkeypatch.setattr(
        scraper.error_handler,
        "execute_with_retry",
        lambda fn, label: fn(),
    )

    await scraper._fetch_all_raw_data(targets)

    assert rate_limit_calls == targets, (
        f"Expected rate_limiter called for each target in order: {targets}, got: {rate_limit_calls}"
    )


@pytest.mark.asyncio
async def test_failed_date_returns_none_without_aborting_run(monkeypatch):
    """
    A date whose fetch raises must produce (None, target) in the results.
    The remaining targets must still be processed.
    """
    scraper = _make_scraper()
    targets = ["2025-03-01", "2025-03-02", "2025-03-03"]
    FAIL_TARGET = "2025-03-02"

    async def fake_await_if_needed(target):
        pass

    async def fake_get_data(target):
        if target == FAIL_TARGET:
            raise RuntimeError(f"simulated failure for {target}")
        return _FakeData(target)

    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", fake_await_if_needed)
    monkeypatch.setattr(scraper, "get_data", fake_get_data)
    # Make error_handler propagate the exception (simulates retry exhaustion)
    async def failing_execute_with_retry(fn, label):
        return await fn()

    monkeypatch.setattr(scraper.error_handler, "execute_with_retry", failing_execute_with_retry)

    results = await scraper._fetch_all_raw_data(targets)

    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    result_map = {t: data for data, t in results}

    assert result_map["2025-03-01"] is not None, "First target should have succeeded"
    assert result_map["2025-03-02"] is None, "Failed target should produce None"
    assert result_map["2025-03-03"] is not None, "Third target should have succeeded despite middle failure"


@pytest.mark.asyncio
async def test_results_preserve_target_order(monkeypatch):
    """Results list must match the order of input targets."""
    scraper = _make_scraper()
    targets = ["2025-04-03", "2025-04-01", "2025-04-02"]

    async def fake_await_if_needed(target):
        pass

    async def fake_get_data(target):
        return _FakeData(target)

    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", fake_await_if_needed)
    monkeypatch.setattr(scraper, "get_data", fake_get_data)
    monkeypatch.setattr(
        scraper.error_handler,
        "execute_with_retry",
        lambda fn, label: fn(),
    )

    results = await scraper._fetch_all_raw_data(targets)

    result_targets = [t for _, t in results]
    assert result_targets == targets, (
        f"Result order {result_targets} does not match input order {targets}"
    )
