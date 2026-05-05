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

from laughtrack.foundation.infrastructure.http import (
    residential_proxy_egress,
    scraper_proxy_registry,
)
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
    residential_proxy_egress.reset_cache()
    with patch.object(
        scraper_proxy_registry,
        "proxy_enabled_keys",
        return_value=frozenset({_ALLOWLISTED}),
    ):
        yield
    scraper_proxy_registry.reset_cache()
    residential_proxy_egress.reset_cache()


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

    @pytest.mark.asyncio
    async def test_no_proxy_warn_when_caller_pinned_explicit_proxy(self, monkeypatch):
        """Explicit non-residential proxy_url must not trigger the residential WARN.

        Test/dev callers sometimes pin a different proxy (e.g. a local mitmproxy
        for traffic capture). The residential WARN would falsely surface when
        no residential proxy was applied.
        """
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_response(403, text="")

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.client.Logger.warn"
            ) as mock_warn:
                result = await HttpClient.fetch_html(
                    session,
                    "https://example.com/page",
                    scraper_key=_ALLOWLISTED,
                    proxy_url="http://mitmproxy.local:8888",
                )

        assert result is None
        proxy_warns = [
            c for c in mock_warn.call_args_list
            if "Residential proxy fetch returned None" in c.args[0]
        ]
        assert proxy_warns == []


# ---------------------------------------------------------------------------
# fetch_json — auto-applies proxy via scraper_key + warns on None
# ---------------------------------------------------------------------------


def _make_json_response(status_code: int, payload, text: str = '{"ok":true}'):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json = MagicMock(return_value=payload)
    return resp


class TestFetchJsonProxyRouting:
    @pytest.mark.asyncio
    async def test_proxy_applied_for_allowlisted_scraper(self, monkeypatch):
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_json_response(200, {"data": 1})

        with _NO_FALLBACK:
            result = await HttpClient.fetch_json(
                session, "https://example.com/api", scraper_key=_ALLOWLISTED
            )

        assert result == {"data": 1}
        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") == {"http": _PROXY_URL, "https": _PROXY_URL}

    @pytest.mark.asyncio
    async def test_proxy_omitted_for_non_allowlisted_scraper(self, monkeypatch):
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_json_response(200, {"data": 1})

        with _NO_FALLBACK:
            await HttpClient.fetch_json(
                session, "https://example.com/api", scraper_key=_NOT_ALLOWLISTED
            )

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") is None

    @pytest.mark.asyncio
    async def test_explicit_proxy_url_wins_over_allowlist(self, monkeypatch):
        """Caller-pinned proxy_url must not be overwritten by the auto-resolver."""
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_json_response(200, {"data": 1})
        explicit = "http://override.example:9090"

        with _NO_FALLBACK:
            await HttpClient.fetch_json(
                session,
                "https://example.com/api",
                scraper_key=_ALLOWLISTED,
                proxy_url=explicit,
            )

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") == {"http": explicit, "https": explicit}

    @pytest.mark.asyncio
    async def test_no_proxy_when_env_unset_even_for_allowlisted(self, monkeypatch):
        monkeypatch.delenv("RESIDENTIAL_PROXY_URL", raising=False)
        session = AsyncMock()
        session.get.return_value = _make_json_response(200, {"data": 1})

        with _NO_FALLBACK:
            await HttpClient.fetch_json(
                session, "https://example.com/api", scraper_key=_ALLOWLISTED
            )

        _, kwargs = session.get.call_args
        assert kwargs.get("proxies") is None

    @pytest.mark.asyncio
    async def test_no_warn_on_200_success_via_residential_proxy(self, monkeypatch):
        """The residential-proxy WARN must NOT fire on the happy path.

        Defensive guard against a future refactor that accidentally treats
        every proxied call as a None return — the WARN is reserved for the
        'paid for proxy and got nothing' triage signal.
        """
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_json_response(200, {"data": 1})

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.client.Logger.warn"
            ) as mock_warn:
                result = await HttpClient.fetch_json(
                    session,
                    "https://example.com/api",
                    scraper_key=_ALLOWLISTED,
                )

        assert result == {"data": 1}
        proxy_warns = [
            c for c in mock_warn.call_args_list
            if "Residential proxy fetch_json returned None" in c.args[0]
        ]
        assert proxy_warns == []

    @pytest.mark.asyncio
    async def test_warn_logged_when_proxied_fetch_returns_none(self, monkeypatch):
        """Proxied fetch_json returning None must emit a greppable WARN.

        Same operational signal as fetch_html — once tixr is paying for the
        residential proxy, on-call needs to distinguish 'proxy didn't help'
        from 'API returned an unexpected payload'.
        """
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        # 403 with no Playwright fallback → fetch_json returns None
        session.get.return_value = _make_json_response(403, None, text="")

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.client.Logger.warn"
            ) as mock_warn:
                result = await HttpClient.fetch_json(
                    session,
                    "https://example.com/api",
                    scraper_key=_ALLOWLISTED,
                )

        assert result is None
        proxy_warns = [
            c for c in mock_warn.call_args_list
            if "Residential proxy fetch_json returned None" in c.args[0]
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
        session.get.return_value = _make_json_response(403, None, text="")

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.client.Logger.warn"
            ) as mock_warn:
                await HttpClient.fetch_json(
                    session,
                    "https://example.com/api",
                    scraper_key=_NOT_ALLOWLISTED,
                )

        proxy_warns = [
            c for c in mock_warn.call_args_list
            if "Residential proxy fetch_json returned None" in c.args[0]
        ]
        assert proxy_warns == []

    @pytest.mark.asyncio
    async def test_no_proxy_warn_when_caller_pinned_explicit_proxy(self, monkeypatch):
        """Explicit non-residential proxy_url must not trigger the residential WARN."""
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_json_response(403, None, text="")

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.client.Logger.warn"
            ) as mock_warn:
                result = await HttpClient.fetch_json(
                    session,
                    "https://example.com/api",
                    scraper_key=_ALLOWLISTED,
                    proxy_url="http://mitmproxy.local:8888",
                )

        assert result is None
        proxy_warns = [
            c for c in mock_warn.call_args_list
            if "Residential proxy fetch_json returned None" in c.args[0]
        ]
        assert proxy_warns == []


# ---------------------------------------------------------------------------
# Egress IP diagnostic — captured on first None-fetch per scraper-key per run
# ---------------------------------------------------------------------------


class TestResidentialProxyEgressIp:
    """Egress-IP diagnostic added in TASK-1939.

    The "Residential proxy fetch returned None" WARN tells on-call a
    proxied request failed but not whether Decodo's egress IP itself was
    blocked vs. the target being down or 5xx-ing. The egress IP is
    captured on the first None-fetch per scraper-key per run so on-call
    can cross-check against Decodo's dashboard or known-block lists.
    """

    @pytest.mark.asyncio
    async def test_egress_ip_logged_on_first_failure(self, monkeypatch):
        """First proxied-fetch failure resolves and logs the egress IP."""
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_response(403, text="")

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.residential_proxy_egress._fetch_egress_ip",
                new_callable=AsyncMock,
            ) as mock_fetch_ip:
                mock_fetch_ip.return_value = "203.0.113.42"
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
        assert "egress_ip='203.0.113.42'" in proxy_warns[0].args[0]
        mock_fetch_ip.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_egress_ip_cached_per_key(self, monkeypatch):
        """Subsequent failures for the same scraper key reuse the cached IP."""
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_response(403, text="")

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.residential_proxy_egress._fetch_egress_ip",
                new_callable=AsyncMock,
            ) as mock_fetch_ip:
                mock_fetch_ip.return_value = "203.0.113.42"
                with patch(
                    "laughtrack.foundation.infrastructure.http.client.Logger.warn"
                ) as mock_warn:
                    await HttpClient.fetch_html(
                        session,
                        "https://example.com/page1",
                        scraper_key=_ALLOWLISTED,
                    )
                    await HttpClient.fetch_html(
                        session,
                        "https://example.com/page2",
                        scraper_key=_ALLOWLISTED,
                    )

        # Resolver hit the network only on the first failure — the second
        # WARN reuses the cached IP without re-resolving.
        assert mock_fetch_ip.await_count == 1
        proxy_warns = [
            c for c in mock_warn.call_args_list
            if "Residential proxy fetch returned None" in c.args[0]
        ]
        assert len(proxy_warns) == 2
        assert all("egress_ip='203.0.113.42'" in c.args[0] for c in proxy_warns)

    @pytest.mark.asyncio
    async def test_unresolved_sentinel_cached_on_resolver_failure(self, monkeypatch):
        """Resolver failure caches the ``<unresolved>`` sentinel — no re-resolve loop.

        When ipify is globally unreachable (DNS, timeout, non-200), the
        helper must still cap network spend at one round-trip per scraper
        key per run; otherwise a broken egress would multiply log noise
        across hundreds of fetches in a long nightly scrape.
        """
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _PROXY_URL)
        session = AsyncMock()
        session.get.return_value = _make_response(403, text="")

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.residential_proxy_egress._fetch_egress_ip",
                new_callable=AsyncMock,
            ) as mock_fetch_ip:
                mock_fetch_ip.return_value = None
                with patch(
                    "laughtrack.foundation.infrastructure.http.client.Logger.warn"
                ) as mock_warn:
                    await HttpClient.fetch_html(
                        session, "https://example.com/page1",
                        scraper_key=_ALLOWLISTED,
                    )
                    await HttpClient.fetch_html(
                        session, "https://example.com/page2",
                        scraper_key=_ALLOWLISTED,
                    )

        assert mock_fetch_ip.await_count == 1
        proxy_warns = [
            c for c in mock_warn.call_args_list
            if "Residential proxy fetch returned None" in c.args[0]
        ]
        assert len(proxy_warns) == 2
        assert all("egress_ip='<unresolved>'" in c.args[0] for c in proxy_warns)

    @pytest.mark.asyncio
    async def test_egress_ip_skipped_when_unset(self, monkeypatch):
        """No IP-resolution call is attempted when RESIDENTIAL_PROXY_URL is unset.

        The residential WARN itself does not fire (residential proxy was
        never auto-applied), so the egress-IP resolver must never be
        invoked — otherwise we'd burn an unnecessary round-trip on every
        nightly run that has the secret unwired.
        """
        monkeypatch.delenv("RESIDENTIAL_PROXY_URL", raising=False)
        session = AsyncMock()
        session.get.return_value = _make_response(403, text="")

        with _NO_FALLBACK:
            with patch(
                "laughtrack.foundation.infrastructure.http.residential_proxy_egress._fetch_egress_ip",
                new_callable=AsyncMock,
            ) as mock_fetch_ip:
                await HttpClient.fetch_html(
                    session,
                    "https://example.com/page",
                    scraper_key=_ALLOWLISTED,
                )

        mock_fetch_ip.assert_not_awaited()
