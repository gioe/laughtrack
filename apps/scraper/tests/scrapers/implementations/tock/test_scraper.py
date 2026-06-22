"""Tests for the Tock rendered-state scraper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.tock.extractor import extract_tock_events
from laughtrack.scrapers.implementations.tock.scraper import TockScraper

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def club() -> Club:
    _c = Club(
        id=999,
        name="My Buddy's",
        address="4416 N Clark St",
        website="https://www.mybuddyschicago.com/",
        popularity=0,
        zip_code="60640",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        city="Chicago",
        state="IL",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="custom",
        scraper_key="tock",
        source_url="https://www.exploretock.com/mybuddys",
        external_id=None,
        metadata={"comedy_filter": True},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _state_html(experiences: list[dict]) -> str:
    payload = json.dumps(
        {
            "calendar": {
                "offerings": {
                    "experience": experiences,
                },
                "experienceDetail": {"offering": None},
            },
            "navigation": {
                "title": "",
                "onClose": None,
            },
        }
    )
    payload = (
        payload.replace(": null", ":undefined", 1)
        .replace('"onClose": null', '"onClose":function noop() {\\n      // No operation performed.\\n    }')
    )
    return f"<html><script>window.$REDUX_STATE = {payload}</script></html>"


def _experience(
    *,
    event_id: int,
    name: str,
    date: str,
    start_time: str,
    price_cents: int,
    slug: str | None = None,
    description: str = "",
    state: str = "AVAILABLE",
) -> dict:
    return {
        "id": event_id,
        "type": "GA_EVENT",
        "state": state,
        "name": name,
        "slug": slug or name.lower().replace(" ", "-"),
        "description": description,
        "eventDetails": {
            "date": date,
            "startTime": start_time,
            "endTime": "23:00",
            "priceCents": price_cents,
            "location": {
                "name": "My Buddy's",
                "address": "4416 North Clark Street",
                "city": "Chicago",
                "state": "IL",
                "country": "US",
                "zipCode": "60640",
            },
        },
    }


def test_extract_tock_events_decodes_redux_state_and_filters_comedy(club):
    html = _state_html(
        [
            _experience(
                event_id=611697,
                name="Wed Nite Comedy Showdown!",
                date="2026-06-24",
                start_time="21:00",
                price_cents=1000,
                slug="wed-nite-comedy-showdown",
                description="A weekly comedy contest.",
            ),
            _experience(
                event_id=607795,
                name="Drag Bingo hosted by Synthetic",
                date="2026-06-25",
                start_time="18:30",
                price_cents=1000,
            ),
        ]
    )

    events = extract_tock_events(
        html,
        source_url="https://www.exploretock.com/mybuddys",
        timezone=club.timezone,
        comedy_filter=True,
    )

    assert len(events) == 1
    event = events[0]
    assert event.name == "Wed Nite Comedy Showdown!"
    assert event.start_date.isoformat() == "2026-06-24T21:00:00-05:00"
    assert event.url == "https://www.exploretock.com/mybuddys/event/611697/wed-nite-comedy-showdown"
    assert event.location.name == "My Buddy's"
    assert event.offers[0].price == "10.00"
    assert event.offers[0].availability == "InStock"


def test_extract_tock_events_decodes_recurring_prix_fixe_fixture():
    html = (FIXTURES / "batsu_chicago_recurring.html").read_text(encoding="utf-8")

    events = extract_tock_events(
        html,
        source_url="https://www.exploretock.com/batsu-chicago",
        timezone="America/Chicago",
    )

    assert len(events) == 4
    assert {event.name for event in events} == {"BATSU! Chicago"}
    assert [event.start_date.isoformat() for event in events] == [
        "2026-06-26T19:00:00-05:00",
        "2026-06-26T22:00:00-05:00",
        "2026-06-27T19:00:00-05:00",
        "2026-06-27T22:00:00-05:00",
    ]
    assert [offer.name for offer in events[0].offers] == [
        "BATSU! Chicago - VIP Reservation",
        "BATSU! Chicago - Standard Reservation",
    ]
    assert [offer.price for offer in events[0].offers] == ["70.00", "40.00"]
    assert events[0].url == "https://www.exploretock.com/batsu-chicago"
    assert events[0].offers[0].url == (
        "https://www.exploretock.com/batsu-chicago/event/351809/batsu-chicago-vip-reservation"
    )


@pytest.mark.asyncio
async def test_scraper_full_pipeline_produces_comedy_shows(monkeypatch, club):
    scraper = TockScraper(club)
    html = _state_html(
        [
            _experience(
                event_id=527735,
                name="Take A Shot Open Mic Comedy FINALS!!",
                date="2026-06-28",
                start_time="21:00",
                price_cents=1000,
                slug="take-a-shot-open-mic-comedy-finals",
            ),
            _experience(
                event_id=612700,
                name="Trivia Wednesday at My Buddy's!!!",
                date="2026-12-30",
                start_time="19:00",
                price_cents=0,
            ),
        ]
    )

    async def fake_js_fetch(url):
        assert url == "https://www.exploretock.com/mybuddys"
        return html

    monkeypatch.setattr(scraper, "_fetch_html_with_js", fake_js_fetch)

    shows = await scraper.scrape_async()

    assert len(shows) == 1
    assert shows[0].name == "Take A Shot Open Mic Comedy FINALS!!"
    assert shows[0].club_id == club.id
    assert shows[0].show_page_url == "https://www.exploretock.com/mybuddys/event/527735/take-a-shot-open-mic-comedy-finals"
    assert shows[0].tickets[0].price == 10.0
