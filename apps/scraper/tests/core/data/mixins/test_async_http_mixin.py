"""Tests for AsyncHttpMixin session invalidation on BrowserProfile rotation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.core.data.mixins.async_http_mixin import AsyncHttpMixin


# ---------------------------------------------------------------------------
# Minimal concrete implementation for testing
# ---------------------------------------------------------------------------


class _ConcreteHttpMixin(AsyncHttpMixin):
    """Concrete subclass that satisfies the abstract `club` property."""

    def __init__(self, club=None, rate_limiter=None):
        self._club = club or MagicMock(timeout=30, scraping_url="https://example.com/events")
        self.rate_limiter = rate_limiter
        super().__init__()

    @property
    def club(self):
        return self._club


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_profile(target: str):
    profile = MagicMock()
    profile.impersonation_target = target
    return profile


def _make_limiter(target: str):
    """Return a mock rate_limiter whose get_domain_profile() yields *target*."""
    profile = _make_profile(target)
    limiter = MagicMock()
    limiter.get_domain_profile.return_value = profile
    return limiter


# ---------------------------------------------------------------------------
# Tests: _session_impersonation_target initialised on session creation
# ---------------------------------------------------------------------------


class TestSessionImpersonationTargetTracking:
    @pytest.mark.asyncio
    async def test_target_set_on_first_session_creation(self):
        mixin = _ConcreteHttpMixin(rate_limiter=_make_limiter("chrome124"))

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            MockSession.return_value = AsyncMock()
            await mixin.get_session()

        assert mixin._session_impersonation_target == "chrome124"

    @pytest.mark.asyncio
    async def test_target_cleared_on_close_session(self):
        mixin = _ConcreteHttpMixin(rate_limiter=_make_limiter("chrome124"))

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            mock_sess = AsyncMock()
            MockSession.return_value = mock_sess
            await mixin.get_session()

        await mixin.close_session()
        assert mixin._session_impersonation_target is None

    @pytest.mark.asyncio
    async def test_target_none_before_any_session(self):
        mixin = _ConcreteHttpMixin()
        assert mixin._session_impersonation_target is None


# ---------------------------------------------------------------------------
# Tests: session invalidated when profile rotates
# ---------------------------------------------------------------------------


class TestSessionInvalidatedOnProfileRotation:
    @pytest.mark.asyncio
    async def test_same_profile_reuses_session(self):
        """When the profile has not changed, the same session object is returned."""
        mixin = _ConcreteHttpMixin(rate_limiter=_make_limiter("chrome124"))

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            sess1 = AsyncMock()
            MockSession.return_value = sess1

            first = await mixin.get_session()
            second = await mixin.get_session()

        assert first is second
        assert MockSession.call_count == 1

    @pytest.mark.asyncio
    async def test_rotated_profile_closes_old_and_creates_new_session(self):
        """When the profile's impersonation_target changes, get_session() must
        close the old AsyncSession and create a new one with the updated target."""
        limiter = MagicMock()

        # First call returns profile_a, subsequent calls return profile_b
        profile_a = _make_profile("chrome124")
        profile_b = _make_profile("chrome120")
        limiter.get_domain_profile.side_effect = [profile_a, profile_b, profile_b]

        mixin = _ConcreteHttpMixin(rate_limiter=limiter)

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            sess1 = AsyncMock()
            sess2 = AsyncMock()
            MockSession.side_effect = [sess1, sess2]

            first = await mixin.get_session()
            assert mixin._session_impersonation_target == "chrome124"

            # Simulate profile rotation — next get_session() should detect the change
            second = await mixin.get_session()

        # Old session must have been closed
        sess1.close.assert_called_once()
        # A new session must have been opened with the rotated target
        assert second is sess2
        assert mixin._session_impersonation_target == "chrome120"
        assert MockSession.call_count == 2

    @pytest.mark.asyncio
    async def test_rotated_profile_new_session_uses_new_impersonation_target(self):
        """The newly created AsyncSession must be instantiated with the new target."""
        limiter = MagicMock()
        profile_a = _make_profile("chrome124")
        profile_b = _make_profile("chrome120")
        limiter.get_domain_profile.side_effect = [profile_a, profile_b, profile_b]

        mixin = _ConcreteHttpMixin(rate_limiter=limiter)

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            MockSession.side_effect = [AsyncMock(), AsyncMock()]
            await mixin.get_session()
            await mixin.get_session()

        # Second AsyncSession(...) call must use the rotated target
        second_call_kwargs = MockSession.call_args_list[1][1]
        assert second_call_kwargs.get("impersonate") == "chrome120"

    @pytest.mark.asyncio
    async def test_no_limiter_fallback_does_not_invalidate_session(self):
        """Without a rate limiter both calls return 'chrome124'; session stays alive."""
        mixin = _ConcreteHttpMixin()  # no rate_limiter

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            sess = AsyncMock()
            MockSession.return_value = sess

            first = await mixin.get_session()
            second = await mixin.get_session()

        assert first is second
        assert MockSession.call_count == 1
        sess.close.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: proxy_url parameter
# ---------------------------------------------------------------------------


class TestProxyUrl:
    @pytest.mark.asyncio
    async def test_no_proxy_url_omits_proxy_kwarg(self):
        """When proxy_url is not provided, AsyncSession must NOT receive a proxy kwarg."""
        mixin = _ConcreteHttpMixin()

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            MockSession.return_value = AsyncMock()
            await mixin.get_session()

        call_kwargs = MockSession.call_args[1]
        assert "proxy" not in call_kwargs

    @pytest.mark.asyncio
    async def test_proxy_url_forwarded_to_async_session(self):
        """When proxy_url is provided it must be forwarded to AsyncSession as ``proxy``."""
        mixin = _ConcreteHttpMixin()
        proxy = "http://proxy.example.com:8080"

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            MockSession.return_value = AsyncMock()
            await mixin.get_session(proxy_url=proxy)

        call_kwargs = MockSession.call_args[1]
        assert call_kwargs.get("proxy") == proxy

    @pytest.mark.asyncio
    async def test_same_proxy_url_reuses_session(self):
        """Repeated calls with the same proxy_url must reuse the cached session."""
        mixin = _ConcreteHttpMixin()
        proxy = "http://proxy.example.com:8080"

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            sess = AsyncMock()
            MockSession.return_value = sess

            first = await mixin.get_session(proxy_url=proxy)
            second = await mixin.get_session(proxy_url=proxy)

        assert first is second
        assert MockSession.call_count == 1

    @pytest.mark.asyncio
    async def test_changed_proxy_url_invalidates_session(self):
        """When proxy_url changes between calls the old session is closed and a new one opened."""
        mixin = _ConcreteHttpMixin()

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            sess1 = AsyncMock()
            sess2 = AsyncMock()
            MockSession.side_effect = [sess1, sess2]

            first = await mixin.get_session(proxy_url="http://proxy1.example.com")
            second = await mixin.get_session(proxy_url="http://proxy2.example.com")

        sess1.close.assert_called_once()
        assert second is sess2
        assert MockSession.call_count == 2

    @pytest.mark.asyncio
    async def test_proxy_url_cleared_on_close_session(self):
        """After close_session(), _session_proxy_url must be reset to None."""
        mixin = _ConcreteHttpMixin()

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            MockSession.return_value = AsyncMock()
            await mixin.get_session(proxy_url="http://proxy.example.com")

        await mixin.close_session()
        assert mixin._session_proxy_url is None

    @pytest.mark.asyncio
    async def test_no_proxy_to_proxy_invalidates_session(self):
        """Switching from no proxy to a proxy must close the old session."""
        mixin = _ConcreteHttpMixin()

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            sess1 = AsyncMock()
            sess2 = AsyncMock()
            MockSession.side_effect = [sess1, sess2]

            await mixin.get_session()  # no proxy
            await mixin.get_session(proxy_url="http://proxy.example.com")

        sess1.close.assert_called_once()
        assert MockSession.call_count == 2
