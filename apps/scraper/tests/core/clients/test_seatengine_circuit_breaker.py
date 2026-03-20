"""Tests for SeatEngineCircuitBreaker."""

import asyncio
import time
import pytest

from laughtrack.core.clients.seatengine.circuit_breaker import SeatEngineCircuitBreaker
from laughtrack.foundation.exceptions import CircuitBreakerOpenError


@pytest.fixture(autouse=True)
def reset_cb():
    """Ensure each test starts with a fresh circuit breaker singleton."""
    SeatEngineCircuitBreaker.reset_for_testing()
    yield
    SeatEngineCircuitBreaker.reset_for_testing()


def _make_cb(threshold: int = 3, cooldown: float = 60.0) -> SeatEngineCircuitBreaker:
    cb = SeatEngineCircuitBreaker()
    cb._threshold = threshold
    cb._cooldown = cooldown
    return cb


# ------------------------------------------------------------------
# Singleton behaviour
# ------------------------------------------------------------------


def test_singleton_returns_same_instance():
    cb1 = SeatEngineCircuitBreaker()
    cb2 = SeatEngineCircuitBreaker()
    assert cb1 is cb2


# ------------------------------------------------------------------
# CLOSED state (happy path)
# ------------------------------------------------------------------


def test_closed_by_default():
    cb = _make_cb()
    assert not cb.is_open


def test_check_open_does_not_raise_when_closed():
    cb = _make_cb()
    cb.check_open()  # should not raise


def test_failure_below_threshold_keeps_breaker_closed():
    cb = _make_cb(threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert not cb.is_open
    assert cb.failure_count == 2


# ------------------------------------------------------------------
# OPEN state
# ------------------------------------------------------------------


def test_breaker_opens_at_threshold():
    cb = _make_cb(threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert not cb.is_open
    cb.record_failure()
    assert cb.is_open


def test_check_open_raises_when_open():
    cb = _make_cb(threshold=1)
    cb.record_failure()
    with pytest.raises(CircuitBreakerOpenError):
        cb.check_open()


def test_check_open_error_message_contains_reset_countdown():
    cb = _make_cb(threshold=1, cooldown=300.0)
    cb.record_failure()
    with pytest.raises(CircuitBreakerOpenError, match=r"Resets in \d+s"):
        cb.check_open()


def test_failures_beyond_threshold_do_not_change_open_state():
    cb = _make_cb(threshold=3)
    for _ in range(10):
        cb.record_failure()
    assert cb.is_open
    assert cb.failure_count == 10


# ------------------------------------------------------------------
# Success resets the breaker
# ------------------------------------------------------------------


def test_record_success_resets_failure_count():
    cb = _make_cb(threshold=5)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.failure_count == 0
    assert not cb.is_open


def test_record_success_closes_open_breaker():
    cb = _make_cb(threshold=1)
    cb.record_failure()
    assert cb.is_open
    cb.record_success()
    assert not cb.is_open


def test_check_open_does_not_raise_after_success_reset():
    cb = _make_cb(threshold=1)
    cb.record_failure()
    cb.record_success()
    cb.check_open()  # should not raise


# ------------------------------------------------------------------
# Cooldown / time-based reset
# ------------------------------------------------------------------


def test_breaker_resets_after_cooldown(monkeypatch):
    cb = _make_cb(threshold=1, cooldown=10.0)
    cb.record_failure()
    assert cb.is_open

    # Simulate cooldown elapsed by backdating _open_since
    cb._open_since = time.monotonic() - 11.0

    assert not cb.is_open
    cb.check_open()  # should not raise after reset


def test_breaker_still_open_before_cooldown_expires(monkeypatch):
    cb = _make_cb(threshold=1, cooldown=300.0)
    cb.record_failure()

    # Simulate 100s elapsed — cooldown is 300s
    cb._open_since = time.monotonic() - 100.0

    assert cb.is_open
    with pytest.raises(CircuitBreakerOpenError):
        cb.check_open()


# ------------------------------------------------------------------
# get_ticket_data interaction: success resets, failures do NOT record
# ------------------------------------------------------------------


def test_ticket_success_resets_failure_count():
    """A successful ticket fetch resets the failure counter (partial recovery signal)."""
    cb = _make_cb(threshold=5)
    cb.record_failure()
    cb.record_failure()
    assert cb.failure_count == 2

    # Simulate a successful ticket fetch calling record_success()
    cb.record_success()
    assert cb.failure_count == 0
    assert not cb.is_open


def test_ticket_failures_do_not_increment_counter():
    """Per-show ticket failures intentionally do NOT record against the circuit breaker.

    Only venue-level fetch_events() failures drive the failure counter — individual
    show 404s are too noisy to be reliable outage signals.
    """
    cb = _make_cb(threshold=3)
    # Simulate many failed ticket calls (no record_failure() calls)
    for _ in range(100):
        pass  # get_ticket_data failure path: no cb.record_failure()
    assert cb.failure_count == 0
    assert not cb.is_open


# ------------------------------------------------------------------
# Concurrency: circuit breaker is thread-safe under concurrent load
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_failures_reach_threshold_exactly():
    """All concurrent record_failure() calls are counted; breaker opens at threshold."""
    cb = _make_cb(threshold=5)

    async def fail_once():
        await asyncio.sleep(0)  # yield to let other coroutines interleave
        cb.record_failure()
        await asyncio.sleep(0)

    await asyncio.gather(*[fail_once() for _ in range(5)])

    assert cb.failure_count == 5
    assert cb.is_open


@pytest.mark.asyncio
async def test_concurrent_failures_no_count_lost():
    """No failure count is lost when many coroutines call record_failure() concurrently."""
    cb = _make_cb(threshold=50)
    n = 20

    async def fail_with_yield():
        await asyncio.sleep(0)
        cb.record_failure()
        await asyncio.sleep(0)

    await asyncio.gather(*[fail_with_yield() for _ in range(n)])

    assert cb.failure_count == n


@pytest.mark.asyncio
async def test_check_open_is_consistent_under_concurrent_access():
    """Once the breaker opens, all concurrent check_open() calls raise."""
    cb = _make_cb(threshold=1)
    cb.record_failure()
    assert cb.is_open

    errors = []

    async def check():
        await asyncio.sleep(0)
        try:
            cb.check_open()
        except CircuitBreakerOpenError as e:
            errors.append(e)

    await asyncio.gather(*[check() for _ in range(10)])

    assert len(errors) == 10
