"""
Unit tests for TicketmasterClient.fetch_events.

Ensures 'classificationName' is never included in outgoing API params,
which would silently filter out non-comedy events, and that the client
paginates the Discovery API rather than silently truncating at 200 events.
"""

import pytest
from unittest.mock import AsyncMock, patch

from laughtrack.core.clients.ticketmaster import client as tm_module
from laughtrack.core.clients.ticketmaster.client import TicketmasterClient
from laughtrack.core.entities.club.model import Club


async def _noop_rate_limit() -> None:
    return None


def _club() -> Club:
    return Club(
        id=1,
        name="Test Club",
        address="123 Main St",
        website="https://example.com",
        scraping_url="example.com",
        popularity=1,
        zip_code="10001",
        phone_number="000-000-0000",
        visible=True,
        ticketmaster_id="KovZ917ARvk",
    )


@pytest.fixture
def client(monkeypatch) -> TicketmasterClient:
    """Return a TicketmasterClient with BaseApiClient.__init__ stubbed out."""

    def _stub_init(self, club, proxy_pool=None):
        self.club = club
        self.headers = {}
        self.last_request_time = 0
        self.min_delay = 0.2

    monkeypatch.setattr(tm_module.BaseApiClient, "__init__", _stub_init)
    monkeypatch.setattr(tm_module.ConfigManager, "get_config", lambda *a, **k: "fake-api-key")
    return TicketmasterClient(_club(), api_key="fake-api-key")


@pytest.mark.asyncio
async def test_fetch_events_params_do_not_contain_classification_name(client, monkeypatch):
    """fetch_events must not pass classificationName to the API."""
    captured_params = {}

    def fake_build_url(url, params=None):
        captured_params.update(params or {})
        return "https://fake.ticketmaster.com/events.json"

    monkeypatch.setattr(tm_module.URLUtils, "build_url", fake_build_url)

    async def fake_fetch_json(self, url, headers=None):
        return {}

    monkeypatch.setattr(TicketmasterClient, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(client, "_enforce_rate_limit", lambda: None)

    await client.fetch_events("KovZ917ARvk")

    assert "classificationName" not in captured_params, (
        f"classificationName found in API params: {captured_params}"
    )


@pytest.mark.asyncio
async def test_fetch_events_paginates_until_total_pages(client, monkeypatch):
    """fetch_events must walk page=0..totalPages-1 and aggregate every event."""
    captured_pages: list = []

    def fake_build_url(url, params=None):
        captured_pages.append((params or {}).get("page"))
        return "https://fake.ticketmaster.com/events.json"

    monkeypatch.setattr(tm_module.URLUtils, "build_url", fake_build_url)

    page_responses = [
        {
            "_embedded": {"events": [{"id": f"p0-e{i}"} for i in range(200)]},
            "page": {"size": 200, "totalElements": 450, "totalPages": 3, "number": 0},
        },
        {
            "_embedded": {"events": [{"id": f"p1-e{i}"} for i in range(200)]},
            "page": {"size": 200, "totalElements": 450, "totalPages": 3, "number": 1},
        },
        {
            "_embedded": {"events": [{"id": f"p2-e{i}"} for i in range(50)]},
            "page": {"size": 200, "totalElements": 450, "totalPages": 3, "number": 2},
        },
    ]
    call_index = {"n": 0}

    async def fake_fetch_json(self, url, headers=None):
        idx = call_index["n"]
        call_index["n"] += 1
        return page_responses[idx]

    monkeypatch.setattr(TicketmasterClient, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(client, "_enforce_rate_limit", _noop_rate_limit)

    info_messages: list = []
    monkeypatch.setattr(client, "log_info", lambda m: info_messages.append(m))

    events = await client.fetch_events("KovZ917ARvk")

    assert captured_pages == [0, 1, 2], f"expected three paginated calls, got {captured_pages}"
    assert len(events) == 450
    assert events[0]["id"] == "p0-e0"
    assert events[-1]["id"] == "p2-e49"
    assert any("450" in m and "3 pages" in m for m in info_messages), (
        f"expected totalElements/totalPages log, got {info_messages}"
    )


@pytest.mark.asyncio
async def test_fetch_events_single_page_does_not_log_pagination(client, monkeypatch):
    """Venues that fit on one page must not emit the paginating-summary log."""
    monkeypatch.setattr(
        tm_module.URLUtils, "build_url", lambda url, params=None: "https://fake/"
    )

    async def fake_fetch_json(self, url, headers=None):
        return {
            "_embedded": {"events": [{"id": f"e{i}"} for i in range(42)]},
            "page": {"size": 200, "totalElements": 42, "totalPages": 1, "number": 0},
        }

    monkeypatch.setattr(TicketmasterClient, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(client, "_enforce_rate_limit", _noop_rate_limit)

    info_messages: list = []
    monkeypatch.setattr(client, "log_info", lambda m: info_messages.append(m))

    events = await client.fetch_events("KovZ917ARvk")

    assert len(events) == 42
    assert not any("paginating" in m for m in info_messages), (
        f"single-page response should not emit pagination summary, got {info_messages}"
    )


def test_extract_ticket_data_no_price_ranges_produces_price_none(client):
    """Events with no priceRanges key must produce Ticket(price=None), not price=0.0."""
    event_data = {
        "url": "https://ticketmaster.com/event/123",
        "sales": {"public": {"startDateTime": "2026-04-01T19:00:00Z"}},
        # no 'priceRanges' key
    }
    tickets = client._extract_ticket_data_from_api(event_data)
    assert len(tickets) == 1
    assert tickets[0].price is None, f"Expected price=None, got price={tickets[0].price}"
