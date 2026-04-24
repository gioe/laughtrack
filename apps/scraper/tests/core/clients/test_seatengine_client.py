import pytest

from laughtrack.core.clients.seatengine import client as se_client_module
from laughtrack.core.clients.seatengine.client import SeatEngineClient
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club, ScrapingSource


@pytest.fixture
def stub_base_init(monkeypatch):
    def _init(self, club, proxy_pool=None):
        self.club = club
        self.headers = {}

    monkeypatch.setattr(BaseApiClient, "__init__", _init)


def _club() -> Club:
    return Club(
        id=1,
        name="Test Club",
        address="123 St",
        website="https://example.com",
        popularity=1,
        zip_code="00000",
        phone_number="000-000-0000",
        visible=True,
        scraping_sources=[
            ScrapingSource(
                platform="seatengine",
                scraper_key="seatengine",
                source_url="example.com",
                external_id="venue-abc",
            ),
        ],
    )


def _make_client(monkeypatch) -> SeatEngineClient:
    monkeypatch.setattr(
        se_client_module.URLUtils, "get_formatted_domain", lambda url: "example.com"
    )
    monkeypatch.setattr(
        se_client_module.BaseHeaders,
        "get_headers",
        lambda *a, **k: {},
    )
    return SeatEngineClient(_club())


@pytest.mark.asyncio
async def test_fetch_venue_details_returns_inner_dict(monkeypatch, stub_base_init):
    """fetch_json returns {'data': {...}} → method returns the inner dict."""
    client = _make_client(monkeypatch)
    inner = {"name": "The Stand", "capacity": 200}

    async def fake_fetch_json(url, headers=None):
        return {"data": inner}

    monkeypatch.setattr(client, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(client, "log_info", lambda *a, **k: None)

    result = await client.fetch_venue_details("venue-abc")

    assert result == inner


@pytest.mark.asyncio
async def test_fetch_venue_details_returns_raw_dict_when_no_data_key(monkeypatch, stub_base_init):
    """fetch_json returns raw dict without 'data' key → method returns raw dict."""
    client = _make_client(monkeypatch)
    raw = {"venue_id": "venue-abc", "name": "The Stand"}

    async def fake_fetch_json(url, headers=None):
        return raw

    monkeypatch.setattr(client, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(client, "log_info", lambda *a, **k: None)

    result = await client.fetch_venue_details("venue-abc")

    assert result == raw


@pytest.mark.asyncio
async def test_fetch_venue_details_returns_none_when_fetch_json_returns_none(monkeypatch, stub_base_init):
    """fetch_json returns None → method returns None."""
    client = _make_client(monkeypatch)

    async def fake_fetch_json(url, headers=None):
        return None

    monkeypatch.setattr(client, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(client, "log_info", lambda *a, **k: None)
    monkeypatch.setattr(client, "log_error", lambda *a, **k: None)

    result = await client.fetch_venue_details("venue-abc")

    assert result is None


def _make_show_dict(show_id: int = 337633, sold_out: bool = False, inventories=None) -> dict:
    return {
        "id": show_id,
        "start_date_time": "2026-04-01T20:00:00-07:00",
        "sold_out": sold_out,
        "inventories": inventories or [],
        "event": {
            "name": "Test Show",
            "description": "A great show",
            "talents": [{"name": "Some Comedian"}],
            "labels": [],
        },
    }


@pytest.mark.asyncio
async def test_fetch_events_populates_venue_website(monkeypatch, stub_base_init):
    """fetch_events calls fetch_venue_details and caches venue_website."""
    client = _make_client(monkeypatch)
    shows_payload = {"data": [{"id": 1, "event": {}}]}
    venue_payload = {"data": {"website": "https://comedyzoneclt.seatengine.com"}}

    call_urls = []

    async def fake_fetch_json(url, headers=None):
        call_urls.append(url)
        if "shows" in url and url.endswith("/shows"):
            return shows_payload
        return venue_payload

    monkeypatch.setattr(client, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(client, "log_info", lambda *a, **k: None)

    from laughtrack.core.clients.seatengine.circuit_breaker import SeatEngineCircuitBreaker
    monkeypatch.setattr(SeatEngineCircuitBreaker, "check_open", lambda self: None)
    monkeypatch.setattr(SeatEngineCircuitBreaker, "record_success", lambda self: None)
    monkeypatch.setattr(SeatEngineCircuitBreaker, "record_failure", lambda self: None)

    assert client.venue_website is None
    await client.fetch_events("venue-abc")
    assert client.venue_website == "https://comedyzoneclt.seatengine.com"

    # Second call must NOT re-fetch venue details (only one venue API call per run)
    prev_len = len(call_urls)
    await client.fetch_events("venue-abc")
    venue_calls = [u for u in call_urls[prev_len:] if "shows" not in u.split("/")[-1]]
    assert len(venue_calls) == 0, "venue endpoint should not be re-fetched on second call"


@pytest.mark.asyncio
async def test_fetch_events_venue_website_failure_degrades_gracefully(monkeypatch, stub_base_init):
    """A fetch_venue_details failure inside fetch_events returns shows without setting venue_website."""
    client = _make_client(monkeypatch)
    shows_payload = {"data": [{"id": 1, "event": {}}]}

    async def fake_fetch_json(url, headers=None):
        if url.endswith("/shows"):
            return shows_payload
        raise RuntimeError("venue detail exploded")

    monkeypatch.setattr(client, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(client, "log_info", lambda *a, **k: None)
    monkeypatch.setattr(client, "log_warning", lambda *a, **k: None)
    monkeypatch.setattr(client, "log_error", lambda *a, **k: None)

    from laughtrack.core.clients.seatengine.circuit_breaker import SeatEngineCircuitBreaker
    monkeypatch.setattr(SeatEngineCircuitBreaker, "check_open", lambda self: None)
    monkeypatch.setattr(SeatEngineCircuitBreaker, "record_success", lambda self: None)
    monkeypatch.setattr(SeatEngineCircuitBreaker, "record_failure", lambda self: None)

    shows = await client.fetch_events("venue-abc")
    assert shows == shows_payload["data"]
    assert client.venue_website == ""  # sentinel: fetched, no website (failure path)


_FAKE_DATE = "2026-04-01T20:00:00+00:00"


def _patch_dates(monkeypatch):
    from datetime import datetime, timezone
    monkeypatch.setattr(
        se_client_module.DateTimeUtils,
        "parse_datetime_with_timezone",
        lambda *a, **k: datetime(2026, 4, 1, 20, 0, 0, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        se_client_module.DateTimeUtils,
        "format_utc_iso_date",
        lambda *a, **k: _FAKE_DATE,
    )


def test_create_show_url_uses_venue_website(monkeypatch, stub_base_init):
    """create_show produces a public show URL when venue_website is set."""
    client = _make_client(monkeypatch)
    client.venue_website = "https://comedyzoneclt.seatengine.com"
    _patch_dates(monkeypatch)

    show = client.create_show(_make_show_dict(show_id=337633))

    assert show is not None
    assert show.show_page_url == "https://comedyzoneclt.seatengine.com/shows/337633"
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://comedyzoneclt.seatengine.com/shows/337633"


def test_create_show_url_falls_back_to_api_url_without_venue_website(monkeypatch, stub_base_init):
    """create_show falls back to the API URL when venue_website is not set."""
    client = _make_client(monkeypatch)
    assert client.venue_website is None
    _patch_dates(monkeypatch)

    show = client.create_show(_make_show_dict(show_id=999))

    assert show is not None
    assert "services.seatengine.com/api/v1" in show.show_page_url
    assert "services.seatengine.com/api/v1" in show.tickets[0].purchase_url


def test_create_show_price_from_inventories(monkeypatch, stub_base_init):
    """create_show reads price in cents from inventories[0].price."""
    client = _make_client(monkeypatch)
    client.venue_website = "https://comedyzoneclt.seatengine.com"
    _patch_dates(monkeypatch)

    inventories = [{"price": 2500, "service_charge": 300}]
    show = client.create_show(_make_show_dict(inventories=inventories))

    assert show is not None
    assert show.tickets[0].price == 25.0


def test_create_show_price_defaults_to_zero_without_inventories(monkeypatch, stub_base_init):
    """create_show uses 0.0 price when inventories are absent."""
    client = _make_client(monkeypatch)
    client.venue_website = "https://comedyzoneclt.seatengine.com"
    _patch_dates(monkeypatch)

    show = client.create_show(_make_show_dict(inventories=[]))

    assert show is not None
    assert show.tickets[0].price == 0.0


def test_create_show_sold_out_produces_ticket_with_sold_out_true(monkeypatch, stub_base_init):
    """Sold-out shows produce a single Ticket with sold_out=True and correct purchase_url."""
    client = _make_client(monkeypatch)
    client.venue_website = "https://comedyzoneclt.seatengine.com"
    _patch_dates(monkeypatch)

    show = client.create_show(_make_show_dict(show_id=42, sold_out=True))

    assert show is not None
    assert len(show.tickets) == 1
    ticket = show.tickets[0]
    assert ticket.sold_out is True
    assert ticket.purchase_url == "https://comedyzoneclt.seatengine.com/shows/42"
