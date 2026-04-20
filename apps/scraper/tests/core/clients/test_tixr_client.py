"""Unit tests for TixrClient._fetch_tixr_page, _extract_jsonld_event, and _create_show_from_jsonld."""

import json
import pytest

from laughtrack.core.clients.tixr import client as tixr_module
from laughtrack.core.clients.tixr.client import TixrClient
from laughtrack.core.clients.tixr.tixr_failure_monitor import FailureType
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.http.client import HttpClient


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
        scraping_url="example.com",
        popularity=1,
        zip_code="10001",
        phone_number="212-000-0000",
        visible=True,
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
        # Status coerced to 403 so TixrFailureMonitor's _classify_failure
        # inspects the body (_classify_failure treats 200 as success and skips).
        assert call["status_code"] == 403
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
        assert show.tickets[0].price == 0
        assert any("placeholder" in w.lower() or "no offers" in w.lower() for w in warnings)

    def test_offer_price_zero_when_invalid(self, monkeypatch):
        client = self._client(monkeypatch)
        data = self._valid_data()
        data["offers"] = [{"price": "free", "availability": "", "url": "https://tixr.com/x"}]
        show = client._create_show_from_jsonld(data, "https://tixr.com/x")
        assert show is not None
        assert show.tickets[0].price == 0.0

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
