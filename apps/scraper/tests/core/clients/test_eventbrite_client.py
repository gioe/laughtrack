import types
import pytest

# Module under test
from laughtrack.core.clients.eventbrite import client as eb_client_module
from laughtrack.core.clients.eventbrite.client import EventbriteClient
from laughtrack.core.entities.club.model import Club


@pytest.fixture(autouse=True)
def silence_logging(monkeypatch):
    monkeypatch.setattr(eb_client_module.Logger, "debug", lambda *a, **k: None)
    return None


@pytest.fixture
def stub_base_init(monkeypatch):
    def _stub():
        def _init(self, club, limiter):
            # Minimal attributes used by EventbriteClient methods
            self.club = club
            self.headers = {}
        monkeypatch.setattr(eb_client_module.BaseApiClient, "__init__", _init)
    return _stub


def _club(eventbrite_id: str | None = None) -> Club:
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
        eventbrite_id=eventbrite_id,
    )


@pytest.mark.asyncio
async def test_init_sets_rate_limit(monkeypatch, stub_base_init):
    # Arrange BaseApiClient.__init__ stub and RateLimiter spy
    stub_base_init()

    class FakeLimiter:
        def __init__(self):
            self.calls = []
        def set_domain_limit(self, domain, rate):
            self.calls.append((domain, rate))

    created = {}
    def fake_rate_limiter():
        rl = FakeLimiter()
        created["limiter"] = rl
        return rl

    monkeypatch.setattr(eb_client_module, "RateLimiter", fake_rate_limiter)

    # Act
    club = _club(eventbrite_id="VENUE123")
    c = EventbriteClient(club)

    # Assert
    assert isinstance(c, EventbriteClient)
    limiter = created["limiter"]
    assert ("eventbrite.com", EventbriteClient.RATE_LIMIT) in limiter.calls


def test_initialize_headers_builds_bearer_json(monkeypatch, stub_base_init):
    # Arrange
    stub_base_init()
    token_holder = {"token": None}

    def fake_get_config(section, key):
        assert section == "api" and key == "eventbrite_token"
        return "TEST_TOKEN"

    def fake_get_headers(fmt, auth_type=None, auth_token=None):
        token_holder["token"] = auth_token
        # Return a simple dict we can assert directly
        return {
            "Authorization": f"Bearer {auth_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    monkeypatch.setattr(eb_client_module.ConfigManager, "get_config", staticmethod(fake_get_config))
    monkeypatch.setattr(eb_client_module.BaseHeaders, "get_headers", staticmethod(fake_get_headers))

    club = _club(eventbrite_id="VENUE123")
    c = EventbriteClient(club)

    # Act
    headers = c._initialize_headers()

    # Assert
    assert token_holder["token"] == "TEST_TOKEN"
    assert headers["Authorization"] == "Bearer TEST_TOKEN"
    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_fetch_event_list_builds_url_without_continuation(monkeypatch, stub_base_init):
    stub_base_init()
    club = _club(eventbrite_id="VENUE_ID")
    c = EventbriteClient(club)
    c.headers = {"X": "Y"}

    # Capture URL used
    called = {}
    async def fake_fetch_json(url, headers, timeout, logger_context):
        called["url"] = url
        called["headers"] = headers
        called["timeout"] = timeout
        called["logger_context"] = logger_context
        return {"ok": True}

    sentinel_resp = object()
    monkeypatch.setattr(c, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(eb_client_module, "EventbriteListEventsResponse", types.SimpleNamespace(from_dict=lambda d: sentinel_resp))

    # Act
    resp = await c.fetch_eventbrite_event_list(venue_id="VENUE_ID")

    # Assert
    assert resp is sentinel_resp
    # Expected query order matches dict insertion order in client.params
    assert called["url"].startswith(f"{c.BASE_URL}/venues/VENUE_ID/events/?")
    assert "status=live" in called["url"]
    assert "order_by=start_asc" in called["url"]
    assert "only_public=true" in called["url"]
    assert "expand=ticket_availability" in called["url"]
    assert "continuation=" not in called["url"]
    assert called["headers"] == {"X": "Y"}
    assert called["timeout"] == c.REQUEST_TIMEOUT
    assert called["logger_context"] == {"venue_id": "VENUE_ID"}


@pytest.mark.asyncio
async def test_fetch_event_list_builds_url_with_continuation(monkeypatch, stub_base_init):
    stub_base_init()
    club = _club(eventbrite_id="VENUE_ID")
    c = EventbriteClient(club)
    c.headers = {"X": "Y"}

    called = {}
    async def fake_fetch_json(url, headers, timeout, logger_context):
        called["url"] = url
        return {"ok": True}

    sentinel_resp = object()
    monkeypatch.setattr(c, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(eb_client_module, "EventbriteListEventsResponse", types.SimpleNamespace(from_dict=lambda d: sentinel_resp))

    resp = await c.fetch_eventbrite_event_list(venue_id="VENUE_ID", continuation="abc")

    assert resp is sentinel_resp
    assert "continuation=abc" in called["url"]


@pytest.mark.asyncio
async def test_fetch_all_events_paginates_and_converts(monkeypatch, stub_base_init):
    stub_base_init()
    club = _club(eventbrite_id="VENUE42")
    c = EventbriteClient(club)

    class Page:
        def __init__(self, events, has_more, continuation=None):
            self.events = events
            self.pagination = types.SimpleNamespace(has_more_items=has_more, continuation=continuation)

    async def fake_list(venue_id, continuation=None):
        if not continuation:
            return Page([{"id": 1}, {"id": 2}], True, "cont1")
        return Page([{"id": 3}], False, None)

    def fake_convert(api_event):
        return f"E{api_event['id']}"

    monkeypatch.setattr(c, "fetch_eventbrite_event_list", fake_list)
    monkeypatch.setattr(eb_client_module.EventbriteEvent, "from_api_model", staticmethod(fake_convert))

    events = await c.fetch_all_events()

    assert events == ["E1", "E2", "E3"]


@pytest.mark.asyncio
async def test_fetch_all_events_returns_empty_if_no_venue_id(monkeypatch, stub_base_init):
    stub_base_init()
    club = _club(eventbrite_id=None)
    c = EventbriteClient(club)
    assert await c.fetch_all_events() == []


@pytest.mark.asyncio
async def test_retrieve_event_success_and_not_found(monkeypatch, stub_base_init):
    stub_base_init()
    club = _club(eventbrite_id="VENUE")
    c = EventbriteClient(club)

    # Success path
    async def fake_fetch_json_ok(url, headers, timeout, logger_context):
        return {"id": "EVT"}

    sentinel = object()
    monkeypatch.setattr(c, "fetch_json", fake_fetch_json_ok)
    monkeypatch.setattr(eb_client_module, "EventbriteSingleEventResponse", types.SimpleNamespace(from_json_dict=lambda d: sentinel))

    got = await c.retrieve_event("EVT")
    assert got is sentinel

    # Not found path
    warnings = {"msg": None}
    async def fake_fetch_json_none(url, headers, timeout, logger_context):
        return None

    def fake_warn(msg):
        warnings["msg"] = msg

    monkeypatch.setattr(c, "fetch_json", fake_fetch_json_none)
    monkeypatch.setattr(c, "log_warning", fake_warn)

    got = await c.retrieve_event("EVT2")
    assert got is None
    assert warnings["msg"] and "EVT2" in warnings["msg"]
