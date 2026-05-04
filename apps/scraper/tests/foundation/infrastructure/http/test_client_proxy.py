"""Unit tests for HttpClient residential-proxy routing.

Pins the contract added in TASK-1892:

* The allowlist of scraper keys lives in the ``scrapers`` Postgres table —
  ``scraper_proxy_registry.proxy_enabled_keys()`` is the single integration
  point. These tests stub that function so they don't touch a database.
* When ``RESIDENTIAL_PROXY_URL`` is set in the environment,
  ``HttpClient.fetch_html(scraper_key=...)`` routes allowlisted scrapers
  through the proxy and leaves non-allowlisted scrapers direct.
* When a paid-for proxy fetch still returns ``None``, a WARNING is logged
  so nightly triage can distinguish "proxy didn't help" from "scraper has
  stale selectors".
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.foundation.infrastructure.http import scraper_proxy_registry
from laughtrack.foundation.infrastructure.http.client import HttpClient


_ALLOWLISTED = "comedy_mothership"
_NOT_ALLOWLISTED = "some_other_scraper"
_PROXY_URL = "http://residential.example:8080"


def _make_response(status_code: int, text: str = ""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


@pytest.fixture(autouse=True)
def _stub_registry():
    """Pin the registry so tests don't depend on a Postgres connection."""
    scraper_proxy_registry.reset_cache()
    with patch.object(
        scraper_proxy_registry,
        "proxy_enabled_keys",
        return_value=frozenset({_ALLOWLISTED}),
    ):
        yield
    scraper_proxy_registry.reset_cache()


_NO_FALLBACK = patch(
    "laughtrack.foundation.infrastructure.http.client._get_js_browser",
    return_value=None,
)


# ---------------------------------------------------------------------------
# resolve_proxy_url — pure routing function
# ---------------------------------------------------------------------------


class TestResolveProxyUrl:
    def test_returns_env_value_for_allowlisted_key(self, monkeypatch):
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        assert HttpClient.resolve_proxy_url(_ALLOWLISTED) == _PROXY_URL

    def test_returns_none_for_non_allowlisted_key_even_when_env_set(self, monkeypatch):
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        assert HttpClient.resolve_proxy_url(_NOT_ALLOWLISTED) is None

    def test_returns_none_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("RESIDENTIAL_PROXY_URL", raising=False)
        assert HttpClient.resolve_proxy_url(_ALLOWLISTED) is None

    def test_returns_none_for_empty_or_missing_scraper_key(self, monkeypatch):
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        assert HttpClient.resolve_proxy_url(None) is None
        assert HttpClient.resolve_proxy_url("") is None

    def test_empty_env_value_treated_as_unset(self, monkeypatch):
        # An empty RESIDENTIAL_PROXY_URL must not produce a malformed proxy
        # config — coalesce to None so the request goes direct.
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", "")
        assert HttpClient.resolve_proxy_url(_ALLOWLISTED) is None


# ---------------------------------------------------------------------------
# fetch_html — auto-applies proxy via scraper_key + warns on None
# ---------------------------------------------------------------------------


class TestFetchHtmlProxyRouting:
    @pytest.mark.asyncio
    async def test_proxy_applied_for_allowlisted_scraper(self, monkeypatch):
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="<html>ok</html>")

        with _NO_FALLBACK:
            result = await HttpClient.fetch_html(
                session, "https://example.com/page", scraper_key=_ALLOWLISTED
            )

        assert result == "<html>ok</html>"
        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") == {"http": _PROXY_URL, "https": _PROXY_URL}

    @pytest.mark.asyncio
    async def test_proxy_omitted_for_non_allowlisted_scraper(self, monkeypatch):
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="<html>ok</html>")

        with _NO_FALLBACK:
            await HttpClient.fetch_html(
                session, "https://example.com/page", scraper_key=_NOT_ALLOWLISTED
            )

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") is None

    @pytest.mark.asyncio
    async def test_explicit_proxy_url_wins_over_allowlist(self, monkeypatch):
        """Caller-pinned proxy_url must not be overwritten by the auto-resolver."""
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="<html>ok</html>")
        explicit = "http://override.example:9090"

        with _NO_FALLBACK:
            await HttpClient.fetch_html(
                session,
                "https://example.com/page",
                scraper_key=_ALLOWLISTED,
                proxy_url=explicit,
            )

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") == {"http": explicit, "https": explicit}

    @pytest.mark.asyncio
    async def test_no_proxy_when_env_unset_even_for_allowlisted(self, monkeypatch):
        monkeypatch.delenv("RESIDENTIAL_PROXY_URL", raising=False)
        session = AsyncMock()
        session.get.return_value = _make_response(200, text="<html>ok</html>")

        with _NO_FALLBACK:
            await HttpClient.fetch_html(
                session, "https://example.com/page", scraper_key=_ALLOWLISTED
            )

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") is None

    @pytest.mark.asyncio
    async def test_warn_logged_when_proxied_fetch_returns_none(self, monkeypatch):
        """When we route through the proxy and still get nothing back, log a WARN.

        Comedy Mothership is paying customer #1 of this proxy budget — if a
        proxied fetch returns None, on-call needs a greppable signal to
        distinguish "proxy didn't help" from "scraper has stale selectors".
        """
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        # 403 with no Playwright fallback → fetch_html returns None
        session.get.return_value = _make_response(403, text="")

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.client.Logger.warn"
            ) as mock_warn:
                result = await HttpClient.fetch_html(
                    session,
                    "https://example.com/page",
                    scraper_key=_ALLOWLISTED,
                )

        assert result is None
        proxy_warns = [
            c for c in mock_warn.call_args_list
            if "Residential proxy fetch returned None" in c.args[0]
        ]
        assert len(proxy_warns) == 1
        assert _ALLOWLISTED in proxy_warns[0].args[0]

    @pytest.mark.asyncio
    async def test_no_proxy_warn_for_non_allowlisted_scraper_returning_none(
        self, monkeypatch
    ):
        """The proxy WARN must only fire for scrapers we actually proxied."""
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_response(403, text="")

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.client.Logger.warn"
            ) as mock_warn:
                await HttpClient.fetch_html(
                    session,
                    "https://example.com/page",
                    scraper_key=_NOT_ALLOWLISTED,
                )

        proxy_warns = [
            c for c in mock_warn.call_args_list
            if "Residential proxy fetch returned None" in c.args[0]
        ]
        assert proxy_warns == []
