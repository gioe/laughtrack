"""Tests for BrowserProfile, BaseHeaders.from_profile, and RateLimiter profile rotation."""

import asyncio
import time
from dataclasses import FrozenInstanceError
from unittest.mock import patch

import pytest

from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.browser_profile import (
    BUILTIN_PROFILES,
    BrowserProfile,
)
from laughtrack.utilities.infrastructure.domain_config import DomainConfig
from laughtrack.utilities.infrastructure.rate_limiter import RateLimiter


# ---------------------------------------------------------------------------
# BrowserProfile dataclass
# ---------------------------------------------------------------------------


class TestBrowserProfile:
    def test_fields_present(self):
        p = BUILTIN_PROFILES[0]
        assert p.browser_version
        assert p.user_agent
        assert p.sec_ch_ua
        assert p.accept_language
        assert p.platform
        assert p.impersonation_target

    def test_impersonation_target_matches_browser_version(self):
        for p in BUILTIN_PROFILES:
            assert p.impersonation_target == p.browser_version, (
                f"Profile {p.browser_version!r} has mismatched impersonation_target "
                f"{p.impersonation_target!r}"
            )

    def test_no_version_mixing_across_profiles(self):
        """Major version number extracted from browser_version must appear in sec_ch_ua."""
        for p in BUILTIN_PROFILES:
            # Extract the major version digits (e.g. "124" from "chrome124")
            major = "".join(c for c in p.browser_version if c.isdigit())
            assert major in p.sec_ch_ua, (
                f"Profile {p.browser_version!r}: major version {major!r} "
                f"not found in sec_ch_ua {p.sec_ch_ua!r}"
            )

    def test_is_mobile_false_for_all_builtin_profiles(self):
        # BUILTIN_PROFILES currently contains only desktop targets
        for p in BUILTIN_PROFILES:
            assert p.is_mobile is False

    def test_is_mobile_true_for_android_platform(self):
        android_profile = BrowserProfile(
            browser_version="chrome99_android",
            user_agent="Mozilla/5.0 (Linux; Android 10; K) Chrome/99.0.0.0 Mobile",
            sec_ch_ua='"Chromium";v="99"',
            accept_language="en-US,en;q=0.9",
            platform="Android",
            impersonation_target="chrome99_android",
        )
        assert android_profile.is_mobile is True

    def test_to_headers_keys(self):
        p = BUILTIN_PROFILES[0]
        h = p.to_headers()
        assert "User-Agent" in h
        assert "sec-ch-ua" in h
        assert "sec-ch-ua-mobile" in h
        assert "sec-ch-ua-platform" in h
        assert "Accept-Language" in h

    def test_to_headers_mobile_flag_desktop(self):
        desktop = next(p for p in BUILTIN_PROFILES if p.platform != "Android")
        assert desktop.to_headers()["sec-ch-ua-mobile"] == "?0"

    def test_profile_is_frozen(self):
        p = BUILTIN_PROFILES[0]
        with pytest.raises((FrozenInstanceError, AttributeError)):
            p.browser_version = "chrome999"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BaseHeaders.from_profile
# ---------------------------------------------------------------------------


class TestBaseHeadersFromProfile:
    def test_returns_dict(self):
        h = BaseHeaders.from_profile(BUILTIN_PROFILES[0])
        assert isinstance(h, dict)

    def test_ua_matches_profile(self):
        profile = BUILTIN_PROFILES[0]
        h = BaseHeaders.from_profile(profile)
        assert h["User-Agent"] == profile.user_agent

    def test_sec_ch_ua_matches_profile(self):
        profile = BUILTIN_PROFILES[0]
        h = BaseHeaders.from_profile(profile)
        assert h["sec-ch-ua"] == profile.sec_ch_ua

    def test_platform_matches_profile(self):
        profile = BUILTIN_PROFILES[0]
        h = BaseHeaders.from_profile(profile)
        assert profile.platform in h["sec-ch-ua-platform"]

    def test_profile_overrides_base_ua(self):
        """The profile UA should replace whatever the base_type dict provides."""
        profile = BUILTIN_PROFILES[0]
        h = BaseHeaders.from_profile(profile, base_type="desktop_browser")
        assert h["User-Agent"] == profile.user_agent


# ---------------------------------------------------------------------------
# DomainConfig — browser_profiles field
# ---------------------------------------------------------------------------


class TestDomainConfigBrowserProfiles:
    def test_default_browser_profiles_empty(self):
        cfg = DomainConfig()
        assert cfg.browser_profiles == []

    def test_custom_browser_profiles(self):
        cfg = DomainConfig(browser_profiles=[BUILTIN_PROFILES[0]])
        assert len(cfg.browser_profiles) == 1
        assert cfg.browser_profiles[0] is BUILTIN_PROFILES[0]


# ---------------------------------------------------------------------------
# RateLimiter — profile rotation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the RateLimiter singleton state between tests."""
    rl = RateLimiter()
    saved_configs = dict(rl._domain_configs)
    for domain in list(rl._sessions.keys()):
        rl.reset_domain(domain)
    yield
    rl._domain_configs = saved_configs
    for domain in list(rl._sessions.keys()):
        rl.reset_domain(domain)
    rl._last_request.clear()
    rl._async_domain_locks.clear()


def _fast_anti_detection_domain(rl: RateLimiter, name: str) -> str:
    """Register a zero-delay anti-detection domain for testing and return its hostname."""
    rl.set_domain_config(
        name,
        DomainConfig(enable_anti_detection=True, min_delay=0.0, max_delay=0.0),
    )
    return name


class TestRateLimiterProfileRotation:
    @pytest.mark.asyncio
    async def test_session_has_profile_after_request(self):
        rl = RateLimiter()
        domain = _fast_anti_detection_domain(rl, "profile-test-1.example.com")
        await rl.await_if_needed(f"https://{domain}/events")
        profile = rl.get_domain_profile(domain)
        assert profile is not None
        assert isinstance(profile, BrowserProfile)

    @pytest.mark.asyncio
    async def test_user_agent_derived_from_profile(self):
        rl = RateLimiter()
        domain = _fast_anti_detection_domain(rl, "profile-test-2.example.com")
        await rl.await_if_needed(f"https://{domain}/events")
        ua = rl.get_domain_user_agent(domain)
        profile = rl.get_domain_profile(domain)
        assert ua == profile.user_agent

    @pytest.mark.asyncio
    async def test_custom_profiles_are_used(self):
        custom_profile = BrowserProfile(
            browser_version="chrome124",
            user_agent="CustomAgent/1.0",
            sec_ch_ua='"Custom";v="124"',
            accept_language="fr-FR,fr;q=0.9",
            platform="Windows",
            impersonation_target="chrome124",
        )
        rl = RateLimiter()
        domain = "profile-test-3.example.com"
        rl.set_domain_config(
            domain,
            DomainConfig(
                enable_anti_detection=True,
                min_delay=0.0,
                max_delay=0.0,
                browser_profiles=[custom_profile],
            ),
        )
        await rl.await_if_needed(f"https://{domain}/events")
        profile = rl.get_domain_profile(domain)
        assert profile is custom_profile

    @pytest.mark.asyncio
    async def test_get_domain_profile_none_for_unknown_domain(self):
        rl = RateLimiter()
        assert rl.get_domain_profile("unknown.example.com") is None

    @pytest.mark.asyncio
    async def test_get_domain_profile_none_for_non_anti_detection_domain(self):
        """RPS-mode domains never create a session so profile is always None."""
        rl = RateLimiter()
        rps_domain = "rps-test.example.com"
        rl.set_domain_config(rps_domain, DomainConfig(enable_anti_detection=False))
        await rl.await_if_needed(f"https://{rps_domain}/events")
        assert rl.get_domain_profile(rps_domain) is None

    @pytest.mark.asyncio
    async def test_profile_rotates_on_session_reset(self):
        """Each new session picks a profile via random.choice; mock for determinism."""
        rl = RateLimiter()
        fast_domain = "test-rotation.example.com"
        profile_a = BUILTIN_PROFILES[0]   # chrome124 macOS
        profile_b = BUILTIN_PROFILES[2]   # chrome120 macOS
        rl.set_domain_config(
            fast_domain,
            DomainConfig(
                enable_anti_detection=True,
                min_delay=0.0,
                max_delay=0.0,
                browser_profiles=[profile_a, profile_b],
            ),
        )
        # Alternate picks: a, b, a, b
        picks = [profile_a, profile_b, profile_a, profile_b]
        seen = []
        with patch("laughtrack.utilities.infrastructure.rate_limiter.random.choice", side_effect=picks):
            for _ in range(4):
                rl.reset_domain(fast_domain)
                await rl.await_if_needed(f"https://{fast_domain}/events")
                seen.append(rl.get_domain_profile(fast_domain))

        assert seen[0] is profile_a
        assert seen[1] is profile_b
        assert seen[2] is profile_a
        assert seen[3] is profile_b


# ---------------------------------------------------------------------------
# RateLimiter — async domain-lock concurrency
# ---------------------------------------------------------------------------


class TestRateLimiterConcurrency:
    @pytest.mark.asyncio
    async def test_two_concurrent_rps_calls_serialized_by_domain_lock(self):
        """Two concurrent coroutines for the same domain must be serialized.

        We patch asyncio.sleep inside rate_limiter to (a) avoid real delays and
        (b) record the order of enter/exit events.  With the per-domain
        asyncio.Lock the second coroutine cannot enter the critical section
        until the first has finished, so the events must be strictly
        interleaved: enter→exit→enter→exit.  Without the lock both sleeps
        would overlap and we'd see enter→enter→exit→exit instead.
        """
        rl = RateLimiter()
        domain = "rps-concurrency-test.example.com"
        # 2 RPS → 0.5 s min interval; both callers launched at t=0 will wait.
        rl.set_domain_config(domain, DomainConfig(requests_per_second=2.0))

        # Pre-seed slightly in the past so both coroutines still need to wait
        # but there is no risk of elapsed >= min_interval before they start.
        seeded_time = time.time() - 0.01
        rl._last_request[domain] = seeded_time

        events: list[str] = []
        original_sleep = asyncio.sleep

        async def tracked_sleep(delay: float) -> None:
            events.append("enter_sleep")
            await original_sleep(0)  # Real yield without real delay
            events.append("exit_sleep")

        with patch(
            "laughtrack.utilities.infrastructure.rate_limiter.asyncio.sleep",
            side_effect=tracked_sleep,
        ):
            await asyncio.gather(
                rl.await_if_needed(f"https://{domain}/page1"),
                rl.await_if_needed(f"https://{domain}/page2"),
            )

        # Serialized: each sleep fully completes before the next one begins.
        assert events == [
            "enter_sleep",
            "exit_sleep",
            "enter_sleep",
            "exit_sleep",
        ], f"Expected serialized sleeps, got: {events}"

        # _last_request was advanced beyond the pre-seeded value, confirming
        # that both coroutines updated it (not just a no-op pass-through).
        assert rl._last_request[domain] > seeded_time
