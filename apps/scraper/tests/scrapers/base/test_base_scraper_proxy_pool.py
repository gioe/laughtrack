"""Unit tests: BaseScraper.get_session() wires proxy_pool into AsyncHttpMixin."""

from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.scrapers.base.base_scraper import BaseScraper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_club() -> Club:
    _c = Club(id=1, name='Test Club', address='', website='https://example.com', popularity=0, zip_code='', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://example.com/events', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_proxy_pool(proxy_url: Optional[str] = "http://proxy.example.com:8080") -> ProxyPool:
    pool = MagicMock(spec=ProxyPool)
    pool.get_proxy.return_value = proxy_url
    return pool


class _ConcreteScraper(BaseScraper):
    """Minimal concrete subclass for testing."""

    key = "test"

    async def get_data(self, target):
        return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBaseScraperProxyPool:
    @pytest.mark.asyncio
    async def test_get_session_calls_get_proxy_when_pool_configured(self):
        """When proxy_pool is set, get_session() must call pool.get_proxy()."""
        pool = _make_proxy_pool()
        scraper = _ConcreteScraper(club=_make_club(), proxy_pool=pool)

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            MockSession.return_value = AsyncMock()
            await scraper.get_session()

        pool.get_proxy.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_passes_proxy_url_to_async_session(self):
        """The URL returned by get_proxy() must be forwarded to AsyncSession as proxy."""
        proxy = "http://proxy.example.com:8080"
        pool = _make_proxy_pool(proxy_url=proxy)
        scraper = _ConcreteScraper(club=_make_club(), proxy_pool=pool)

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            MockSession.return_value = AsyncMock()
            await scraper.get_session()

        call_kwargs = MockSession.call_args[1]
        assert call_kwargs.get("proxy") == proxy

    @pytest.mark.asyncio
    async def test_get_session_no_proxy_kwarg_when_pool_is_none(self):
        """When proxy_pool is None, AsyncSession must NOT receive a proxy kwarg."""
        scraper = _ConcreteScraper(club=_make_club(), proxy_pool=None)

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            MockSession.return_value = AsyncMock()
            await scraper.get_session()

        call_kwargs = MockSession.call_args[1]
        assert "proxy" not in call_kwargs

    @pytest.mark.asyncio
    async def test_explicit_proxy_url_overrides_pool(self):
        """An explicit proxy_url argument takes precedence over the pool's URL."""
        pool = _make_proxy_pool(proxy_url="http://pool-proxy.example.com:8080")
        scraper = _ConcreteScraper(club=_make_club(), proxy_pool=pool)
        explicit_proxy = "http://explicit-proxy.example.com:9090"

        with patch("laughtrack.core.data.mixins.async_http_mixin.AsyncSession") as MockSession:
            MockSession.return_value = AsyncMock()
            await scraper.get_session(proxy_url=explicit_proxy)

        call_kwargs = MockSession.call_args[1]
        assert call_kwargs.get("proxy") == explicit_proxy
        pool.get_proxy.assert_not_called()
