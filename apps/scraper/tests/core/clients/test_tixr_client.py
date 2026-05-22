"""Unit tests for TixrClient._fetch_tixr_page, _extract_jsonld_event, and _create_show_from_jsonld."""

import json
from unittest.mock import patch

import pytest
import pytz

from laughtrack.core.clients.tixr import client as tixr_module
from laughtrack.core.clients.tixr.client import TixrClient
from laughtrack.core.clients.tixr.tixr_failure_monitor import FailureType
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.foundation.infrastructure.http import (
    residential_proxy_egress,
    scraper_proxy_registry,
)
from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.foundation.infrastructure.http.diagnostics import (
    ScrapeDiagnostics,
    bind_diagnostics,
    reset_diagnostics,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def silence_logging(monkeypatch):
    monkeypatch.setattr(tixr_module.TixrClient, "log_warning", lambda *a, **k: None)
    monkeypatch.setattr(tixr_module.TixrClient, "log_error", lambda *a, **k: None)
    monkeypatch.setattr(tixr_module.TixrClient, "log_info", lambda *a, **k: None)


@pytest.fixture
def stub_base_init(monkeypatch):
    def _init(self, club, proxy_pool=None):
        self.club = club
        self.headers = {}
        self.http_client = HttpClient()
        self.proxy_pool = None
    monkeypatch.setattr(BaseApiClient, "__init__", _init)


class _RecordingMonitor:
    """Captures record_request_result calls for assertion."""

    def __init__(self):
        self.calls = []

    def record_request_result(self, **kwargs):
        self.calls.append(kwargs)
        return None


def _club() -> Club:
    return Club(
        id=7,
        name="Test Club",
        address="123 Main St",
        website="https://example.com",
        popularity=1,
        zip_code="10001",
        phone_number="212-000-0000",
        visible=True,
        scraping_sources=[
            ScrapingSource(platform="tixr", scraper_key="tixr", source_url="example.com"),
        ],
    )


# ---------------------------------------------------------------------------
# _fetch_tixr_page
# ---------------------------------------------------------------------------

class TestFetchTixrPage:

    @pytest.mark.asyncio
    async def test_200_returns_html(self, monkeypatch, stub_base_init):
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())

        class FakeResponse:
            status_code = 200
            text = "<html>hello</html>"

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result == "<html>hello</html>"

    @pytest.mark.asyncio
    async def test_non_200_returns_none(self, monkeypatch, stub_base_init):
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())

        class FakeResponse:
            status_code = 403
            text = "Forbidden"

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self, monkeypatch, stub_base_init):
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                raise ConnectionError("network down")

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result is None

    @pytest.mark.asyncio
    async def test_datadome_403_triggers_playwright_fallback(self, monkeypatch, stub_base_init):
        """A DataDome 403 returns rescued HTML via the Playwright fallback."""
        monkeypatch.delenv("PLAYWRIGHT_FALLBACK", raising=False)
        client = TixrClient(_club())
        monitor = _RecordingMonitor()
        client._failure_monitor = monitor

        class FakeResponse:
            status_code = 403
            text = "<html><body>datadome challenge</body></html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        class FakeBrowser:
            async def fetch_html(self, url, proxy_url=None):
                return "<html>rescued by playwright</html>"

        monkeypatch.setattr(
            "laughtrack.core.clients.tixr.client._get_js_browser",
            lambda: FakeBrowser(),
        )

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result == "<html>rescued by playwright</html>"
        # DataDome block on the original 403 must have been recorded via the
        # failure monitor so TixrAlertSystem can aggregate group-page blocks
        # alongside event-detail blocks — even though Playwright recovered.
        assert len(monitor.calls) == 1
        assert monitor.calls[0]["status_code"] == 403

    @pytest.mark.asyncio
    async def test_datadome_200_interstitial_records_cookie_failure(self, monkeypatch, stub_base_init):
        """A 200 response whose body is a DataDome interstitial is recorded as DATADOME_COOKIE."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())
        monitor = _RecordingMonitor()
        client._failure_monitor = monitor

        warnings: list = []
        monkeypatch.setattr(client, "log_warning", lambda msg: warnings.append(msg))

        class FakeResponse:
            status_code = 200
            text = "<html>datadome blocked</html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        # PLAYWRIGHT_FALLBACK=0 → bot-block → no rescue → None.
        assert result is None
        assert len(monitor.calls) == 1
        call = monitor.calls[0]
        # Real status is passed through unchanged — TixrFailureMonitor now
        # inspects the body itself and does not require a 200→403 coercion.
        assert call["status_code"] == 200
        assert "datadome" in call["response_body"].lower()
        # A dedicated DataDome WARN must be surfaced for triage.
        assert any("datadome" in w.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_datadome_200_captcha_records_captcha_failure(self, monkeypatch, stub_base_init):
        """A 200 with a DataDome captcha interstitial classifies as DATADOME_CAPTCHA."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())
        monitor = _RecordingMonitor()
        client._failure_monitor = monitor

        warnings: list = []
        monkeypatch.setattr(client, "log_warning", lambda msg: warnings.append(msg))

        class FakeResponse:
            status_code = 200
            text = (
                "<html>DataDome captcha challenge from "
                "https://geo.captcha-delivery.com/captcha/</html>"
            )
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert len(monitor.calls) == 1
        # WARN must identify the captcha variant so triage can distinguish it
        # from a plain DataDome cookie block.
        assert any(FailureType.DATADOME_CAPTCHA.value in w for w in warnings)

    @pytest.mark.asyncio
    async def test_datadome_diagnostics_capture_structured_fields(self, monkeypatch, stub_base_init):
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())
        client._failure_monitor = _RecordingMonitor()

        class FakeResponse:
            status_code = 200
            text = (
                "<html>DataDome captcha challenge from "
                "https://geo.captcha-delivery.com/captcha/</html>"
            )
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            await client._fetch_tixr_page("https://tixr.com/groups/x")
        finally:
            reset_diagnostics(token)

        assert diagnostics.bot_block_detected is True
        assert diagnostics.bot_block_signature == FailureType.DATADOME_CAPTCHA.value
        assert diagnostics.bot_block_provider == "datadome"
        assert diagnostics.bot_block_type == "captcha"
        assert diagnostics.bot_block_source == "captcha_body"
        assert diagnostics.bot_block_stage == "direct_fetch"

    @pytest.mark.asyncio
    async def test_x_datadome_header_records_cookie_failure(self, monkeypatch, stub_base_init):
        """An X-DataDome response header on any status flags DATADOME_COOKIE."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())
        monitor = _RecordingMonitor()
        client._failure_monitor = monitor

        warnings: list = []
        monkeypatch.setattr(client, "log_warning", lambda msg: warnings.append(msg))

        class FakeResponse:
            status_code = 200
            # No datadome content in the body — the header alone is the signal.
            text = "<html><body>payload</body></html>"
            headers = {"X-DataDome": "protected"}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert len(monitor.calls) == 1
        assert any("datadome" in w.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_500_returns_none_without_playwright_fallback(self, monkeypatch, stub_base_init):
        """5xx responses short-circuit: no DataDome recording, no Playwright rescue."""
        client = TixrClient(_club())
        monitor = _RecordingMonitor()
        client._failure_monitor = monitor

        class FakeResponse:
            status_code = 503
            # Body happens to contain a DataDome marker — should NOT be recorded
            # because 5xx is a server-side failure classified elsewhere.
            text = "<html>datadome outage</html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        browser_called = {"value": False}

        class FakeBrowser:
            async def fetch_html(self, url, proxy_url=None):
                browser_called["value"] = True
                return "<html>should never be returned</html>"

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")
        monkeypatch.setattr(
            "laughtrack.core.clients.tixr.client._get_js_browser",
            lambda: FakeBrowser(),
        )

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result is None
        assert browser_called["value"] is False
        assert monitor.calls == []

    @pytest.mark.asyncio
    async def test_normal_200_does_not_invoke_failure_monitor(self, monkeypatch, stub_base_init):
        """A clean 200 response does not record any failure."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())
        monitor = _RecordingMonitor()
        client._failure_monitor = monitor

        class FakeResponse:
            status_code = 200
            text = "<html><body>actual event listing</body></html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result == "<html><body>actual event listing</body></html>"
        assert monitor.calls == []

    @pytest.mark.asyncio
    async def test_proxy_pool_threads_proxy_into_session_and_reports_success(
        self, monkeypatch, stub_base_init
    ):
        """When a proxy_pool is configured, the curl-cffi GET is routed
        through the proxy and a clean 200 reports success to the pool."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())

        pool = _StubProxyPool("http://user:pass@proxy.example.com:8080")
        client.proxy_pool = pool

        seen_proxies: list = []

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                seen_proxies.append(proxies)
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result == "<html>ok</html>"
        # Proxy dict threaded through for both schemes — matches base.py pattern.
        assert seen_proxies == [
            {"http": "http://user:pass@proxy.example.com:8080",
             "https": "http://user:pass@proxy.example.com:8080"}
        ]
        assert pool.successes == ["http://user:pass@proxy.example.com:8080"]
        assert pool.failures == []

    @pytest.mark.asyncio
    async def test_proxy_pool_reports_failure_on_network_exception(
        self, monkeypatch, stub_base_init
    ):
        """A network exception during the proxied fetch must surface as a
        proxy failure so the pool can retire a bad proxy after max_failures."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())

        pool = _StubProxyPool("http://proxy.example.com:8080")
        client.proxy_pool = pool

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                raise ConnectionError("proxy tunnel down")

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result is None
        assert pool.failures == ["http://proxy.example.com:8080"]
        assert pool.successes == []

    @pytest.mark.asyncio
    async def test_proxy_pool_threads_proxy_into_playwright_fallback(
        self, monkeypatch, stub_base_init
    ):
        """The Playwright rescue inherits the same proxy_url so the fallback
        fetches from the same egress IP as curl-cffi did."""
        monkeypatch.delenv("PLAYWRIGHT_FALLBACK", raising=False)
        client = TixrClient(_club())
        client._failure_monitor = _RecordingMonitor()

        pool = _StubProxyPool("http://proxy.example.com:8080")
        client.proxy_pool = pool

        class FakeResponse:
            status_code = 403
            text = "<html><body>datadome challenge</body></html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        browser_calls: list = []

        class FakeBrowser:
            async def fetch_html(self, url, proxy_url=None):
                browser_calls.append({"url": url, "proxy_url": proxy_url})
                return "<html>rescued</html>"

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")
        monkeypatch.setattr(
            "laughtrack.core.clients.tixr.client._get_js_browser",
            lambda: FakeBrowser(),
        )

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result == "<html>rescued</html>"
        assert len(browser_calls) == 1
        assert browser_calls[0]["proxy_url"] == "http://proxy.example.com:8080"
        # Playwright recovered → the proxy ultimately served content, so report success.
        assert pool.successes == ["http://proxy.example.com:8080"]
        assert pool.failures == []

    @pytest.mark.asyncio
    async def test_no_proxy_pool_omits_proxies_kwarg(self, monkeypatch, stub_base_init):
        """With no proxy_pool configured, session.get receives proxies=None."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        # apps/scraper/.env defines RESIDENTIAL_PROXY_URL for dev runs, and
        # tixr is allowlisted in scraper_proxy_registry — so without this,
        # _fetch_tixr_page's HttpClient.resolve_proxy_url fallback leaks the
        # dev proxy into the session.get call. Setting to "" (rather than
        # delenv) is required because resolve_proxy_url's call into
        # scraper_proxy_registry.proxy_enabled_keys triggers a DB connection
        # via ConfigManager, which re-runs load_dotenv and would re-populate
        # a deleted RESIDENTIAL_PROXY_URL from .env. load_dotenv defaults to
        # override=False, so an explicitly-empty value sticks; the
        # `or None` in resolve_proxy_url then yields None.
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", "")
        client = TixrClient(_club())
        # stub_base_init already sets proxy_pool=None; be explicit for the test.
        client.proxy_pool = None

        seen_proxies: list = []

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                seen_proxies.append(proxies)
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result == "<html>ok</html>"
        assert seen_proxies == [None]

    @pytest.mark.asyncio
    async def test_proxy_pool_reports_failure_on_5xx(
        self, monkeypatch, stub_base_init
    ):
        """5xx short-circuits without Playwright but must still penalize the proxy."""
        client = TixrClient(_club())

        pool = _StubProxyPool("http://proxy.example.com:8080")
        client.proxy_pool = pool

        class FakeResponse:
            status_code = 503
            text = "<html>upstream</html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result is None
        assert pool.failures == ["http://proxy.example.com:8080"]
        assert pool.successes == []

    @pytest.mark.asyncio
    async def test_proxy_pool_reports_failure_when_browser_unavailable(
        self, monkeypatch, stub_base_init
    ):
        """When PLAYWRIGHT_FALLBACK is disabled and curl-cffi was bot-blocked,
        no rescue is possible — the proxy must be marked as failed."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        client = TixrClient(_club())
        client._failure_monitor = _RecordingMonitor()

        pool = _StubProxyPool("http://proxy.example.com:8080")
        client.proxy_pool = pool

        class FakeResponse:
            status_code = 403
            text = "<html><body>datadome challenge</body></html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result is None
        assert pool.failures == ["http://proxy.example.com:8080"]
        assert pool.successes == []

    @pytest.mark.asyncio
    async def test_proxy_pool_reports_failure_when_playwright_raises(
        self, monkeypatch, stub_base_init
    ):
        """If the Playwright fallback itself raises, the proxy must be marked as failed."""
        monkeypatch.delenv("PLAYWRIGHT_FALLBACK", raising=False)
        client = TixrClient(_club())
        client._failure_monitor = _RecordingMonitor()

        pool = _StubProxyPool("http://proxy.example.com:8080")
        client.proxy_pool = pool

        class FakeResponse:
            status_code = 403
            text = "<html><body>datadome challenge</body></html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        class FakeBrowser:
            async def fetch_html(self, url, proxy_url=None):
                raise RuntimeError("playwright crashed")

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")
        monkeypatch.setattr(
            "laughtrack.core.clients.tixr.client._get_js_browser",
            lambda: FakeBrowser(),
        )

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result is None
        assert pool.failures == ["http://proxy.example.com:8080"]
        assert pool.successes == []


class _StubProxyPool:
    """Minimal ProxyPool stand-in that records success/failure calls."""

    def __init__(self, proxy_url: str):
        self._proxy_url = proxy_url
        self.successes: list = []
        self.failures: list = []

    def get_proxy(self):
        return self._proxy_url

    def report_success(self, proxy_url):
        self.successes.append(proxy_url)

    def report_failure(self, proxy_url):
        self.failures.append(proxy_url)


# ---------------------------------------------------------------------------
# Residential-proxy auto-routing for _fetch_tixr_page (TASK-1936)
#
# When the rotating proxy_pool returns None, allowlisted scrapers (TixrClient:
# key="tixr") must fall back to RESIDENTIAL_PROXY_URL via
# HttpClient.resolve_proxy_url so the inline group/event-page HTML path picks
# up the same residential coverage as fetch_html / fetch_json.
# ---------------------------------------------------------------------------

_RESIDENTIAL_PROXY_URL = "http://residential.example:8080"


@pytest.fixture
def stub_registry_tixr_allowlisted():
    """Pin the registry so the residential-proxy allowlist contains 'tixr'."""
    scraper_proxy_registry.reset_cache()
    residential_proxy_egress.reset_cache()
    with patch.object(
        scraper_proxy_registry,
        "proxy_enabled_keys",
        return_value=frozenset({"tixr"}),
    ):
        yield
    scraper_proxy_registry.reset_cache()
    residential_proxy_egress.reset_cache()


@pytest.fixture
def stub_registry_empty():
    """Pin the registry so no scraper is allowlisted."""
    scraper_proxy_registry.reset_cache()
    residential_proxy_egress.reset_cache()
    with patch.object(
        scraper_proxy_registry,
        "proxy_enabled_keys",
        return_value=frozenset(),
    ):
        yield
    scraper_proxy_registry.reset_cache()
    residential_proxy_egress.reset_cache()


class TestFetchTixrPageResidentialProxy:

    @pytest.mark.asyncio
    async def test_routes_through_residential_when_pool_is_none_and_key_allowlisted(
        self, monkeypatch, stub_base_init, stub_registry_tixr_allowlisted
    ):
        """No pool + allowlisted key + env set → request routes through residential proxy."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _RESIDENTIAL_PROXY_URL)
        client = TixrClient(_club())
        client.proxy_pool = None

        seen_proxies: list = []

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                seen_proxies.append(proxies)
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result == "<html>ok</html>"
        assert seen_proxies == [
            {"http": _RESIDENTIAL_PROXY_URL, "https": _RESIDENTIAL_PROXY_URL}
        ]

    @pytest.mark.asyncio
    async def test_no_residential_when_key_not_allowlisted(
        self, monkeypatch, stub_base_init, stub_registry_empty
    ):
        """Empty allowlist → tixr key is not routed through residential proxy."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _RESIDENTIAL_PROXY_URL)
        client = TixrClient(_club())
        client.proxy_pool = None

        seen_proxies: list = []

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                seen_proxies.append(proxies)
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result == "<html>ok</html>"
        assert seen_proxies == [None]

    @pytest.mark.asyncio
    async def test_pool_url_wins_over_residential(
        self, monkeypatch, stub_base_init, stub_registry_tixr_allowlisted
    ):
        """A configured proxy_pool URL takes precedence over RESIDENTIAL_PROXY_URL."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _RESIDENTIAL_PROXY_URL)
        client = TixrClient(_club())
        pool = _StubProxyPool("http://pool.example.com:8080")
        client.proxy_pool = pool

        seen_proxies: list = []

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                seen_proxies.append(proxies)
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result == "<html>ok</html>"
        assert seen_proxies == [
            {"http": "http://pool.example.com:8080",
             "https": "http://pool.example.com:8080"}
        ]
        # Pool URL was used → pool got the success report.
        assert pool.successes == ["http://pool.example.com:8080"]

    @pytest.mark.asyncio
    async def test_no_proxy_when_env_unset(
        self, monkeypatch, stub_base_init, stub_registry_tixr_allowlisted
    ):
        """RESIDENTIAL_PROXY_URL unset → no proxy, even for allowlisted key."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        monkeypatch.delenv("RESIDENTIAL_PROXY_URL", raising=False)
        client = TixrClient(_club())
        client.proxy_pool = None

        seen_proxies: list = []

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                seen_proxies.append(proxies)
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result == "<html>ok</html>"
        assert seen_proxies == [None]

    @pytest.mark.asyncio
    async def test_residential_threads_into_playwright_fallback(
        self, monkeypatch, stub_base_init, stub_registry_tixr_allowlisted
    ):
        """Playwright rescue inherits the residential URL when curl-cffi is bot-blocked."""
        monkeypatch.delenv("PLAYWRIGHT_FALLBACK", raising=False)
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _RESIDENTIAL_PROXY_URL)
        client = TixrClient(_club())
        client.proxy_pool = None
        client._failure_monitor = _RecordingMonitor()

        class FakeResponse:
            status_code = 403
            text = "<html><body>datadome challenge</body></html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        browser_calls: list = []

        class FakeBrowser:
            async def fetch_html(self, url, proxy_url=None):
                browser_calls.append({"url": url, "proxy_url": proxy_url})
                return "<html>rescued</html>"

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")
        monkeypatch.setattr(
            "laughtrack.core.clients.tixr.client._get_js_browser",
            lambda: FakeBrowser(),
        )

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result == "<html>rescued</html>"
        assert browser_calls == [
            {"url": "https://tixr.com/groups/x/events/y", "proxy_url": _RESIDENTIAL_PROXY_URL}
        ]

    @pytest.mark.asyncio
    async def test_warn_emitted_when_residential_fails_to_recover(
        self, monkeypatch, stub_base_init, stub_registry_tixr_allowlisted
    ):
        """When residential is auto-applied and Playwright still returns None, log WARN."""
        monkeypatch.delenv("PLAYWRIGHT_FALLBACK", raising=False)
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _RESIDENTIAL_PROXY_URL)
        client = TixrClient(_club())
        client.proxy_pool = None
        client._failure_monitor = _RecordingMonitor()

        warns: list = []
        monkeypatch.setattr(
            tixr_module.Logger,
            "warn",
            staticmethod(lambda msg, ctx=None: warns.append(msg)),
        )

        class FakeResponse:
            status_code = 403
            text = "<html><body>datadome challenge</body></html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        class FakeBrowser:
            async def fetch_html(self, url, proxy_url=None):
                return None

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")
        monkeypatch.setattr(
            "laughtrack.core.clients.tixr.client._get_js_browser",
            lambda: FakeBrowser(),
        )

        async def _fake_egress_ip(_proxy_url):
            return "203.0.113.99"

        monkeypatch.setattr(
            residential_proxy_egress, "_fetch_egress_ip", _fake_egress_ip
        )

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result is None
        assert any(
            "Residential proxy fetch returned None" in w
            and "scraper='tixr'" in w
            and "egress_ip='203.0.113.99'" in w
            for w in warns
        ), f"Expected residential-proxy WARN with egress_ip, got: {warns}"

    @pytest.mark.asyncio
    async def test_residential_applied_when_pool_exists_but_exhausted(
        self, monkeypatch, stub_base_init, stub_registry_tixr_allowlisted
    ):
        """Pool configured but get_proxy() returns None → residential is auto-applied
        and no success/failure is reported back to the pool."""
        monkeypatch.setenv("PLAYWRIGHT_FALLBACK", "0")
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _RESIDENTIAL_PROXY_URL)
        client = TixrClient(_club())

        class ExhaustedPool:
            def __init__(self):
                self.successes: list = []
                self.failures: list = []

            def get_proxy(self):
                return None

            def report_success(self, proxy_url):
                self.successes.append(proxy_url)

            def report_failure(self, proxy_url):
                self.failures.append(proxy_url)

        pool = ExhaustedPool()
        client.proxy_pool = pool

        seen_proxies: list = []

        class FakeResponse:
            status_code = 200
            text = "<html>ok</html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                seen_proxies.append(proxies)
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result == "<html>ok</html>"
        # Residential URL was used because pool yielded None.
        assert seen_proxies == [
            {"http": _RESIDENTIAL_PROXY_URL, "https": _RESIDENTIAL_PROXY_URL}
        ]
        # Pool received no outcome — it doesn't own the residential URL.
        assert pool.successes == []
        assert pool.failures == []

    @pytest.mark.asyncio
    async def test_warn_suppressed_when_pool_url_was_used(
        self, monkeypatch, stub_base_init, stub_registry_tixr_allowlisted
    ):
        """Caller-pinned proxy_pool URLs are not residential — suppress the WARN."""
        monkeypatch.delenv("PLAYWRIGHT_FALLBACK", raising=False)
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", _RESIDENTIAL_PROXY_URL)
        client = TixrClient(_club())
        client.proxy_pool = _StubProxyPool("http://pool.example.com:8080")
        client._failure_monitor = _RecordingMonitor()

        warns: list = []
        monkeypatch.setattr(
            tixr_module.Logger,
            "warn",
            staticmethod(lambda msg, ctx=None: warns.append(msg)),
        )

        class FakeResponse:
            status_code = 403
            text = "<html><body>datadome challenge</body></html>"
            headers: dict = {}

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                return FakeResponse()

        class FakeBrowser:
            async def fetch_html(self, url, proxy_url=None):
                return None

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")
        monkeypatch.setattr(
            "laughtrack.core.clients.tixr.client._get_js_browser",
            lambda: FakeBrowser(),
        )

        result = await client._fetch_tixr_page("https://tixr.com/groups/x")
        assert result is None
        assert not any(
            "Residential proxy fetch returned None" in w for w in warns
        ), f"Did not expect residential-proxy WARN, got: {warns}"


# Async no-op coroutine used as stub for _apply_rate_limit
async def _noop(*args, **kwargs):
    pass


class _FakeSession:
    """Reusable async context manager stub for AsyncSession used across _fetch_tixr_page tests."""

    def __init__(self, impersonate, timeout):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url, headers=None, proxies=None, **kwargs):
        raise NotImplementedError("subclass must override get()")


# ---------------------------------------------------------------------------
# _extract_jsonld_event
# ---------------------------------------------------------------------------

class TestExtractJsonldEvent:

    def _client(self, monkeypatch) -> TixrClient:
        monkeypatch.setattr(BaseApiClient, "__init__", lambda self, club, proxy_pool=None: (
            setattr(self, "club", club) or setattr(self, "headers", {})
        ))
        return TixrClient(_club())

    def _wrap(self, data: object) -> str:
        """Wrap data in a minimal HTML page with a JSON-LD script block."""
        return (
            '<html><head>'
            '<script type="application/ld+json">'
            + json.dumps(data)
            + '</script></head><body></body></html>'
        )

    def test_bare_dict_event(self, monkeypatch):
        client = self._client(monkeypatch)
        data = {"@type": "Event", "name": "Comedy Night"}
        html = self._wrap(data)
        result = client._extract_jsonld_event(html)
        assert result is not None
        assert result["name"] == "Comedy Night"

    def test_list_root(self, monkeypatch):
        client = self._client(monkeypatch)
        data = [
            {"@type": "Organization", "name": "The Club"},
            {"@type": "Event", "name": "Stand-Up"},
        ]
        html = self._wrap(data)
        result = client._extract_jsonld_event(html)
        assert result is not None
        assert result["name"] == "Stand-Up"

    def test_graph_wrapper(self, monkeypatch):
        client = self._client(monkeypatch)
        data = {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebSite", "url": "https://tixr.com"},
                {"@type": "MusicEvent", "name": "Live Music"},
            ],
        }
        html = self._wrap(data)
        result = client._extract_jsonld_event(html)
        assert result is not None
        assert result["name"] == "Live Music"

    def test_array_type_field(self, monkeypatch):
        client = self._client(monkeypatch)
        data = {"@type": ["Organization", "ComedyEvent"], "name": "Funny Night"}
        html = self._wrap(data)
        result = client._extract_jsonld_event(html)
        assert result is not None
        assert result["name"] == "Funny Night"

    def test_malformed_json_skipped(self, monkeypatch):
        client = self._client(monkeypatch)
        html = (
            '<html><head>'
            '<script type="application/ld+json">{bad json}</script>'
            '<script type="application/ld+json">{"@type": "Event", "name": "Good"}</script>'
            '</head><body></body></html>'
        )
        result = client._extract_jsonld_event(html)
        assert result is not None
        assert result["name"] == "Good"

    def test_no_event_block_returns_none(self, monkeypatch):
        client = self._client(monkeypatch)
        data = {"@type": "WebSite", "url": "https://tixr.com"}
        html = self._wrap(data)
        result = client._extract_jsonld_event(html)
        assert result is None

    def test_no_script_tags_returns_none(self, monkeypatch):
        client = self._client(monkeypatch)
        result = client._extract_jsonld_event("<html><body>plain</body></html>")
        assert result is None

    def test_theater_event_type_matched(self, monkeypatch):
        client = self._client(monkeypatch)
        data = {"@type": "TheaterEvent", "name": "Drama Show"}
        html = self._wrap(data)
        result = client._extract_jsonld_event(html)
        assert result is not None
        assert result["@type"] == "TheaterEvent"


# ---------------------------------------------------------------------------
# _create_show_from_jsonld
# ---------------------------------------------------------------------------

class TestCreateShowFromJsonld:

    def _client(self, monkeypatch) -> TixrClient:
        monkeypatch.setattr(BaseApiClient, "__init__", lambda self, club, proxy_pool=None: (
            setattr(self, "club", club) or setattr(self, "headers", {})
        ))
        return TixrClient(_club())

    def _valid_data(self) -> dict:
        return {
            "@type": "Event",
            "name": "Comedy Night",
            "startDate": "2026-05-01T20:00:00-04:00",
            "url": "https://tixr.com/groups/comedy/events/test-123",
            "performer": [{"@type": "Person", "name": "Alice Smith"}],
            "offers": [
                {
                    "price": "25.00",
                    "availability": "https://schema.org/InStock",
                    "url": "https://tixr.com/groups/comedy/events/test-123",
                    "name": "General Admission",
                }
            ],
        }

    def test_valid_data_returns_show(self, monkeypatch):
        client = self._client(monkeypatch)
        show = client._create_show_from_jsonld(self._valid_data(), "https://tixr.com/x")
        assert show is not None
        assert show.name == "Comedy Night"
        assert show.club_id == 7

    def test_missing_start_date_returns_none(self, monkeypatch):
        client = self._client(monkeypatch)
        data = self._valid_data()
        del data["startDate"]
        result = client._create_show_from_jsonld(data, "https://tixr.com/x")
        assert result is None

    def test_performer_as_string(self, monkeypatch):
        client = self._client(monkeypatch)
        data = self._valid_data()
        data["performer"] = ["Bob Jones", "Carol Lee"]
        show = client._create_show_from_jsonld(data, "https://tixr.com/x")
        assert show is not None
        names = [c.name for c in show.lineup]
        assert "Bob Jones" in names
        assert "Carol Lee" in names

    def test_performer_as_dict(self, monkeypatch):
        client = self._client(monkeypatch)
        data = self._valid_data()
        data["performer"] = [{"@type": "Person", "name": "Dave Chappelle"}]
        show = client._create_show_from_jsonld(data, "https://tixr.com/x")
        assert show is not None
        assert show.lineup[0].name == "Dave Chappelle"

    def test_sold_out_offer(self, monkeypatch):
        client = self._client(monkeypatch)
        data = self._valid_data()
        data["offers"] = [
            {
                "price": "30.00",
                "availability": "https://schema.org/SoldOut",
                "url": "https://tixr.com/x",
                "name": "VIP",
            }
        ]
        show = client._create_show_from_jsonld(data, "https://tixr.com/x")
        assert show is not None
        assert show.tickets[0].sold_out is True

    def test_empty_offers_inserts_placeholder(self, monkeypatch):
        warnings = []
        client = self._client(monkeypatch)
        # Instance-level patch intentionally shadows the class-level silence_logging autouse
        # fixture so this test can capture warning calls while the others stay silent.
        monkeypatch.setattr(client, "log_warning", lambda msg: warnings.append(msg))
        data = self._valid_data()
        data["offers"] = []
        show = client._create_show_from_jsonld(data, "https://tixr.com/x")
        assert show is not None
        assert len(show.tickets) == 1
        assert show.tickets[0].sold_out is False
        # Placeholder ticket carries no price signal; unknown is None, not 0.
        assert show.tickets[0].price is None
        assert any("placeholder" in w.lower() or "no offers" in w.lower() for w in warnings)

    def test_offer_price_none_when_invalid(self, monkeypatch):
        client = self._client(monkeypatch)
        data = self._valid_data()
        data["offers"] = [{"price": "free", "availability": "", "url": "https://tixr.com/x"}]
        show = client._create_show_from_jsonld(data, "https://tixr.com/x")
        assert show is not None
        # Unparseable offer price is unknown, not free.
        assert show.tickets[0].price is None

    def test_unparseable_start_date_returns_none(self, monkeypatch):
        client = self._client(monkeypatch)
        data = self._valid_data()
        data["startDate"] = "not-a-date"
        result = client._create_show_from_jsonld(data, "https://tixr.com/x")
        assert result is None

    def test_html_entities_decoded_in_all_string_fields(self, monkeypatch):
        client = self._client(monkeypatch)
        data = self._valid_data()
        data["name"] = "Comedy &amp; Friends"
        data["description"] = "A night of laughs &amp; fun with Dave&#39;s crew"
        data["performer"] = [{"@type": "Person", "name": "Dave &amp; Friends"}]
        data["offers"] = [
            {
                "price": "20.00",
                "availability": "https://schema.org/InStock",
                "url": "https://tixr.com/x",
                "name": "GA &amp; VIP Combo",
            }
        ]
        show = client._create_show_from_jsonld(data, "https://tixr.com/x")
        assert show is not None
        assert show.name == "Comedy & Friends"
        assert show.description == "A night of laughs & fun with Dave's crew"
        assert show.lineup[0].name == "Dave & Friends"
        assert show.tickets[0].type == "GA & VIP Combo"

    def test_show_page_url_falls_back_to_page_url(self, monkeypatch):
        client = self._client(monkeypatch)
        data = self._valid_data()
        del data["url"]
        page_url = "https://tixr.com/fallback"
        show = client._create_show_from_jsonld(data, page_url)
        assert show is not None
        assert show.show_page_url == page_url


# ---------------------------------------------------------------------------
# _build_tickets_from_tiers / _extract_fallback_tickets — unknown-price path
# ---------------------------------------------------------------------------

class TestBuildTicketsFromTiers:
    """Pin the null-vs-zero contract for tier-derived tickets (TASK-2405)."""

    def test_tier_missing_price_emits_none(self):
        tiers = [{"name": "GA", "active": True}]
        tickets = TixrClient._build_tickets_from_tiers(tiers, "https://tixr.com/x")
        assert len(tickets) == 1
        assert tickets[0].price is None

    def test_tier_unparseable_price_emits_none(self):
        tiers = [{"name": "GA", "active": True, "price": "free"}]
        tickets = TixrClient._build_tickets_from_tiers(tiers, "https://tixr.com/x")
        assert len(tickets) == 1
        assert tickets[0].price is None

    def test_tier_numeric_price_preserved(self):
        tiers = [{"name": "GA", "active": True, "price": "25"}]
        tickets = TixrClient._build_tickets_from_tiers(tiers, "https://tixr.com/x")
        assert tickets[0].price == 25.0

    def test_tier_explicit_zero_price_preserved_as_free(self):
        tiers = [{"name": "GA", "active": True, "price": 0}]
        tickets = TixrClient._build_tickets_from_tiers(tiers, "https://tixr.com/x")
        # An explicit 0 from Tixr means proven-free; do not promote to None.
        assert tickets[0].price == 0


class TestExtractFallbackTickets:
    """Pin the null-vs-zero contract for the no-sales fallback path."""

    def test_has_tickets_with_no_sales_emits_none_price(self):
        data = {"hasTickets": True, "ticketUrl": "https://tixr.com/x"}
        tickets = TixrClient._extract_fallback_tickets(data, "https://tixr.com/y")
        assert len(tickets) == 1
        assert tickets[0].price is None
        assert tickets[0].purchase_url == "https://tixr.com/x"

    def test_no_tickets_returns_empty(self):
        data = {"hasTickets": False}
        tickets = TixrClient._extract_fallback_tickets(data, "https://tixr.com/y")
        assert tickets == []


# ---------------------------------------------------------------------------
# get_event_detail — event_id extraction
# ---------------------------------------------------------------------------

class TestGetEventDetailEventId:
    """Tests that get_event_detail populates TixrEvent.event_id correctly."""

    def _client(self, monkeypatch) -> TixrClient:
        monkeypatch.setattr(BaseApiClient, "__init__", lambda self, club, proxy_pool=None: (
            setattr(self, "club", club) or setattr(self, "headers", {})
        ))
        return TixrClient(_club())

    def _valid_jsonld(self) -> dict:
        return {
            "@type": "Event",
            "name": "Comedy Night",
            "startDate": "2026-05-01T20:00:00-04:00",
            "url": "https://tixr.com/groups/comedy/events/test-123",
            "performer": [{"@type": "Person", "name": "Alice Smith"}],
            "offers": [
                {
                    "price": "25.00",
                    "availability": "https://schema.org/InStock",
                    "url": "https://tixr.com/groups/comedy/events/test-123",
                }
            ],
            "location": {"@type": "Place", "name": "Test Club", "address": "123 Main St"},
        }

    @pytest.mark.asyncio
    async def test_numeric_suffix_url_extracts_numeric_id(self, monkeypatch):
        client = self._client(monkeypatch)
        url = "https://tixr.com/groups/comedy/events/show-name-179551"

        async def fake_fetch(u):
            return "<html/>"

        monkeypatch.setattr(client, "_fetch_tixr_page", fake_fetch)
        monkeypatch.setattr(client, "_extract_jsonld_event", lambda html: self._valid_jsonld())
        monkeypatch.setattr(client, "_create_show_from_jsonld", lambda data, u: object())

        from laughtrack.core.entities.event.tixr import TixrEvent
        captured = {}

        def fake_from_show(show, source_url, event_id):
            captured["event_id"] = event_id
            return object()

        monkeypatch.setattr(TixrEvent, "from_tixr_show", staticmethod(fake_from_show))
        await client.get_event_detail_from_url(url)
        assert captured["event_id"] == "179551"

    @pytest.mark.asyncio
    async def test_slug_only_url_uses_slug_as_event_id(self, monkeypatch):
        client = self._client(monkeypatch)
        url = "https://tixr.com/groups/comedy/events/standup-saturday"

        async def fake_fetch(u):
            return "<html/>"

        monkeypatch.setattr(client, "_fetch_tixr_page", fake_fetch)
        monkeypatch.setattr(client, "_extract_jsonld_event", lambda html: self._valid_jsonld())
        monkeypatch.setattr(client, "_create_show_from_jsonld", lambda data, u: object())

        from laughtrack.core.entities.event.tixr import TixrEvent
        captured = {}

        def fake_from_show(show, source_url, event_id):
            captured["event_id"] = event_id
            return object()

        monkeypatch.setattr(TixrEvent, "from_tixr_show", staticmethod(fake_from_show))
        await client.get_event_detail_from_url(url)
        assert captured["event_id"] == "standup-saturday"
        assert captured["event_id"] != ""

    @pytest.mark.asyncio
    async def test_event_id_never_empty_for_valid_events_path(self, monkeypatch):
        """event_id must be non-empty for any URL containing /events/."""
        client = self._client(monkeypatch)

        async def fake_fetch(u):
            return "<html/>"

        monkeypatch.setattr(client, "_fetch_tixr_page", fake_fetch)
        monkeypatch.setattr(client, "_extract_jsonld_event", lambda html: self._valid_jsonld())
        monkeypatch.setattr(client, "_create_show_from_jsonld", lambda data, u: object())

        from laughtrack.core.entities.event.tixr import TixrEvent
        captured = {}

        def fake_from_show(show, source_url, event_id):
            captured["event_id"] = event_id
            return object()

        monkeypatch.setattr(TixrEvent, "from_tixr_show", staticmethod(fake_from_show))

        for url in [
            "https://tixr.com/groups/comedy/events/standup-saturday",
            "https://tixr.com/groups/comedy/events/show-179551",
            "https://tixr.com/groups/comedy/events/179551",
        ]:
            await client.get_event_detail_from_url(url)
            assert captured["event_id"] != "", f"event_id was empty for {url}"


class TestFetchGroupEvents:
    """Tests for the opt-in Tixr group-events API fallback."""

    def _client(self, monkeypatch) -> TixrClient:
        monkeypatch.setattr(BaseApiClient, "__init__", lambda self, club, proxy_pool=None: (
            setattr(self, "club", club) or setattr(self, "headers", {})
            or setattr(self, "http_client", HttpClient())
        ))
        return TixrClient(_club())

    def _api_event(self, event_id: str = "189028") -> dict:
        return {
            "id": event_id,
            "name": "Comedy Night",
            "formattedISOStartDate": "2026-05-12T20:00:00-07:00",
            "url": f"https://www.tixr.com/groups/laughfactorycovina/events/comedy-night-{event_id}",
            "description": "A showcase",
            "group": {"subdomain": "laughfactorycovina"},
            "sales": [
                {
                    "tiers": [
                        {"name": "General Admission", "price": "25.00", "active": True}
                    ]
                }
            ],
        }

    def test_extract_group_event_records_supports_known_envelopes(self):
        event = {"id": 1}
        assert TixrClient._extract_group_event_records([event]) == [event]
        assert TixrClient._extract_group_event_records({"events": [event]}) == [event]
        assert TixrClient._extract_group_event_records({"data": {"items": [event]}}) == [event]
        assert TixrClient._extract_group_event_records({"data": {"results": [event]}}) == [event]

    @pytest.mark.asyncio
    async def test_fetch_group_events_builds_tixr_events(self, monkeypatch):
        client = self._client(monkeypatch)
        calls = []

        async def fake_direct_fetch(url, logger_context):
            calls.append((url, logger_context))
            return {"events": [self._api_event()]}

        monkeypatch.setattr(client, "_fetch_group_events_json_direct", fake_direct_fetch)

        events = await client.fetch_group_events("1613", max_pages=1)

        assert len(events) == 1
        assert events[0].event_id == "189028"
        assert events[0].title == "Comedy Night"
        assert calls == [
            (
                "https://www.tixr.com/api/groups/1613/events?page=1",
                {"group_id": "1613", "page": 1},
            )
        ]
        assert client.key == "tixr"

    @pytest.mark.asyncio
    async def test_fetch_group_events_reads_until_first_empty_page(self, monkeypatch):
        """Covina's group-events API returns additional events on page 2."""
        client = self._client(monkeypatch)
        calls = []

        async def fake_direct_fetch(url, logger_context):
            calls.append((url, logger_context))
            if url.endswith("page=1"):
                return {"events": [self._api_event("189028")]}
            if url.endswith("page=2"):
                return {"events": [self._api_event("190370")]}
            return []

        monkeypatch.setattr(client, "_fetch_group_events_json_direct", fake_direct_fetch)

        events = await client.fetch_group_events("1613")

        assert [event.event_id for event in events] == ["189028", "190370"]
        assert [event.show.tickets[0].price for event in events] == [25.0, 25.0]
        assert calls == [
            (
                "https://www.tixr.com/api/groups/1613/events?page=1",
                {"group_id": "1613", "page": 1},
            ),
            (
                "https://www.tixr.com/api/groups/1613/events?page=2",
                {"group_id": "1613", "page": 2},
            ),
            (
                "https://www.tixr.com/api/groups/1613/events?page=3",
                {"group_id": "1613", "page": 3},
            ),
        ]

    @pytest.mark.asyncio
    async def test_fetch_group_events_tries_direct_before_headerless_proxy(self, monkeypatch):
        client = self._client(monkeypatch)
        calls = []

        async def fake_direct_fetch(url, logger_context):
            calls.append("direct")
            return None

        async def fake_proxy_fetch(url, logger_context):
            calls.append("proxy")
            return {"events": [self._api_event()]}

        monkeypatch.setattr(client, "_fetch_group_events_json_direct", fake_direct_fetch)
        monkeypatch.setattr(client, "_fetch_group_events_json_proxy", fake_proxy_fetch)

        events = await client.fetch_group_events("1613", max_pages=1)

        assert len(events) == 1
        assert calls == ["direct", "proxy"]
        assert client.key == "tixr"

    @pytest.mark.asyncio
    async def test_fetch_group_events_proxy_keeps_headerless_fingerprint(self, monkeypatch):
        client = self._client(monkeypatch)
        calls = []

        class Session(_FakeSession):
            async def get(self, url, headers=None, proxies=None, **kwargs):
                raise AssertionError("fetch_json should be patched")

        async def fake_fetch_json(**kwargs):
            calls.append(kwargs)
            return {"events": [self._api_event()]}

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")
        monkeypatch.setattr(client.http_client, "fetch_json", fake_fetch_json)
        monkeypatch.setattr(tixr_module.HttpClient, "resolve_proxy_url", lambda key: "http://proxy")

        data = await client._fetch_group_events_json_proxy(
            "https://www.tixr.com/api/groups/1613/events?page=1",
            {"group_id": "1613"},
        )

        assert data == {"events": [self._api_event()]}
        assert calls[0]["headers"] is None
        assert calls[0]["proxy_url"] == "http://proxy"
        assert calls[0]["scraper_key"] is None

    @pytest.mark.asyncio
    async def test_fetch_group_events_proxy_returns_none_when_tixr_proxy_not_configured(self, monkeypatch):
        client = self._client(monkeypatch)
        monkeypatch.setattr(tixr_module.HttpClient, "resolve_proxy_url", lambda key: None)

        data = await client._fetch_group_events_json_proxy(
            "https://www.tixr.com/api/groups/1613/events?page=1",
            {"group_id": "1613"},
        )

        assert data is None

    @pytest.mark.asyncio
    async def test_fetch_group_events_deduplicates_and_skips_unparseable(self, monkeypatch):
        client = self._client(monkeypatch)
        valid = self._api_event("189028")
        duplicate = self._api_event("189028")
        invalid = {"id": "bad", "name": "Missing Date"}

        async def fake_direct_fetch(url, logger_context):
            return {"events": [valid, duplicate, invalid]}

        monkeypatch.setattr(client, "_fetch_group_events_json_direct", fake_direct_fetch)

        events = await client.fetch_group_events("1613")

        assert [event.event_id for event in events] == ["189028"]

    @pytest.mark.asyncio
    async def test_fetch_group_events_splits_multi_performance_bundle_by_ticket_time(
        self, monkeypatch
    ):
        """A Tixr event whose tiers cover multiple performance times is split
        into one TixrEvent per occurrence, each carrying only its own tiers.

        Models the live Laugh Factory Covina event 187607 ("JERRY GARCIA
        (May 22-23)") whose API response carries ``formattedISOStartDate``
        in UTC (Tixr emits UTC for the live group-events feed even for
        Pacific venues) and ``venue.timezone="America/Los_Angeles"``. The
        splitter must do its weekday + clock-time math in the venue's local
        timezone so "Friday 7:30pm" lands on Friday-night PT, not Friday
        morning PT.
        """
        client = self._client(monkeypatch)
        # 2026-05-23T02:30:00Z is Friday 2026-05-22 19:30 PT (-07:00 DST).
        bundled_event = {
            "id": "187607",
            "name": "JERRY GARCIA (May 22-23)",
            "formattedISOStartDate": "2026-05-23T02:30:00Z",
            "url": (
                "https://www.tixr.com/groups/laughfactorycovina/events/"
                "jerry-garcia-may-22-23--187607"
            ),
            "group": {"subdomain": "laughfactorycovina"},
            "venue": {"timezone": "America/Los_Angeles"},
            "sales": [
                {
                    "tiers": [
                        {"name": "General Admission - Friday 7:30pm", "price": "31.62", "active": True},
                        {"name": "VIP Seating - Friday 7:30pm", "price": "42.32", "active": True},
                        {"name": "General Admission - Friday 9:30pm", "price": "31.62", "active": True},
                        {"name": "Booth Seats - Saturday 7pm", "price": "53.02", "active": True},
                        {"name": "General Admission - Saturday 9:30pm", "price": "31.62", "active": True},
                    ]
                }
            ],
        }

        async def fake_direct_fetch(url, logger_context):
            return {"events": [bundled_event]}

        monkeypatch.setattr(client, "_fetch_group_events_json_direct", fake_direct_fetch)

        events = await client.fetch_group_events("1613")

        assert len(events) == 4
        assert {event.event_id for event in events} == {"187607"}

        # Compare in Pacific local time — that's the wall clock named on each tier.
        la = pytz.timezone("America/Los_Angeles")
        by_local_dt = {}
        for event in events:
            local = event.date_time.astimezone(la)
            by_local_dt[(local.weekday(), local.hour, local.minute)] = event

        # Friday is weekday 4, Saturday is weekday 5.
        fri_730 = by_local_dt[(4, 19, 30)]
        fri_930 = by_local_dt[(4, 21, 30)]
        sat_7 = by_local_dt[(5, 19, 0)]
        sat_930 = by_local_dt[(5, 21, 30)]

        # Each split lands on the matching calendar date in PT (Fri 5/22 / Sat 5/23).
        for ev, expected_day in ((fri_730, 22), (fri_930, 22), (sat_7, 23), (sat_930, 23)):
            local = ev.date_time.astimezone(la)
            assert (local.year, local.month, local.day) == (2026, 5, expected_day)

        # Post-split tier names drop the redundant " - <weekday> <clock>" suffix
        # since each performance is now its own Show with the time on the Show
        # itself. The three "General Admission - ..." source tiers collapse to
        # the bare "General Admission" base name across distinct performances —
        # the per-show Ticket.type set must stay collision-free (the model has
        # @@unique([showId, type])).
        assert [t.type for t in fri_730.show.tickets] == [
            "General Admission",
            "VIP Seating",
        ]
        assert [t.type for t in fri_930.show.tickets] == ["General Admission"]
        assert [t.type for t in sat_7.show.tickets] == ["Booth Seats"]
        assert [t.type for t in sat_930.show.tickets] == ["General Admission"]

        # All three "General Admission - ..." source tiers share a base name
        # but land on different shows — the splitter must never produce two
        # tiers with the same base name on a single show.
        for event in events:
            tier_types = [t.type for t in event.show.tickets]
            assert len(tier_types) == len(set(tier_types))

        # All splits keep the bundled event's source URL so the user lands on the same purchase page.
        assert {event.show.show_page_url for event in events} == {bundled_event["url"]}

    @pytest.mark.asyncio
    async def test_fetch_group_events_preserves_single_performance_ticket_tiers(
        self, monkeypatch
    ):
        """Single-performance events with tiers that lack a weekday+time
        suffix still return one Show carrying every tier — the splitter
        must not false-positive on plain tier names."""
        client = self._client(monkeypatch)
        plain_event = {
            "id": "189028",
            "name": "Comedy Night",
            "formattedISOStartDate": "2026-05-12T20:00:00-07:00",
            "url": (
                "https://www.tixr.com/groups/laughfactorycovina/events/comedy-night-189028"
            ),
            "group": {"subdomain": "laughfactorycovina"},
            "sales": [
                {
                    "tiers": [
                        {"name": "General Admission", "price": "25.00", "active": True},
                        {"name": "VIP Seating", "price": "45.00", "active": True},
                        {"name": "Booth Seats", "price": "55.00", "active": False},
                    ]
                }
            ],
        }

        async def fake_direct_fetch(url, logger_context):
            return {"events": [plain_event]}

        monkeypatch.setattr(client, "_fetch_group_events_json_direct", fake_direct_fetch)

        events = await client.fetch_group_events("1613")

        assert len(events) == 1
        event = events[0]
        assert event.event_id == "189028"
        assert (event.date_time.hour, event.date_time.minute) == (20, 0)
        assert [t.type for t in event.show.tickets] == [
            "General Admission",
            "VIP Seating",
            "Booth Seats",
        ]
        assert [t.sold_out for t in event.show.tickets] == [False, False, True]

    def test_localize_for_weekday_math_returns_unchanged_when_no_timezone(self):
        """A missing venue.timezone returns base_date unchanged.

        The fallback path matters because a regression to the original
        UTC-vs-local bug shows up only when the venue timezone is missing
        or unresolvable — the live-API splitter test always passes a valid
        timezone string.
        """
        from datetime import datetime
        base = datetime(2026, 5, 23, 2, 30, tzinfo=pytz.UTC)
        assert TixrClient._localize_for_weekday_math(base, None) is base
        assert TixrClient._localize_for_weekday_math(base, "") is base

    def test_localize_for_weekday_math_returns_unchanged_when_timezone_invalid(self):
        """An unresolvable timezone string returns base_date unchanged."""
        from datetime import datetime
        base = datetime(2026, 5, 23, 2, 30, tzinfo=pytz.UTC)
        assert TixrClient._localize_for_weekday_math(base, "Not/A_Real_Zone") is base

    def test_localize_for_weekday_math_converts_to_venue_tz(self):
        """A valid venue timezone returns the same instant in venue local time.

        Anchors the contract the splitter relies on: a UTC ``base_date``
        landing past midnight UTC must report the *previous* PT calendar
        day so the tier "Friday 7:30pm" anchors on Friday-PT, not the
        UTC Saturday that the same instant falls on.
        """
        from datetime import datetime
        base = datetime(2026, 5, 23, 2, 30, tzinfo=pytz.UTC)
        local = TixrClient._localize_for_weekday_math(base, "America/Los_Angeles")
        assert (local.year, local.month, local.day) == (2026, 5, 22)
        assert (local.hour, local.minute) == (19, 30)
        assert local.weekday() == 4  # Friday

    def test_strip_performance_time_suffix_strips_matching_suffix(self):
        """A tier name whose suffix matches the show's performance time is
        stripped down to its base name."""
        from datetime import datetime
        # Friday 2026-05-22 19:30 PT — weekday=4, hour=19, minute=30.
        perf = datetime(2026, 5, 22, 19, 30)
        assert (
            TixrClient._strip_performance_time_suffix(
                "Golden Circle - Friday 7:30pm", perf
            )
            == "Golden Circle"
        )
        assert (
            TixrClient._strip_performance_time_suffix(
                "General Admission - Fri 7:30pm", perf
            )
            == "General Admission"
        )

    def test_strip_performance_time_suffix_preserves_when_no_suffix(self):
        """A tier name without a recognizable suffix is returned unchanged."""
        from datetime import datetime
        perf = datetime(2026, 5, 22, 19, 30)
        assert (
            TixrClient._strip_performance_time_suffix("General Admission", perf)
            == "General Admission"
        )
        assert (
            TixrClient._strip_performance_time_suffix("VIP - Premium Seating", perf)
            == "VIP - Premium Seating"
        )

    def test_strip_performance_time_suffix_preserves_when_suffix_mismatches(self):
        """Defensive guard: a tier carrying a parseable suffix that does NOT
        match the host show's (weekday, hour, minute) keeps its original name.

        This is what protects unexpected tier shapes — e.g. a tier that ends
        up in the base-date catch-all bucket but happens to carry a different
        weekday/time suffix — from being silently mangled.
        """
        from datetime import datetime
        # Performance is Friday 7:30pm PT.
        perf = datetime(2026, 5, 22, 19, 30)

        # Wrong weekday — Saturday suffix vs Friday show.
        assert (
            TixrClient._strip_performance_time_suffix(
                "Golden Circle - Saturday 7:30pm", perf
            )
            == "Golden Circle - Saturday 7:30pm"
        )
        # Wrong hour — 9:30pm suffix vs 7:30pm show.
        assert (
            TixrClient._strip_performance_time_suffix(
                "Golden Circle - Friday 9:30pm", perf
            )
            == "Golden Circle - Friday 9:30pm"
        )
        # Wrong minute — 7:00pm suffix vs 7:30pm show.
        assert (
            TixrClient._strip_performance_time_suffix(
                "Golden Circle - Friday 7pm", perf
            )
            == "Golden Circle - Friday 7pm"
        )
