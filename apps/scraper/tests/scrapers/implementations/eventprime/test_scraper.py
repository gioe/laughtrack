"""Tests for the EventPrime get_events scraper.

The smoke test drives the full ``scrape_async`` pipeline against a captured
Flip Flops Comedy Club fixture (dates shifted to far-future / far-past to avoid
time-bomb failures per the scraper test-date convention).
"""

from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.app.registry import discover_scrapers
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.eventprime.scraper import EventPrimeScraper

_FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "get_events.json").read_text())
_ENDPOINT = "https://flipflopscomedy.com/wp-json/eventprime/v1/get_events"
_DRIFTWOOD_URL = "https://flipflopscomedy.com/event/driftwood-open-mic-5/"


def _detail_html(*, start_time: str = "08:00 PM", all_day: str = "0") -> str:
    return (
        "<html><script>"
        f'"em_start_time":"{start_time}",'
        f'"em_all_day":"{all_day}",'
        '"em_end_time":"03:00 AM"'
        "</script></html>"
    )


@pytest.fixture
def club() -> Club:
    _c = Club(
        id=999,
        name="Flip Flops Comedy Club",
        address="",
        website="https://flipflopscomedy.com/",
        popularity=0,
        zip_code="04064",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        city="Old Orchard Beach",
        state="ME",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="custom",
        scraper_key="eventprime",
        source_url=_ENDPOINT,
        external_id=None,
        metadata={},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_registry_resolves_eventprime_key():
    assert discover_scrapers().get("eventprime") is EventPrimeScraper


@pytest.mark.asyncio
async def test_scraper_full_pipeline_produces_upcoming_shows(monkeypatch, club):
    scraper = EventPrimeScraper(club)
    fetched_details = []

    async def fake_fetch_json(url, **kwargs):
        assert url == _ENDPOINT
        return copy.deepcopy(_FIXTURE)

    async def fake_fetch_html(url, **kwargs):
        fetched_details.append((url, kwargs))
        assert url == _DRIFTWOOD_URL
        assert kwargs.get("skip_js_fallback") is True
        return _detail_html(start_time="08:00 PM")

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)

    shows = await scraper.scrape_async()

    # Fixture has 2 far-future events + 1 far-past; past is filtered.
    assert len(shows) == 2
    assert {s.club_id for s in shows} == {club.id}
    shell = next(s for s in shows if s.name.startswith("Shell Yeah"))
    assert shell.date.isoformat() == "2099-07-15T21:30:00-04:00"
    driftwood = next(s for s in shows if s.name == "Driftwood Open Mic")
    assert driftwood.date.isoformat() == "2099-07-02T20:00:00-04:00"
    assert [url for url, _ in fetched_details] == [_DRIFTWOOD_URL]
    # multiple EventPrime tickets become multiple Show tickets
    assert sorted(t.price for t in shell.tickets) == [12.0, 35.0]
    # (URL normalization drops the trailing slash)
    assert (
        shell.show_page_url.rstrip("/") == "https://flipflopscomedy.com/event/shell-yeah-a-night-of-longform-improv-4"
    )
    # the captured past event ("2020-...") is dropped
    assert all(s.date.year >= 2099 for s in shows)


@pytest.mark.asyncio
async def test_no_source_url_yields_no_shows(monkeypatch):
    c = Club(
        id=2,
        name="No Config",
        address="",
        website="",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        city="",
        state="ME",
    )
    c.active_scraping_source = ScrapingSource(
        platform="custom",
        scraper_key="eventprime",
        source_url=None,
        metadata={},
    )
    scraper = EventPrimeScraper(c)

    async def fail_fetch(url, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("fetch_json should not run without a source_url")

    monkeypatch.setattr(scraper, "fetch_json", fail_fetch)
    assert await scraper.scrape_async() == []


@pytest.mark.asyncio
async def test_midnight_enrichment_degrades_to_midnight_on_detail_failure(club):
    scraper = EventPrimeScraper(club)
    payload = copy.deepcopy(_FIXTURE)
    payload["events"] = [payload["events"][1]]

    async def fail_fetch_html(url, **kwargs):
        raise RuntimeError("detail down")

    scraper.fetch_html = fail_fetch_html

    data = await scraper._enrich_midnight_start_times(payload)
    events = data["events"]
    assert events[0]["start_date"] == "2099-07-02T00:00:00-04:00"


@pytest.mark.asyncio
async def test_midnight_enrichment_leaves_all_day_events_at_midnight(club):
    scraper = EventPrimeScraper(club)
    payload = copy.deepcopy(_FIXTURE)
    payload["events"] = [payload["events"][1]]

    async def fake_fetch_html(url, **kwargs):
        return _detail_html(start_time="08:00 PM", all_day="1")

    scraper.fetch_html = fake_fetch_html

    data = await scraper._enrich_midnight_start_times(payload)
    events = data["events"]
    assert events[0]["start_date"] == "2099-07-02T00:00:00-04:00"


@pytest.mark.asyncio
async def test_midnight_enrichment_fetches_are_bounded(club):
    scraper = EventPrimeScraper(club)
    template = copy.deepcopy(_FIXTURE["events"][1])
    payload = {
        "events": [
            {
                **template,
                "id": 2000 + index,
                "title": f"Open Mic {index}",
                "permalink": f"https://flipflopscomedy.com/all-events/?event={2000 + index}",
            }
            for index in range(12)
        ]
    }
    active = 0
    max_active = 0

    async def fake_fetch_html(url, **kwargs):
        nonlocal active, max_active
        assert kwargs.get("skip_js_fallback") is True
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return _detail_html(start_time="08:00 PM")

    scraper.fetch_html = fake_fetch_html

    data = await scraper._enrich_midnight_start_times(payload)
    assert max_active <= 5
    assert {event["start_date"] for event in data["events"]} == {"2099-07-02T20:00:00-04:00"}
