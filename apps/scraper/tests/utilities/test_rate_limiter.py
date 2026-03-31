"""
Tests for DomainConfig and RateLimiter anti-detection mode.

Covers:
- DomainConfig defaults and both modes (RPS vs anti-detection)
- Session rotation triggers (count, duration, consecutive errors)
- Peak-hour multiplier and exponential backoff delay calculations
- record_request_error / record_request_success
- reset_domain clears _last_request and _sessions
- get_domain_user_agent before and after session creation
- Concurrent anti-detection callers serialized by per-domain _sessions_write_lock (defaultdict(threading.Lock))
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from laughtrack.utilities.infrastructure.domain_config import DomainConfig
from laughtrack.utilities.infrastructure.rate_limiter import RateLimiter, _RequestSession


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Restore RateLimiter singleton state around every test."""
    rl = RateLimiter()
    saved_configs = dict(rl._domain_configs)
    for domain in list(rl._sessions.keys()):
        rl.reset_domain(domain)
    yield
    rl._domain_configs = saved_configs
    for domain in list(rl._sessions.keys()):
        rl.reset_domain(domain)
    rl._last_request.clear()


def _fast_anti(rl: RateLimiter, name: str, **kwargs) -> str:
    """Register a zero-delay anti-detection domain and return its name."""
    defaults: dict = dict(enable_anti_detection=True, min_delay=0.0, max_delay=0.0)
    defaults.update(kwargs)
    rl.set_domain_config(name, DomainConfig(**defaults))
    return name


# ---------------------------------------------------------------------------
# DomainConfig — defaults and modes
# ---------------------------------------------------------------------------


class TestDomainConfigDefaults:
    def test_default_rps(self):
        cfg = DomainConfig()
        assert cfg.requests_per_second == 1.0

    def test_default_anti_detection_off(self):
        cfg = DomainConfig()
        assert cfg.enable_anti_detection is False

    def test_default_delay_bounds(self):
        cfg = DomainConfig()
        assert cfg.min_delay == 2.0
        assert cfg.max_delay == 5.0

    def test_default_session_request_limit(self):
        cfg = DomainConfig()
        assert cfg.session_request_limit == 50

    def test_default_session_duration(self):
        cfg = DomainConfig()
        assert cfg.session_duration_secs == 3600

    def test_default_error_backoff_base(self):
        cfg = DomainConfig()
        assert cfg.error_backoff_base == 5.0

    def test_default_peak_hour_multiplier(self):
        cfg = DomainConfig()
        assert cfg.peak_hour_multiplier == 1.2

    def test_default_browser_profiles_empty(self):
        cfg = DomainConfig()
        assert cfg.browser_profiles == []

    def test_rps_mode_config(self):
        cfg = DomainConfig(requests_per_second=0.5)
        assert cfg.enable_anti_detection is False
        assert cfg.requests_per_second == 0.5

    def test_anti_detection_mode_config(self):
        cfg = DomainConfig(enable_anti_detection=True, min_delay=3.0, max_delay=8.0)
        assert cfg.enable_anti_detection is True
        assert cfg.min_delay == 3.0
        assert cfg.max_delay == 8.0


class TestRateLimiterModes:
    @pytest.mark.asyncio
    async def test_rps_mode_does_not_create_session(self):
        rl = RateLimiter()
        domain = "rps-mode.example.com"
        rl.set_domain_config(domain, DomainConfig(enable_anti_detection=False))
        await rl.await_if_needed(f"https://{domain}/page")
        assert domain not in rl._sessions

    @pytest.mark.asyncio
    async def test_anti_detection_mode_creates_session(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "anti-det-mode.example.com")
        await rl.await_if_needed(f"https://{domain}/page")
        assert domain in rl._sessions

    @pytest.mark.asyncio
    async def test_rps_mode_records_last_request_timestamp(self):
        rl = RateLimiter()
        domain = "rps-ts.example.com"
        rl.set_domain_config(domain, DomainConfig(enable_anti_detection=False, requests_per_second=100.0))
        before = time.time()
        await rl.await_if_needed(f"https://{domain}/page")
        assert rl._last_request.get(domain, 0) >= before

    def test_set_domain_limit_updates_rps(self):
        rl = RateLimiter()
        domain = "rps-update.example.com"
        rl.set_domain_config(domain, DomainConfig(requests_per_second=1.0))
        rl.set_domain_limit(domain, 5.0)
        assert rl.get_domain_limit(domain) == 5.0

    def test_set_domain_limit_preserves_anti_detection_flag(self):
        rl = RateLimiter()
        domain = "rps-preserve.example.com"
        rl.set_domain_config(domain, DomainConfig(enable_anti_detection=True, requests_per_second=1.0))
        rl.set_domain_limit(domain, 2.0)
        cfg = rl._get_config(domain)
        assert cfg.enable_anti_detection is True
        assert cfg.requests_per_second == 2.0


# ---------------------------------------------------------------------------
# Session rotation triggers
# ---------------------------------------------------------------------------


class TestSessionRotation:
    @pytest.mark.asyncio
    async def test_rotates_after_request_count_exceeded(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "rot-count.example.com", session_request_limit=1)
        # First request — creates session
        await rl.await_if_needed(f"https://{domain}/page")
        first_id = rl._sessions[domain].session_id
        # Second request — count limit reached, session should rotate
        await rl.await_if_needed(f"https://{domain}/page")
        second_id = rl._sessions[domain].session_id
        assert first_id != second_id

    @pytest.mark.asyncio
    async def test_rotates_after_duration_exceeded(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "rot-dur.example.com", session_duration_secs=0)
        await rl.await_if_needed(f"https://{domain}/page")
        first_id = rl._sessions[domain].session_id
        # Session age > 0s → should rotate immediately on next request
        await rl.await_if_needed(f"https://{domain}/page")
        second_id = rl._sessions[domain].session_id
        assert first_id != second_id

    @pytest.mark.asyncio
    async def test_rotates_after_consecutive_errors(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "rot-err.example.com")
        await rl.await_if_needed(f"https://{domain}/page")
        first_id = rl._sessions[domain].session_id

        # Trigger 3 consecutive errors (rotation threshold)
        for _ in range(3):
            rl.record_request_error(domain)

        await rl.await_if_needed(f"https://{domain}/page")
        second_id = rl._sessions[domain].session_id
        assert first_id != second_id

    @pytest.mark.asyncio
    async def test_no_rotation_below_thresholds(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "no-rot.example.com", session_request_limit=10)
        await rl.await_if_needed(f"https://{domain}/page")
        first_id = rl._sessions[domain].session_id
        await rl.await_if_needed(f"https://{domain}/page")
        second_id = rl._sessions[domain].session_id
        assert first_id == second_id


# ---------------------------------------------------------------------------
# Exponential backoff and record_request_error / record_request_success
# ---------------------------------------------------------------------------


class TestExponentialBackoff:
    def _make_session(self, domain: str = "backoff.example.com", errors: int = 0) -> _RequestSession:
        now = datetime.now()
        return _RequestSession(
            domain=domain,
            start_time=now,
            request_count=0,
            last_request=now,
            consecutive_errors=errors,
            user_agent="TestAgent/1.0",
            session_id="abc123",
        )

    def test_record_request_error_increments_counter(self):
        rl = RateLimiter()
        domain = "err-inc.example.com"
        rl.set_domain_config(domain, DomainConfig(enable_anti_detection=True))
        # Inject a session directly
        rl._sessions[domain] = self._make_session(domain)
        rl.record_request_error(domain)
        assert rl._sessions[domain].consecutive_errors == 1

    def test_record_request_error_accumulates(self):
        rl = RateLimiter()
        domain = "err-acc.example.com"
        rl.set_domain_config(domain, DomainConfig(enable_anti_detection=True))
        rl._sessions[domain] = self._make_session(domain)
        for _ in range(3):
            rl.record_request_error(domain)
        assert rl._sessions[domain].consecutive_errors == 3

    def test_record_request_success_resets_counter(self):
        rl = RateLimiter()
        domain = "err-reset.example.com"
        rl.set_domain_config(domain, DomainConfig(enable_anti_detection=True))
        rl._sessions[domain] = self._make_session(domain, errors=3)
        rl.record_request_success(domain)
        assert rl._sessions[domain].consecutive_errors == 0

    def test_record_error_noop_for_unknown_domain(self):
        rl = RateLimiter()
        rl.record_request_error("nonexistent.example.com")  # must not raise

    def test_record_success_noop_for_unknown_domain(self):
        rl = RateLimiter()
        rl.record_request_success("nonexistent.example.com")  # must not raise

    def test_backoff_increases_delay_with_errors(self):
        """Each additional error should raise the calculated delay."""
        rl = RateLimiter()
        cfg = DomainConfig(
            enable_anti_detection=True,
            min_delay=0.0,
            max_delay=0.0,
            error_backoff_base=5.0,
        )
        # Patch random.uniform to return 0 so base delay is deterministic
        with patch("laughtrack.utilities.infrastructure.rate_limiter.random.uniform", return_value=0.0):
            # Non-peak hours to avoid multiplier
            with patch("laughtrack.utilities.infrastructure.rate_limiter.datetime") as mock_dt:
                mock_dt.now.return_value = datetime(2026, 1, 1, 3, 0, 0)  # 03:00 — off-peak
                session_0 = self._make_session(errors=0)
                delay_0 = rl._calculate_anti_detection_delay(session_0, cfg)

                session_1 = self._make_session(errors=1)
                delay_1 = rl._calculate_anti_detection_delay(session_1, cfg)

                session_2 = self._make_session(errors=2)
                delay_2 = rl._calculate_anti_detection_delay(session_2, cfg)

        assert delay_0 <= delay_1 < delay_2

    def test_backoff_multiplier_capped_at_8x(self):
        """Consecutive errors > 3 cap multiplier at 8× (2^3 = 8)."""
        rl = RateLimiter()
        cfg = DomainConfig(
            enable_anti_detection=True,
            min_delay=0.0,
            max_delay=0.0,
            error_backoff_base=5.0,
        )
        with patch("laughtrack.utilities.infrastructure.rate_limiter.random.uniform", return_value=0.0):
            with patch("laughtrack.utilities.infrastructure.rate_limiter.datetime") as mock_dt:
                mock_dt.now.return_value = datetime(2026, 1, 1, 3, 0, 0)
                session_high = self._make_session(errors=10)
                delay_high = rl._calculate_anti_detection_delay(session_high, cfg)
                # 8× cap: backoff = 5.0 * 8 = 40.0
                assert delay_high == pytest.approx(40.0, rel=0.01)


# ---------------------------------------------------------------------------
# Peak-hour multiplier
# ---------------------------------------------------------------------------


class TestPeakHourMultiplier:
    def _make_session(self, domain: str = "peak.example.com") -> _RequestSession:
        now = datetime.now()
        return _RequestSession(
            domain=domain,
            start_time=now,
            request_count=0,
            last_request=now,
            consecutive_errors=0,
            user_agent="TestAgent/1.0",
            session_id="abc123",
        )

    def test_peak_hour_multiplier_applied_during_peak(self):
        rl = RateLimiter()
        # Use min_delay=max_delay=2.0 so base > 1.0 floor, peak_hour_multiplier=2.0
        cfg = DomainConfig(
            enable_anti_detection=True,
            min_delay=2.0,
            max_delay=2.0,
            peak_hour_multiplier=2.0,
        )
        # side_effect=lambda a, b: a → uniform(2.0, 2.0)=2.0; uniform(-0.5, 1.0)=-0.5
        # → delay = 2.0 + (-0.5) = 1.5 (off-peak), 1.5 * 2.0 = 3.0 (peak)
        with patch(
            "laughtrack.utilities.infrastructure.rate_limiter.random.uniform",
            side_effect=lambda a, b: a,
        ):
            with patch("laughtrack.utilities.infrastructure.rate_limiter.datetime") as mock_dt:
                mock_dt.now.return_value = datetime(2026, 1, 1, 3, 0, 0)  # off-peak
                session = self._make_session()
                delay_off_peak = rl._calculate_anti_detection_delay(session, cfg)

                mock_dt.now.return_value = datetime(2026, 1, 1, 10, 0, 0)  # peak
                delay_peak = rl._calculate_anti_detection_delay(session, cfg)

        assert delay_off_peak == pytest.approx(1.5, rel=0.01)
        assert delay_peak == pytest.approx(3.0, rel=0.01)

    def test_no_peak_multiplier_outside_peak_hours(self):
        rl = RateLimiter()
        cfg = DomainConfig(
            enable_anti_detection=True,
            min_delay=1.0,
            max_delay=1.0,
            peak_hour_multiplier=3.0,
        )
        with patch("laughtrack.utilities.infrastructure.rate_limiter.random.uniform", return_value=0.0):
            with patch("laughtrack.utilities.infrastructure.rate_limiter.datetime") as mock_dt:
                mock_dt.now.return_value = datetime(2026, 1, 1, 8, 59, 0)  # just before peak
                session = self._make_session()
                delay = rl._calculate_anti_detection_delay(session, cfg)

        # No multiplier applied: base = 1.0 + jitter(0) = 1.0
        assert delay == pytest.approx(1.0, rel=0.01)


# ---------------------------------------------------------------------------
# reset_domain
# ---------------------------------------------------------------------------


class TestResetDomain:
    @pytest.mark.asyncio
    async def test_reset_clears_last_request(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "reset-lr.example.com")
        await rl.await_if_needed(f"https://{domain}/page")
        assert domain in rl._last_request or domain in rl._sessions
        rl.reset_domain(domain)
        assert domain not in rl._last_request

    @pytest.mark.asyncio
    async def test_reset_clears_session(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "reset-sess.example.com")
        await rl.await_if_needed(f"https://{domain}/page")
        assert domain in rl._sessions
        rl.reset_domain(domain)
        assert domain not in rl._sessions

    def test_reset_noop_for_unknown_domain(self):
        rl = RateLimiter()
        rl.reset_domain("nonexistent.example.com")  # must not raise

    @pytest.mark.asyncio
    async def test_new_session_created_after_reset(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "reset-new.example.com")
        await rl.await_if_needed(f"https://{domain}/page")
        first_id = rl._sessions[domain].session_id
        rl.reset_domain(domain)
        await rl.await_if_needed(f"https://{domain}/page")
        second_id = rl._sessions[domain].session_id
        assert first_id != second_id


# ---------------------------------------------------------------------------
# get_domain_user_agent
# ---------------------------------------------------------------------------


class TestGetDomainUserAgent:
    def test_returns_none_before_session(self):
        rl = RateLimiter()
        assert rl.get_domain_user_agent("no-session.example.com") is None

    def test_returns_none_for_rps_domain(self):
        rl = RateLimiter()
        domain = "rps-ua.example.com"
        rl.set_domain_config(domain, DomainConfig(enable_anti_detection=False))
        # No session is created for RPS mode
        assert rl.get_domain_user_agent(domain) is None

    @pytest.mark.asyncio
    async def test_returns_user_agent_after_session_created(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "ua-after.example.com")
        await rl.await_if_needed(f"https://{domain}/page")
        ua = rl.get_domain_user_agent(domain)
        assert ua is not None
        assert isinstance(ua, str)
        assert len(ua) > 0

    @pytest.mark.asyncio
    async def test_user_agent_matches_session_profile(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "ua-match.example.com")
        await rl.await_if_needed(f"https://{domain}/page")
        ua = rl.get_domain_user_agent(domain)
        profile = rl.get_domain_profile(domain)
        assert ua == profile.user_agent

    @pytest.mark.asyncio
    async def test_returns_none_after_reset(self):
        rl = RateLimiter()
        domain = _fast_anti(rl, "ua-reset.example.com")
        await rl.await_if_needed(f"https://{domain}/page")
        assert rl.get_domain_user_agent(domain) is not None
        rl.reset_domain(domain)
        assert rl.get_domain_user_agent(domain) is None


# ---------------------------------------------------------------------------
# Concurrent anti-detection callers serialized by _sessions_write_lock (threading.Lock)
# ---------------------------------------------------------------------------


class TestAntiDetectionConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_callers_both_complete(self):
        """Two concurrent anti-detection requests for the same domain must both
        complete without hanging and must each update session state correctly.

        NOTE: With the per-domain threading.Lock fix, state (last_request, request_count)
        is updated atomically before sleeping — not held across a suspension point.
        This is safe across event loops in separate threads. The old asyncio.Lock
        pattern was unsafe cross-thread: asyncio.Lock.release() uses call_soon()
        on the waiting loop's Future from the wrong thread, never waking that
        loop's selector.select() — causing indefinite hangs.
        """
        rl = RateLimiter()
        # Zero-delay so calls complete immediately; we just verify both finish
        # and that session state reflects exactly 2 increments.
        domain = _fast_anti(rl, "anti-conc.example.com", min_delay=0.0, max_delay=0.0)

        # Pre-create the session.
        await rl.await_if_needed(f"https://{domain}/page0")
        count_after_first = rl._sessions[domain].request_count

        with patch(
            "laughtrack.utilities.infrastructure.rate_limiter.asyncio.sleep",
            return_value=None,  # suppress real sleeping; both calls must still complete
        ):
            await asyncio.gather(
                rl.await_if_needed(f"https://{domain}/page1"),
                rl.await_if_needed(f"https://{domain}/page2"),
            )

        # Both calls completed; request_count must reflect exactly 2 more increments.
        assert rl._sessions[domain].request_count == count_after_first + 2

    @pytest.mark.asyncio
    async def test_different_domains_run_concurrently(self):
        """Requests for different domains must NOT block each other."""
        rl = RateLimiter()
        domain_a = _fast_anti(rl, "conc-a.example.com", min_delay=0.001, max_delay=0.001)
        domain_b = _fast_anti(rl, "conc-b.example.com", min_delay=0.001, max_delay=0.001)

        events: list[str] = []
        original_sleep = asyncio.sleep

        async def tracked_sleep(delay: float) -> None:
            events.append("enter")
            await original_sleep(0)
            events.append("exit")

        with patch(
            "laughtrack.utilities.infrastructure.rate_limiter.asyncio.sleep",
            side_effect=tracked_sleep,
        ):
            await asyncio.gather(
                rl.await_if_needed(f"https://{domain_a}/page"),
                rl.await_if_needed(f"https://{domain_b}/page"),
            )

        # Each coroutine holds its own per-domain lock and releases before sleep,
        # so both sleeps proceed concurrently (interleaved enter/exit is expected)
        assert len(events) == 4
        assert events.count("enter") == 2
        assert events.count("exit") == 2
