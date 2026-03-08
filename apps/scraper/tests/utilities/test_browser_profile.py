"""Tests for BrowserProfile, BaseHeaders.from_profile, and RateLimiter profile rotation."""

import random
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
        """UA version number must appear in sec_ch_ua for the same profile."""
        for p in BUILTIN_PROFILES:
            # Extract the numeric version from browser_version (e.g. "124" from "chrome124")
            digits = "".join(c for c in p.browser_version if c.isdigit())
            # The major version number should appear in sec_ch_ua
            assert digits in p.sec_ch_ua, (
                f"Profile {p.browser_version!r}: version digits {digits!r} "
                f"not found in sec_ch_ua {p.sec_ch_ua!r}"
            )

    def test_is_mobile_for_android(self):
        android_profiles = [p for p in BUILTIN_PROFILES if p.platform == "Android"]
        assert android_profiles, "Expected at least one Android profile in BUILTIN_PROFILES"
        for p in android_profiles:
            assert p.is_mobile is True

    def test_is_mobile_false_for_desktop(self):
        desktop_profiles = [p for p in BUILTIN_PROFILES if p.platform != "Android"]
        for p in desktop_profiles:
            assert p.is_mobile is False

    def test_to_headers_keys(self):
        p = BUILTIN_PROFILES[0]
        h = p.to_headers()
        assert "User-Agent" in h
        assert "sec-ch-ua" in h
        assert "sec-ch-ua-mobile" in h
        assert "sec-ch-ua-platform" in h
        assert "Accept-Language" in h

    def test_to_headers_mobile_flag(self):
        android = next(p for p in BUILTIN_PROFILES if p.platform == "Android")
        desktop = next(p for p in BUILTIN_PROFILES if p.platform != "Android")
        assert android.to_headers()["sec-ch-ua-mobile"] == "?1"
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

    def test_android_profile_mobile_flag(self):
        android = next(p for p in BUILTIN_PROFILES if p.platform == "Android")
        h = BaseHeaders.from_profile(android, base_type="mobile_browser")
        assert h["sec-ch-ua-mobile"] == "?1"

    def test_profile_overrides_base_ua(self):
        """The profile UA should replace whatever the base_type dict provides."""
        profile = BUILTIN_PROFILES[0]
        # desktop_browser base has a hardcoded UA; profile must win
        base_ua = BaseHeaders.DESKTOP_BROWSER_HEADERS.get("user-agent") or BaseHeaders.DESKTOP_BROWSER_HEADERS.get("User-Agent")
        h = BaseHeaders.from_profile(profile, base_type="desktop_browser")
        assert h["User-Agent"] == profile.user_agent
        assert h["User-Agent"] != base_ua or profile.user_agent == base_ua  # profile wins


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
    # Snapshot configs before test so we can restore them afterward
    saved_configs = dict(rl._domain_configs)
    for domain in list(rl._sessions.keys()):
        rl.reset_domain(domain)
    yield
    # Restore configs and clear any sessions created during the test
    rl._domain_configs = saved_configs
    for domain in list(rl._sessions.keys()):
        rl.reset_domain(domain)


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
            browser_version="chrome131",
            user_agent="CustomAgent/1.0",
            sec_ch_ua='"Custom";v="131"',
            accept_language="fr-FR,fr;q=0.9",
            platform="Windows",
            impersonation_target="chrome131",
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
    async def test_profile_rotates_on_session_reset(self):
        """After resetting, a new random profile is picked for the next request."""
        rl = RateLimiter()
        # Use a fast config to avoid real anti-detection delays
        fast_domain = "test-rotation.example.com"
        rl.set_domain_config(
            fast_domain,
            DomainConfig(
                enable_anti_detection=True,
                min_delay=0.0,
                max_delay=0.0,
            ),
        )
        seen_profiles: set = set()
        for _ in range(20):
            rl.reset_domain(fast_domain)
            await rl.await_if_needed(f"https://{fast_domain}/events")
            p = rl.get_domain_profile(fast_domain)
            assert p is not None
            seen_profiles.add(p.browser_version)
        # With 7 built-in profiles across multiple browser versions we expect
        # at least 2 distinct versions to have appeared across 20 sessions.
        assert len(seen_profiles) >= 2, (
            f"Expected profile rotation across sessions, but only saw: {seen_profiles}"
        )
