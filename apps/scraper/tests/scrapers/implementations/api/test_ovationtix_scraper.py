"""Tests for the generic OvationTix platform scraper."""

from __future__ import annotations

from typing import Dict

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.ovationtix.scraper import OvationTixScraper

CLIENT_ID = "36697"
CAL_URL = f"https://web.ovationtix.com/trs/cal/{CLIENT_ID}"


def _club(metadata: dict | None = None) -> Club:
    source = ScrapingSource(
        id=9001,
        club_id=999,
        platform="ovationtix",
        scraper_key="ovationtix",
        source_url=CAL_URL,
        ovationtix_id=CLIENT_ID,
        priority=0,
        enabled=True,
        metadata=metadata or {},
    )
    return Club(
        id=999,
        name="The Colonial Theatre",
        address="95 Main St",
        website="https://thecolonial.org",
        popularity=0,
        zip_code="03431",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        city="Keene",
        state="NH",
        scraping_sources=[source],
        active_scraping_source=source,
    )


def _production_payload(
    *,
    production_name: str,
    performance_id: str,
    description: str = "",
) -> Dict:
    return {
        "productionName": production_name,
        "description": description,
        "performances": [
            {
                "id": performance_id,
                "startDate": "2099-07-22 20:00",
                "ticketsAvailable": True,
                "availableToPurchaseOnWeb": True,
            }
        ],
    }


class _FakeResponse:
    def __init__(self, payload: Dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, payloads_by_production: Dict[str, Dict]):
        self._payloads = payloads_by_production
        self.calls = []

    async def get(self, url, headers=None):
        self.calls.append(url)
        for production_id, payload in self._payloads.items():
            if f"Production({production_id})" in url:
                return _FakeResponse(payload)
        if "Performance(" in url:
            return _FakeResponse({"sections": []})
        return _FakeResponse({}, status_code=404)


class _FakeBatchScraper:
    async def process_batch(self, items, processor, description=""):
        for item in items:
            await processor(item)


async def _no_series(self, discovery_url, client_id):
    return []


async def _run_scraper(
    monkeypatch, *, metadata: dict | None = None, payloads: dict | None = None
):
    payloads = payloads if payloads is not None else {
        "100": _production_payload(
            production_name="Patton Oswalt: Effervescent",
            performance_id="1001",
            description="A night of stand-up comedy.",
        ),
        "200": _production_payload(
            production_name="Margaret Cho",
            performance_id="2001",
            description="Stand-up comedian Margaret Cho live.",
        ),
        "300": _production_payload(
            production_name="Mavis Staples",
            performance_id="3001",
            description="Legendary soul and gospel concert.",
        ),
        "400": _production_payload(
            production_name="Nosferatu",
            performance_id="4001",
            description="Silent film screening with live score.",
        ),
        "500": _production_payload(
            production_name="New England Philharmonic Chamber Ensemble",
            performance_id="5001",
            description="A silent-film program with physical comedy and live chamber music.",
        ),
    }
    html = "".join(
        f'<a href="https://ci.ovationtix.com/{CLIENT_ID}/production/{production_id}">'
        f"{payload['productionName']}</a>"
        for production_id, payload in payloads.items()
    )

    async def fake_fetch_html(self, url, headers=None):
        assert url == CAL_URL
        return html

    fake_session = _FakeSession(payloads)

    async def fake_get_session(self):
        return fake_session

    monkeypatch.setattr(OvationTixScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(OvationTixScraper, "_fetch_series_production_ids", _no_series)
    monkeypatch.setattr(OvationTixScraper, "get_session", fake_get_session)

    scraper = OvationTixScraper(_club(metadata=metadata))
    scraper.batch_scraper = _FakeBatchScraper()
    page = await scraper.get_data(CAL_URL)
    return page, fake_session


@pytest.mark.asyncio
async def test_scraper_keeps_all_events_without_comedy_filter(monkeypatch):
    page, fake_session = await _run_scraper(monkeypatch)

    assert page is not None
    assert sorted(event.production_name for event in page.event_list) == [
        "Margaret Cho",
        "Mavis Staples",
        "New England Philharmonic Chamber Ensemble",
        "Nosferatu",
        "Patton Oswalt: Effervescent",
    ]
    assert sum("Performance(" in call for call in fake_session.calls) == 5


@pytest.mark.asyncio
async def test_comedy_filter_keeps_only_comedy_events(monkeypatch):
    page, fake_session = await _run_scraper(
        monkeypatch,
        metadata={
            "comedy_filter": True,
            "exclude_title_patterns": ["Philharmonic", "^FILM:"],
        },
    )

    assert page is not None
    assert sorted(event.production_name for event in page.event_list) == [
        "Margaret Cho",
        "Patton Oswalt: Effervescent",
    ]
    assert sum("Performance(" in call for call in fake_session.calls) == 2


@pytest.mark.asyncio
async def test_exclude_patterns_drop_classes_without_comedy_filter(monkeypatch):
    """exclude_title_patterns must apply even when comedy_filter is unset (TASK-3480).

    An all-comedy venue that only wants to drop class/camp/workshop listings
    should be able to set exclude_title_patterns WITHOUT comedy_filter — and a
    real show whose title carries no comedy keyword ("The Lineup", a generic
    showcase name) must survive, instead of being eaten by the is_comedy_event
    keyword gate that comedy_filter would have forced on.
    """
    payloads = {
        "100": _production_payload(
            production_name="Improv 101: Beginner Workshop",
            performance_id="1001",
            description="Eight-week drop-in improv class for adults.",
        ),
        "200": _production_payload(
            production_name="Kids Comedy Camp",
            performance_id="2001",
            description="Summer day camp for young performers.",
        ),
        "300": _production_payload(
            production_name="The Lineup",
            performance_id="3001",
            description="Tonight's rotating cast takes the stage.",
        ),
    }
    page, fake_session = await _run_scraper(
        monkeypatch,
        metadata={"exclude_title_patterns": ["Workshop", "Camp"]},
        payloads=payloads,
    )

    assert page is not None
    # Both class/camp titles dropped by the exclude patterns; the keyword-less
    # real show ("The Lineup") is kept because comedy_filter is off.
    assert sorted(event.production_name for event in page.event_list) == ["The Lineup"]
    assert sum("Performance(" in call for call in fake_session.calls) == 1
