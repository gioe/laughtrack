"""Tests for the World Stage Ciright-API scraper.

Covers the public surface of TASK-2009: the Ciright payload shape, the room
filter, and the end-to-end pipeline that turns the API response into Show
objects keyed on (club, date, room) for The Lounge at World Stage.
"""

from datetime import datetime
from typing import Any, Dict, List

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.world_stage.data import WorldStagePageData
from laughtrack.scrapers.implementations.venues.world_stage.extractor import WorldStageExtractor
from laughtrack.scrapers.implementations.venues.world_stage.scraper import WorldStageScraper

_LOUNGE_ROOM_ID = 3131060
_MAIN_HALL_ROOM_ID = 3131059
_SOURCE_URL = "https://worldstage.live/shows"
_API_URL = "https://www.myciright.com/Ciright/api/worldcafelive/m3203760"


def _club(*, room_ids: List[int] = (_LOUNGE_ROOM_ID,)) -> Club:
    club = Club(
        id=1353,
        name="The Lounge at World Stage",
        address="3025 Walnut St, Philadelphia, PA 19104",
        website="https://worldstage.live",
        popularity=0,
        zip_code="19104",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="world_stage",
        source_url=_SOURCE_URL,
        external_id=None,
        metadata={
            "subscription_id": 8990189,
            "vertical_id": 2851,
            "type_id": 1662515,
            "app_id": 2949,
            "status_id": 1851385,
            "room_ids": list(room_ids),
            "lookahead_days": 90,
            "api_url": _API_URL,
        },
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _ciright_response() -> Dict[str, Any]:
    """Trimmed snapshot of the live 2026-05-07 Ciright payload."""
    return {
        "status": True,
        "message": "ok",
        "data": [
            {
                "childEventId": 3428950,
                "eventId": 3428949,
                "eventName": "Unplugged Series: R&B Dinner Party 1",
                "roomId": _LOUNGE_ROOM_ID,
                "room": "The Lounge",
                "time": "03:00 PM - 11:00 PM",
                "startDate": "05/28/2026",
                "endDate": "05/28/2026",
                "status": "Confirmed",
            },
            {
                "childEventId": 3428970,
                "eventId": 3428970,
                "eventName": "Clayton English Comedy Show",
                "roomId": _LOUNGE_ROOM_ID,
                "room": "The Lounge",
                "time": "03:00 PM - 11:00 PM",
                "startDate": "05/16/2026",
                "endDate": "05/16/2026",
                "status": "Confirmed",
            },
            {
                "childEventId": 3429001,
                "eventId": 3429001,
                "eventName": "Lets Keep It 100 Podcast",
                "roomId": _MAIN_HALL_ROOM_ID,
                "room": "Main Hall",
                "time": "05:00 PM - 11:00 PM",
                "startDate": "05/09/2026",
                "endDate": "05/09/2026",
                "status": "Confirmed",
            },
            {
                "childEventId": 3429055,
                "eventId": 3429055,
                "eventName": "Tentative Lounge Booking",
                "roomId": _LOUNGE_ROOM_ID,
                "room": "The Lounge",
                "time": "07:00 PM - 11:00 PM",
                "startDate": "06/01/2026",
                "endDate": "06/01/2026",
                "status": "Pending",
            },
        ],
    }


def test_extractor_filters_to_configured_rooms_and_drops_unconfirmed():
    events = WorldStageExtractor.extract_events(
        _ciright_response(),
        room_ids=[_LOUNGE_ROOM_ID],
        source_url=_SOURCE_URL,
    )

    assert {e.title for e in events} == {
        "Unplugged Series: R&B Dinner Party 1",
        "Clayton English Comedy Show",
    }
    assert all(e.room == "The Lounge" for e in events)
    assert all(e.start_date in {"05/28/2026", "05/16/2026"} for e in events)


def test_extractor_returns_empty_when_status_is_false():
    bad = {"status": False, "message": "Subscription Id is not available", "data": None}

    assert WorldStageExtractor.extract_events(bad, room_ids=[_LOUNGE_ROOM_ID], source_url=_SOURCE_URL) == []


@pytest.mark.asyncio
async def test_get_data_posts_room_neutral_payload_and_emits_filtered_events(monkeypatch):
    scraper = WorldStageScraper(_club())
    captured: Dict[str, Any] = {}

    async def fake_post_json(self, url, data, **kwargs):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = kwargs.get("headers")
        return _ciright_response()

    monkeypatch.setattr(WorldStageScraper, "post_json", fake_post_json)

    result = await scraper.get_data(_API_URL)

    # Ciright's roomIds filter is buggy when populated, so the scraper always
    # sends roomIds=null and filters in-process via the extractor.
    assert captured["url"] == _API_URL
    assert captured["data"]["roomIds"] is None
    assert captured["data"]["statusIds"] == [1851385]
    assert captured["data"]["subscriptionId"] == 8990189
    assert captured["headers"]["x-requested-with"] == "XMLHttpRequest"

    assert isinstance(result, WorldStagePageData)
    assert {e.title for e in result.event_list} == {
        "Unplugged Series: R&B Dinner Party 1",
        "Clayton English Comedy Show",
    }


@pytest.mark.asyncio
async def test_get_data_returns_none_when_room_ids_unset(monkeypatch):
    club = _club()
    club.active_scraping_source.metadata = {}  # type: ignore[union-attr]
    scraper = WorldStageScraper(club)

    async def fake_post_json(self, url, data, **kwargs):  # pragma: no cover — must not run
        raise AssertionError("should not POST when room_ids missing")

    monkeypatch.setattr(WorldStageScraper, "post_json", fake_post_json)

    assert await scraper.get_data(_API_URL) is None


@pytest.mark.asyncio
async def test_get_data_returns_empty_page_data_when_ciright_returns_no_events(monkeypatch):
    scraper = WorldStageScraper(_club())

    async def fake_post_json(self, url, data, **kwargs):
        return {"status": True, "message": "ok", "data": []}

    monkeypatch.setattr(WorldStageScraper, "post_json", fake_post_json)

    result = await scraper.get_data(_API_URL)
    assert isinstance(result, WorldStagePageData)
    assert result.event_list == []


def test_transformation_pipeline_produces_lounge_shows():
    scraper = WorldStageScraper(_club())
    events = WorldStageExtractor.extract_events(
        _ciright_response(),
        room_ids=[_LOUNGE_ROOM_ID],
        source_url=_SOURCE_URL,
    )

    shows = scraper.transformation_pipeline.transform(WorldStagePageData(event_list=events))

    assert len(shows) == 2
    assert all(isinstance(s, Show) for s in shows)
    titles = {s.name for s in shows}
    assert "Clayton English Comedy Show" in titles

    clayton = next(s for s in shows if s.name == "Clayton English Comedy Show")
    assert clayton.room == "The Lounge"
    assert clayton.show_page_url == _SOURCE_URL
    # 03:00 PM in America/New_York for 2026-05-16
    assert clayton.date == datetime(2026, 5, 16, 15, 0, tzinfo=clayton.date.tzinfo)
