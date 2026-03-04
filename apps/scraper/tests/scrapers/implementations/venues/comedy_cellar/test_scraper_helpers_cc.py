import asyncio
import importlib.util
from typing import Any, List, Optional

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_cellar import ComedyCellarEvent
from laughtrack.scrapers.implementations.venues.comedy_cellar.scraper import (
    ComedyCellarScraper,
)
from laughtrack.foundation.models.api.comedy_cellar.models import (
    ComedyCellarLineupAPIResponse,
    ComedyCellarShowsAPIResponse,
    ShowInfoData,
    ShowsInfoData,
    ShowsDataContainer,
    DateAbbreviation,
    ShowAge,
)


def _make_lineup(api_date: str = "2025-01-01", html: str = "<div>ok</div>") -> ComedyCellarLineupAPIResponse:
    payload = {
        "show": {"html": html, "date": "Sunday January 1, 2025"},
        "date": api_date,
        "dates": {api_date: "Sunday January 1, 2025"},
    }
    return ComedyCellarLineupAPIResponse.from_dict(payload)


def _make_shows(api_date: str, shows: List[ShowInfoData]) -> ComedyCellarShowsAPIResponse:
    info = ShowsInfoData(
        date=api_date,
        prettyDate="",
        abbr=DateAbbreviation(day="", month="", date="", pretty=""),
        shows=shows,
        age=ShowAge(seconds=0, time=0),
    )
    return ComedyCellarShowsAPIResponse(message="Ok", data=ShowsDataContainer(showInfo=info))


class _FakeClient:
    def __init__(self, dates: Optional[List[str]] = None, lineup: Any = None, shows: Any = None, raise_on: str | None = None):
        self._dates = dates or ["2025-01-01"]
        self._lineup = lineup or _make_lineup(self._dates[0])
        self._shows = shows or _make_shows(self._dates[0], [ShowInfoData(id=1, time="20:00:00", description="Show", roomId=1, timestamp=1)])
        self._raise_on = raise_on

    async def discover_available_dates(self) -> List[str]:
        if self._raise_on == "discover":
            raise RuntimeError("boom")
        return list(self._dates)

    async def get_lineup_data(self, target: str):
        if self._raise_on == "lineup":
            raise RuntimeError("boom")
        return self._lineup

    async def get_shows_data(self, target: str):
        if self._raise_on == "shows":
            raise RuntimeError("boom")
        return self._shows


def _club() -> Club:
    return Club(
        id=99,
        name="Comedy Cellar",
        address="",
        website="https://www.comedycellar.com",
        scraping_url="https://www.comedycellar.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )


@pytest.mark.asyncio
async def test_collect_scraping_targets_delegates_to_client(monkeypatch):
    s = ComedyCellarScraper(_club())
    fake = _FakeClient(dates=["2025-01-01", "2025-01-02"]) 
    s.api_client = fake  # type: ignore[assignment]

    dates = await s.collect_scraping_targets()
    assert dates == ["2025-01-01", "2025-01-02"]


@pytest.mark.asyncio
async def test_get_data_returns_container_when_extractor_produces_events(monkeypatch):
    s = ComedyCellarScraper(_club())
    fake = _FakeClient(dates=["2025-01-10"]) 
    s.api_client = fake  # type: ignore[assignment]

    captured_args: list[tuple] = []

    def fake_extract_events(date_key, lineup, shows):
        captured_args.append((date_key, lineup, shows))
        # Return a single minimal event
        ev = ComedyCellarEvent(
            show_id=123,
            date_key=str(date_key),
            api_time="20:00:00",
            show_name="A Show",
            description="",
            note=None,
            room_id=2,
            room_name="Village Underground",
            timestamp=1,
            ticket_link="https://www.comedycellar.com/reservations-newyork/?showid=123",
            ticket_data=ShowInfoData(id=123, time="20:00:00", description="A Show", roomId=2, timestamp=1, cover=25),
            html_container="<div>..</div>",
            lineup_names=["Comic A"],
        )
        return [ev]

    from laughtrack.scrapers.implementations.venues.comedy_cellar import extractor as extractor_mod

    monkeypatch.setattr(extractor_mod.ComedyCellarExtractor, "extract_events", staticmethod(fake_extract_events))

    data = await s.get_data("2025-01-10")
    assert data is not None
    assert len(data.event_list) == 1
    # extractor should have received the same objects that client returned
    assert captured_args and captured_args[0][0] == "2025-01-10"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_extractor_returns_empty(monkeypatch):
    s = ComedyCellarScraper(_club())
    s.api_client = _FakeClient(dates=["2025-02-01"])  # type: ignore[assignment]

    def fake_extract_events(date_key, lineup, shows):
        return []

    from laughtrack.scrapers.implementations.venues.comedy_cellar import extractor as extractor_mod

    monkeypatch.setattr(extractor_mod.ComedyCellarExtractor, "extract_events", staticmethod(fake_extract_events))

    data = await s.get_data("2025-02-01")
    assert data is None


@pytest.mark.asyncio
async def test_get_data_handles_client_exception_and_returns_none(monkeypatch):
    s = ComedyCellarScraper(_club())
    # Simulate error on one of the concurrent API calls
    s.api_client = _FakeClient(dates=["2025-03-01"], raise_on="shows")  # type: ignore[assignment]

    # extractor shouldn't be reached, but make it robust if it is
    from laughtrack.scrapers.implementations.venues.comedy_cellar import extractor as extractor_mod
    monkeypatch.setattr(
        extractor_mod.ComedyCellarExtractor,
        "extract_events",
        staticmethod(lambda *_args, **_kwargs: []),
    )

    data = await s.get_data("2025-03-01")
    assert data is None
