"""Tests for the Showpass scraper's optional comedy title filter (TASK-3355).

A Showpass venue calendar lists every event with no category, so a
mixed-programming performing-arts center (stand-up + plays + ballet + concerts)
needs an `include_title_patterns` comedy allowlist. These tests cover the
include/exclude filtering and the default (no filter -> keep all) behavior.
"""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.showpass.scraper import ShowpassScraper
from laughtrack.scrapers.implementations.api.showpass.data import ShowpassPageData

CAL_URL = "https://www.showpass.com/api/public/venues/lauderhill-performing-arts-center-lpac/calendar/"

# Mirrors the live Lauderhill PAC calendar: comedy series mixed with ballet,
# plays, and cultural events. All active; no category field.
RESULTS = [
    {"id": 1, "name": "Lauderhill Live - ALL ROCK. NO FILTER. Comedy", "slug": "lauderhill-live-tony-rock",
     "starts_on": "2099-06-28T00:00:00+00:00", "ends_on": "2099-06-28T02:00:00+00:00",
     "timezone": "America/New_York", "status": "sp_event_active"},
    {"id": 2, "name": "Funny Women of a Certain Age", "slug": "funny-women",
     "starts_on": "2099-07-15T00:00:00+00:00", "ends_on": "2099-07-15T02:00:00+00:00",
     "timezone": "America/New_York", "status": "sp_event_active"},
    {"id": 3, "name": "64th Jamaican Independence Celebration", "slug": "jamaican-independence",
     "starts_on": "2099-08-08T22:00:00+00:00", "ends_on": "2099-08-09T02:00:00+00:00",
     "timezone": "America/New_York", "status": "sp_event_active"},
    {"id": 4, "name": "Georgian National Ballet \"Sukhishvili\"", "slug": "georgian-ballet",
     "starts_on": "2099-10-31T00:00:00+00:00", "ends_on": "2099-10-31T02:00:00+00:00",
     "timezone": "America/New_York", "status": "sp_event_active"},
    # Inactive: must be dropped before the title filter even runs.
    {"id": 5, "name": "Comedy Night (cancelled)", "slug": "cancelled",
     "starts_on": "2099-09-01T00:00:00+00:00", "ends_on": "2099-09-01T02:00:00+00:00",
     "timezone": "America/New_York", "status": "sp_event_cancelled"},
]

COMEDY_PATTERNS = ["lauderhill live", "comedy", "comedian", "stand up", "standup", "funny", "comic"]


def _club(metadata):
    c = Club(id=99200, name='Lauderhill Performing Arts Center', address='3800 NW 11th Pl, Lauderhill, FL 33311',
             website='https://www.lpacfl.com/', popularity=0, zip_code='33311',
             phone_number='', visible=True, timezone='America/New_York')
    c.active_scraping_source = ScrapingSource(
        id=1, club_id=c.id, platform='showpass', scraper_key='showpass', source_url=CAL_URL,
        external_id=None, metadata=metadata)
    c.scraping_sources = [c.active_scraping_source]
    return c


@pytest.mark.asyncio
async def test_comedy_include_filter(monkeypatch):
    scraper = ShowpassScraper(_club({"include_title_patterns": COMEDY_PATTERNS}))

    async def fake_fetch_json(self, url, **kwargs):
        return {"results": RESULTS}

    monkeypatch.setattr(ShowpassScraper, "fetch_json", fake_fetch_json)
    result = await scraper.get_data(CAL_URL)

    assert isinstance(result, ShowpassPageData)
    names = sorted(e.name for e in result.event_list)
    # Only the two comedy events; ballet + cultural dropped; cancelled dropped.
    assert names == ["Funny Women of a Certain Age", "Lauderhill Live - ALL ROCK. NO FILTER. Comedy"]


@pytest.mark.asyncio
async def test_no_filter_keeps_all_active(monkeypatch):
    scraper = ShowpassScraper(_club({}))

    async def fake_fetch_json(self, url, **kwargs):
        return {"results": RESULTS}

    monkeypatch.setattr(ShowpassScraper, "fetch_json", fake_fetch_json)
    result = await scraper.get_data(CAL_URL)

    # All 4 active events kept (the cancelled one is always dropped).
    assert len(result.event_list) == 4


@pytest.mark.asyncio
async def test_exclude_filter_wins(monkeypatch):
    scraper = ShowpassScraper(_club({"exclude_title_patterns": ["ballet", "celebration"]}))

    async def fake_fetch_json(self, url, **kwargs):
        return {"results": RESULTS}

    monkeypatch.setattr(ShowpassScraper, "fetch_json", fake_fetch_json)
    result = await scraper.get_data(CAL_URL)

    names = {e.name for e in result.event_list}
    assert "Georgian National Ballet \"Sukhishvili\"" not in names
    assert "64th Jamaican Independence Celebration" not in names
    assert "Lauderhill Live - ALL ROCK. NO FILTER. Comedy" in names
