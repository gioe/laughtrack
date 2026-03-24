"""
Unit tests for TicketmasterClient.fetch_events.

Ensures 'classificationName' is never included in outgoing API params,
which would silently filter out non-comedy events.
"""

import pytest
from unittest.mock import AsyncMock, patch

from laughtrack.core.clients.ticketmaster import client as tm_module
from laughtrack.core.clients.ticketmaster.client import TicketmasterClient
from laughtrack.core.entities.club.model import Club


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
