import pytest

from laughtrack.core.clients.seatengine import client as se_client_module
from laughtrack.core.clients.seatengine.client import SeatEngineClient
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.entities.club.model import Club


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
        scraping_url="example.com",
        popularity=1,
        zip_code="00000",
        phone_number="000-000-0000",
        visible=True,
        seatengine_id="venue-abc",
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
