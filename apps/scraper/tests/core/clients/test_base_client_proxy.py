"""Integration tests verifying BaseApiClient proxy wiring.

Confirms that get_proxy(), report_success(), and report_failure() are
called at the right points — including the non-200 (None-return) case that
was previously a silent false-success bug.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool


PROXY_URL = "http://proxy-host:8080"


def _make_club() -> Club:
    return Club(
        id=1,
        name="Test Club",
        address="123 St",
        website="https://example.com",
        scraping_url="example.com",
        popularity=1,
        zip_code="00000",
        phone_number="000-000-0000",
        visible=True,
    )


class ConcreteClient(BaseApiClient):
    """Minimal concrete subclass for testing."""

    def _initialize_headers(self):
        return {}


def _make_pool(proxy_url: str = PROXY_URL) -> ProxyPool:
    pool = MagicMock(spec=ProxyPool)
    pool.get_proxy.return_value = proxy_url
    return pool


def _make_session_cm(status_code: int = 200, text: str = "<html/>", json_data=None):
    """Return an AsyncSession context-manager mock."""
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json = MagicMock(return_value=json_data or {"ok": True})

    session = AsyncMock()
    session.get.return_value = response
    session.post.return_value = response

    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = False
    return cm, session


# ---------------------------------------------------------------------------
# fetch_json
# ---------------------------------------------------------------------------


class TestFetchJsonProxyWiring:
    @pytest.mark.asyncio
    async def test_get_proxy_called_once_per_request(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(200, json_data={"data": 1})

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            await client.fetch_json("https://example.com/api")

        pool.get_proxy.assert_called_once()

    @pytest.mark.asyncio
    async def test_report_success_on_200_response(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(200, json_data={"data": 1})

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            await client.fetch_json("https://example.com/api")

        pool.report_success.assert_called_once_with(PROXY_URL)
        pool.report_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_report_failure_on_non200_response(self):
        """Non-200 returns None from HttpClient — must call report_failure, not report_success."""
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(status_code=503)

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            result = await client.fetch_json("https://example.com/api")

        assert result is None
        pool.report_failure.assert_called_once_with(PROXY_URL)
        pool.report_success.assert_not_called()

    @pytest.mark.asyncio
    async def test_report_failure_on_network_exception(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)

        cm = AsyncMock()
        cm.__aenter__.side_effect = ConnectionError("timeout")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            result = await client.fetch_json("https://example.com/api")

        assert result is None
        pool.report_failure.assert_called_once_with(PROXY_URL)

    @pytest.mark.asyncio
    async def test_no_pool_no_proxy_calls(self):
        """When proxy_pool is None the pool methods are never invoked."""
        client = ConcreteClient(_make_club())
        cm, _ = _make_session_cm(200, json_data={"ok": True})

        # Should not raise and should return data normally
        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            result = await client.fetch_json("https://example.com/api")

        assert result == {"ok": True}


# ---------------------------------------------------------------------------
# fetch_html
# ---------------------------------------------------------------------------


class TestFetchHtmlProxyWiring:
    @pytest.mark.asyncio
    async def test_report_success_on_200_response(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(200, text="<html>ok</html>")

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            await client.fetch_html("https://example.com/page")

        pool.report_success.assert_called_once_with(PROXY_URL)
        pool.report_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_report_failure_on_non200_response(self):
        pool = _make_pool()
        client = ConcreteClient(_make_club(), proxy_pool=pool)
        cm, _ = _make_session_cm(status_code=404)

        with patch("laughtrack.core.clients.base.AsyncSession", return_value=cm):
            result = await client.fetch_html("https://example.com/page")

        assert result is None
        pool.report_failure.assert_called_once_with(PROXY_URL)
        pool.report_success.assert_not_called()
