"""Unit tests for TixrClient._fetch_tixr_page, _extract_jsonld_event, and _create_show_from_jsonld."""

import json
import pytest

from laughtrack.core.clients.tixr import client as tixr_module
from laughtrack.core.clients.tixr.client import TixrClient
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club


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
    monkeypatch.setattr(BaseApiClient, "__init__", _init)


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
        client = TixrClient(_club())

        class FakeResponse:
            status_code = 200
            text = "<html>hello</html>"

        class Session(_FakeSession):
            async def get(self, url):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result == "<html>hello</html>"

    @pytest.mark.asyncio
    async def test_non_200_returns_none(self, monkeypatch, stub_base_init):
        client = TixrClient(_club())

        class FakeResponse:
            status_code = 403
            text = "Forbidden"

        class Session(_FakeSession):
            async def get(self, url):
                return FakeResponse()

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self, monkeypatch, stub_base_init):
        client = TixrClient(_club())

        class Session(_FakeSession):
            async def get(self, url):
                raise ConnectionError("network down")

        monkeypatch.setattr(tixr_module, "AsyncSession", Session)
        monkeypatch.setattr(client, "_apply_rate_limit", lambda url: _noop())
        monkeypatch.setattr(client, "_get_impersonation_target", lambda url: "chrome124")

        result = await client._fetch_tixr_page("https://tixr.com/groups/x/events/y")
        assert result is None


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

    async def get(self, url):
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
        monkeypatch.setattr(client, "_fetch_tixr_page", lambda u: pytest.approx or None)

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
