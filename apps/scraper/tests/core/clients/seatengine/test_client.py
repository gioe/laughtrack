from datetime import datetime, timezone

import pytest

from laughtrack.core.clients import base as base_client_module
from laughtrack.core.clients.seatengine import client as se_client_module
from laughtrack.core.clients.seatengine.client import SeatEngineClient
from laughtrack.core.entities.club.model import Club, ScrapingSource


@pytest.fixture
def stub_base_init(monkeypatch):
    def _init(self, club, proxy_pool=None):
        self.club = club
        self.headers = {}

    monkeypatch.setattr(base_client_module.BaseApiClient, "__init__", _init)


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
        se_client_module.URLUtils,
        "get_formatted_domain",
        lambda url: "example.com",
    )
    monkeypatch.setattr(
        se_client_module.BaseHeaders,
        "get_headers",
        lambda *a, **k: {},
    )
    return SeatEngineClient(_club())


def _make_show_dict(show_id: int = 337633) -> dict:
    return {
        "id": show_id,
        "start_date_time": "2026-04-01T20:00:00-07:00",
        "inventories": [],
        "event": {
            "name": "Test Show",
            "description": "A great show",
            "talents": [],
            "labels": [],
        },
    }


class TestSeatEngineClientUrls:
    def test_invalid_venue_website_falls_back_to_configured_public_base(
        self,
        monkeypatch,
        stub_base_init,
    ):
        client = _make_client(monkeypatch)
        client.venue_website = "#"
        monkeypatch.setattr(
            se_client_module.DateTimeUtils,
            "parse_datetime_with_timezone",
            lambda *a, **k: datetime(2026, 4, 1, 20, 0, 0, tzinfo=timezone.utc),
        )
        monkeypatch.setattr(
            se_client_module.DateTimeUtils,
            "format_utc_iso_date",
            lambda *a, **k: "2026-04-01T20:00:00+00:00",
        )

        show = client.create_show(_make_show_dict(show_id=337633))

        assert show is not None
        assert show.show_page_url == "https://example.com/shows/337633"
        assert len(show.tickets) == 1
        assert show.tickets[0].purchase_url == "https://example.com/shows/337633"
