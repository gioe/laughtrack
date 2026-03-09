import json
import types
import pytest

from laughtrack.core.clients.venuepilot import client as vp_module
from laughtrack.core.clients.venuepilot.client import VenuePilotClient
from laughtrack.core.entities.club.model import Club


@pytest.fixture(autouse=True)
def silence_logging(monkeypatch):
    monkeypatch.setattr(vp_module.VenuePilotClient, "log_warning", lambda *a, **k: None)
    monkeypatch.setattr(vp_module.VenuePilotClient, "log_error", lambda *a, **k: None)


def _club() -> Club:
    return Club(
        id=1,
        name="Test Club",
        address="123 St",
        website="https://example.com",
        scraping_url="https://example.com",
        popularity=1,
        zip_code="00000",
        phone_number="000-000-0000",
        visible=True,
    )


def _make_client(monkeypatch) -> VenuePilotClient:
    def _stub_init(self, club, proxy_pool=None):
        self.club = club
        self.headers = {}

    monkeypatch.setattr(vp_module.VenuePilotClient, "__init__", _stub_init)
    return VenuePilotClient(_club())


def _build_page_text(event_data: dict) -> str:
    payload = {
        "_piniaInitialState": {
            "checkout": {
                "selectedEvent": event_data,
                "tickets": [],
            }
        }
    }
    json_blob = json.dumps(payload)
    return f'<html><script type="application/json">{json_blob}</script></html>'


def test_create_show_extracts_artists_into_lineup(monkeypatch):
    """Artists from selectedEvent are extracted and set as the show lineup."""
    client = _make_client(monkeypatch)

    event_data = {
        "name": "Comedy Night",
        "startTime": "2026-04-01T20:00:00Z",
        "description": "A great show",
        "slug": "comedy-night-2026",
        "artists": [
            {"name": "Alice Smith", "links": []},
            {"name": "Bob Jones", "links": ["https://twitter.com/bobjones"]},
        ],
    }

    page_text = _build_page_text(event_data)
    fake_response = types.SimpleNamespace(
        text=page_text,
        url="https://tickets.venuepilot.com/e/comedy-night-2026",
    )

    monkeypatch.setattr(vp_module.VenuePilotClient, "extract_ticket_data", lambda *a, **k: [])
    monkeypatch.setattr(
        vp_module.DateTimeUtils, "format_utc_iso_date", staticmethod(lambda d: d)
    )

    show = client.create_show(fake_response)

    assert show is not None
    assert show.lineup == ["Alice Smith", "Bob Jones"]


def test_create_show_empty_artists_yields_empty_lineup(monkeypatch):
    """When artists list is empty, lineup is []."""
    client = _make_client(monkeypatch)

    event_data = {
        "name": "Solo Show",
        "startTime": "2026-04-02T20:00:00Z",
        "description": "Just one comedian",
        "slug": "solo-show",
        "artists": [],
    }

    page_text = _build_page_text(event_data)
    fake_response = types.SimpleNamespace(
        text=page_text,
        url="https://tickets.venuepilot.com/e/solo-show",
    )

    monkeypatch.setattr(vp_module.VenuePilotClient, "extract_ticket_data", lambda *a, **k: [])
    monkeypatch.setattr(
        vp_module.DateTimeUtils, "format_utc_iso_date", staticmethod(lambda d: d)
    )

    show = client.create_show(fake_response)

    assert show is not None
    assert show.lineup == []


def test_create_show_missing_artists_key_yields_empty_lineup(monkeypatch):
    """When artists key is absent, lineup defaults to []."""
    client = _make_client(monkeypatch)

    event_data = {
        "name": "Mystery Show",
        "startTime": "2026-04-03T20:00:00Z",
        "description": "TBD",
        "slug": "mystery-show",
    }

    page_text = _build_page_text(event_data)
    fake_response = types.SimpleNamespace(
        text=page_text,
        url="https://tickets.venuepilot.com/e/mystery-show",
    )

    monkeypatch.setattr(vp_module.VenuePilotClient, "extract_ticket_data", lambda *a, **k: [])
    monkeypatch.setattr(
        vp_module.DateTimeUtils, "format_utc_iso_date", staticmethod(lambda d: d)
    )

    show = client.create_show(fake_response)

    assert show is not None
    assert show.lineup == []
