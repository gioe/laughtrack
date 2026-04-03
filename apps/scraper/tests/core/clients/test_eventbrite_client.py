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
        def _init(self, club, limiter=None, proxy_pool=None):
            # Minimal attributes used by EventbriteClient methods
            self.club = club
            self.headers = {}
        monkeypatch.setattr(eb_client_module.BaseApiClient, "__init__", _init)
    return _stub


def _club(eventbrite_id: str | None = None, scraping_url: str = "example.com") -> Club:
    return Club(
        id=1,
        name="Test Club",
        address="123 St",
        website="https://example.com",
        scraping_url=scraping_url,
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
async def test_fetch_all_events_falls_back_to_organizer_on_venue_404(monkeypatch, stub_base_init):
    """When venues endpoint returns None (404/error), organizer endpoint is tried."""
    stub_base_init()
    club = _club(eventbrite_id="ORG123")
    c = EventbriteClient(club)

    class Page:
        def __init__(self, events, has_more, continuation=None):
            self.events = events
            self.pagination = type("P", (), {"has_more_items": has_more, "continuation": continuation})()

    async def fake_venue_list(venue_id, continuation=None):
        return None  # 404 / error

    async def fake_organizer_list(organizer_id, continuation=None):
        return Page([{"id": 10}], False)

    def fake_convert(api_event):
        return f"E{api_event['id']}"

    monkeypatch.setattr(c, "fetch_eventbrite_event_list", fake_venue_list)
    monkeypatch.setattr(c, "fetch_organizer_event_list", fake_organizer_list)
    monkeypatch.setattr(eb_client_module.EventbriteEvent, "from_api_model", staticmethod(fake_convert))

    events = await c.fetch_all_events()
    assert events == ["E10"]


@pytest.mark.asyncio
async def test_fetch_all_events_no_fallback_when_venue_is_empty(monkeypatch, stub_base_init):
    """A valid venue with no scheduled shows returns [] without calling organizer endpoint."""
    stub_base_init()
    club = _club(eventbrite_id="VENUE42")
    c = EventbriteClient(club)

    class Page:
        def __init__(self, events, has_more):
            self.events = events
            self.pagination = type("P", (), {"has_more_items": has_more, "continuation": None})()

    async def fake_venue_list(venue_id, continuation=None):
        return Page([], False)  # valid response, just no events

    organizer_called = {"called": False}

    async def fake_organizer_list(organizer_id, continuation=None):
        organizer_called["called"] = True
        return Page([{"id": 99}], False)

    def fake_convert(api_event):
        return f"E{api_event['id']}"

    monkeypatch.setattr(c, "fetch_eventbrite_event_list", fake_venue_list)
    monkeypatch.setattr(c, "fetch_organizer_event_list", fake_organizer_list)
    monkeypatch.setattr(eb_client_module.EventbriteEvent, "from_api_model", staticmethod(fake_convert))

    events = await c.fetch_all_events()
    assert events == []
    assert not organizer_called["called"], "organizer endpoint should not be called for empty-but-valid venue"


@pytest.mark.asyncio
async def test_fetch_all_events_both_endpoints_empty(monkeypatch, stub_base_init):
    """Both venue (404) and organizer (no events) return empty → []."""
    stub_base_init()
    club = _club(eventbrite_id="BAD_ID")
    c = EventbriteClient(club)

    async def fake_venue_list(venue_id, continuation=None):
        return None  # 404

    class Page:
        def __init__(self):
            self.events = []
            self.pagination = type("P", (), {"has_more_items": False, "continuation": None})()

    async def fake_organizer_list(organizer_id, continuation=None):
        return Page()

    monkeypatch.setattr(c, "fetch_eventbrite_event_list", fake_venue_list)
    monkeypatch.setattr(c, "fetch_organizer_event_list", fake_organizer_list)

    events = await c.fetch_all_events()
    assert events == []


@pytest.mark.asyncio
async def test_fetch_organizer_event_list_url_format(monkeypatch, stub_base_init):
    """fetch_organizer_event_list calls /organizers/{id}/events/ with correct params."""
    stub_base_init()
    club = _club(eventbrite_id="ORG999")
    c = EventbriteClient(club)
    c.headers = {}

    called = {}

    async def fake_fetch_json(url, headers, timeout, logger_context):
        called["url"] = url
        called["logger_context"] = logger_context
        return {"ok": True}

    sentinel_resp = object()
    monkeypatch.setattr(c, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(eb_client_module, "EventbriteListEventsResponse", type("R", (), {"from_dict": staticmethod(lambda d: sentinel_resp)})())

    resp = await c.fetch_organizer_event_list(organizer_id="ORG999")

    assert resp is sentinel_resp
    assert called["url"].startswith(f"{c.BASE_URL}/organizers/ORG999/events/?")
    assert "status=live" in called["url"]
    assert "continuation=" not in called["url"]
    assert called["logger_context"] == {"organizer_id": "ORG999"}


@pytest.mark.asyncio
async def test_fetch_organizer_event_list_url_with_continuation(monkeypatch, stub_base_init):
    stub_base_init()
    club = _club(eventbrite_id="ORG999")
    c = EventbriteClient(club)
    c.headers = {}

    called = {}

    async def fake_fetch_json(url, headers, timeout, logger_context):
        called["url"] = url
        return {"ok": True}

    monkeypatch.setattr(c, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(eb_client_module, "EventbriteListEventsResponse", type("R", (), {"from_dict": staticmethod(lambda d: object())})())

    await c.fetch_organizer_event_list(organizer_id="ORG999", continuation="tok1")
    assert "continuation=tok1" in called["url"]


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


@pytest.mark.asyncio
async def test_fetch_all_events_organizer_url_skips_venue_endpoint(monkeypatch, stub_base_init):
    """When scraping_url contains /o/, organizer endpoint is used directly (no venue call)."""
    stub_base_init()
    club = _club(
        eventbrite_id="ORG456",
        scraping_url="https://www.eventbrite.com/o/laugh-factory-hollywood-18525142576",
    )
    c = EventbriteClient(club)

    class Page:
        def __init__(self, events, has_more):
            self.events = events
            self.pagination = type("P", (), {"has_more_items": has_more, "continuation": None})()

    venue_called = {"called": False}

    async def fake_venue_list(venue_id, continuation=None):
        venue_called["called"] = True
        return Page([{"id": 99}], False)

    async def fake_organizer_list(organizer_id, continuation=None):
        return Page([{"id": 7}], False)

    def fake_convert(api_event):
        return f"E{api_event['id']}"

    monkeypatch.setattr(c, "fetch_eventbrite_event_list", fake_venue_list)
    monkeypatch.setattr(c, "fetch_organizer_event_list", fake_organizer_list)
    monkeypatch.setattr(eb_client_module.EventbriteEvent, "from_api_model", staticmethod(fake_convert))

    events = await c.fetch_all_events()
    assert events == ["E7"]
    assert not venue_called["called"], "venue endpoint must not be called for organizer-URL clubs"


@pytest.mark.asyncio
async def test_fetch_all_events_non_organizer_url_tries_venue_first(monkeypatch, stub_base_init):
    """When scraping_url has no /o/, venue endpoint is tried first (backward compat)."""
    stub_base_init()
    club = _club(
        eventbrite_id="VENUE42",
        scraping_url="www.eventbrite.com",
    )
    c = EventbriteClient(club)

    class Page:
        def __init__(self, events, has_more):
            self.events = events
            self.pagination = type("P", (), {"has_more_items": has_more, "continuation": None})()

    venue_called = {"called": False}

    async def fake_venue_list(venue_id, continuation=None):
        venue_called["called"] = True
        return Page([{"id": 5}], False)

    organizer_called = {"called": False}

    async def fake_organizer_list(organizer_id, continuation=None):
        organizer_called["called"] = True
        return Page([{"id": 9}], False)

    def fake_convert(api_event):
        return f"E{api_event['id']}"

    monkeypatch.setattr(c, "fetch_eventbrite_event_list", fake_venue_list)
    monkeypatch.setattr(c, "fetch_organizer_event_list", fake_organizer_list)
    monkeypatch.setattr(eb_client_module.EventbriteEvent, "from_api_model", staticmethod(fake_convert))

    events = await c.fetch_all_events()
    assert events == ["E5"]
    assert venue_called["called"], "venue endpoint must be tried first for non-organizer-URL clubs"
    assert not organizer_called["called"], "organizer endpoint should not be called when venue succeeds"


@pytest.mark.asyncio
async def test_fetch_all_events_organizer_url_organizer_failure_returns_empty(monkeypatch, stub_base_init):
    """When scraping_url contains /o/ but organizer endpoint fails (None), fetch_all_events returns []."""
    stub_base_init()
    club = _club(
        eventbrite_id="ORG456",
        scraping_url="https://www.eventbrite.com/o/some-club-12345",
    )
    c = EventbriteClient(club)

    async def fake_organizer_list(organizer_id, continuation=None):
        return None  # endpoint failure (404 / network error)

    monkeypatch.setattr(c, "fetch_organizer_event_list", fake_organizer_list)

    events = await c.fetch_all_events()
    assert events == []
