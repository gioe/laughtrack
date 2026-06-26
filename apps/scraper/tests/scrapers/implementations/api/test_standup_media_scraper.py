"""Tests for the StandUp Media (Funny Bone / Levity) reservation-API scraper."""

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.standup_media.data import StandUpMediaPageData
from laughtrack.scrapers.implementations.api.standup_media.extractor import (
    StandUpMediaExtractor,
)
from laughtrack.scrapers.implementations.api.standup_media.scraper import StandUpMediaScraper

_LOCATION_ID = "718bd264-309b-4fa0-a6fa-0b93455f88d0"
_DBNAME = "stlouis_prod"
_SOURCE_URL = "https://stlouisfunnybone.com/stlouis/events"
_API_URL = (
    "https://apireservation.standupmedia.com/api/Show/GetAllShows/"
    f"{_LOCATION_ID}/false/{_DBNAME}"
)


def _record(**overrides) -> dict:
    row = {
        "ShowID": "show-1",
        "ShowDt": "2026-07-05T00:00:00",
        "ShowTm": "2026-07-05T19:30:00",
        "ComicName": "Scott James",
        "ShowPrice": 15.0,
        "soldout": 0,
        "isprivate": False,
    }
    row.update(overrides)
    return row


def _club(metadata: dict | None = None, timezone: str = "America/Chicago") -> Club:
    club = Club(
        id=999,
        name="Westport Funny Bone",
        address="614 Westport Plaza Dr",
        website="https://stlouisfunnybone.com/",
        popularity=0,
        zip_code="63146",
        phone_number="",
        visible=True,
        timezone=timezone,
        city="Maryland Heights",
        state="MO",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="standup_media",
        source_url=_SOURCE_URL,
        metadata=(
            metadata
            if metadata is not None
            else {"standup_media_location_id": _LOCATION_ID, "standup_media_dbname": _DBNAME}
        ),
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


# ---- registry / url ------------------------------------------------------

def test_registry_resolves_standup_media_key():
    assert ScraperResolver().get("standup_media") is StandUpMediaScraper


def test_api_url_built_from_metadata():
    scraper = StandUpMediaScraper(_club())
    assert scraper._api_url() == _API_URL


def test_api_url_none_when_metadata_missing():
    scraper = StandUpMediaScraper(_club(metadata={"standup_media_location_id": _LOCATION_ID}))
    assert scraper._api_url() is None  # dbname absent


async def test_collect_targets_missing_metadata_returns_empty():
    scraper = StandUpMediaScraper(_club(metadata={}))
    assert await scraper.collect_scraping_targets() == []


async def test_collect_targets_returns_api_url():
    scraper = StandUpMediaScraper(_club())
    assert await scraper.collect_scraping_targets() == [_API_URL]


# ---- extractor -----------------------------------------------------------

def test_extractor_dedups_sections_by_showid_keeps_lowest_price():
    """Two price sections share one ShowID -> one event at the lowest price."""
    records = [
        _record(ShowID="s1", ShowPrice=35.0, **{"ShowSec": "VIP"}),
        _record(ShowID="s1", ShowPrice=25.0, **{"ShowSec": "GA"}),
    ]
    events = StandUpMediaExtractor.extract_events(records, _SOURCE_URL)
    assert len(events) == 1
    assert events[0].show_id == "s1"
    assert events[0].price == 25.0


def test_extractor_distinct_showids_distinct_events():
    records = [
        _record(ShowID="s1", ShowTm="2026-07-05T19:30:00"),
        _record(ShowID="s2", ShowTm="2026-07-05T21:00:00", ComicName="Open Mic Night"),
    ]
    events = StandUpMediaExtractor.extract_events(records, _SOURCE_URL)
    assert {e.show_id for e in events} == {"s1", "s2"}


def test_extractor_drops_private_and_malformed():
    records = [
        _record(ShowID="ok"),
        _record(ShowID="priv", isprivate=True),          # private buyout
        _record(ShowID="", ComicName="No Id"),           # missing ShowID
        _record(ShowID="notime", ShowTm=""),             # missing ShowTm
        _record(ShowID="noname", ComicName=""),          # missing ComicName
    ]
    events = StandUpMediaExtractor.extract_events(records, _SOURCE_URL)
    assert [e.show_id for e in events] == ["ok"]


def test_extractor_soldout_only_when_all_sections_soldout():
    # one section sold out, the other not -> showtime is NOT sold out
    mixed = StandUpMediaExtractor.extract_events(
        [_record(ShowID="s1", soldout=1), _record(ShowID="s1", soldout=0)], _SOURCE_URL
    )
    assert mixed[0].sold_out is False
    # every section sold out -> sold out
    allout = StandUpMediaExtractor.extract_events(
        [_record(ShowID="s2", soldout=1), _record(ShowID="s2", soldout=1)], _SOURCE_URL
    )
    assert allout[0].sold_out is True


def test_extractor_zero_price_is_unknown():
    events = StandUpMediaExtractor.extract_events([_record(ShowID="s1", ShowPrice=0.0)], _SOURCE_URL)
    assert events[0].price is None


# ---- event.to_show -------------------------------------------------------

def test_event_to_show_localizes_and_prices():
    events = StandUpMediaExtractor.extract_events([_record(ShowID="s1", ShowPrice=15.0)], _SOURCE_URL)
    show = events[0].to_show(_club())
    assert show is not None
    assert show.name == "Scott James"
    assert show.date.tzinfo is not None          # localized with club tz
    assert show.date.hour == 19 and show.date.minute == 30
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 15.0
    assert show.tickets[0].purchase_url == _SOURCE_URL


# ---- get_data / scrape_async (fetch_json mocked) -------------------------

async def test_get_data_builds_events(monkeypatch):
    scraper = StandUpMediaScraper(_club())
    records = [
        _record(ShowID="s1", ShowPrice=35.0),
        _record(ShowID="s1", ShowPrice=25.0),
        _record(ShowID="s2", ComicName="Open Mic Night", ShowPrice=5.0),
    ]

    async def fake_fetch_json(url):
        assert url == _API_URL
        return records

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    page = await scraper.get_data(_API_URL)
    assert isinstance(page, StandUpMediaPageData)
    assert {e.show_id for e in page.event_list} == {"s1", "s2"}


async def test_get_data_non_list_payload_returns_none(monkeypatch):
    scraper = StandUpMediaScraper(_club())

    async def fake_fetch_json(url):
        return {"Message": "error"}

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    assert await scraper.get_data(_API_URL) is None


async def test_get_data_empty_returns_none(monkeypatch):
    scraper = StandUpMediaScraper(_club())

    async def fake_fetch_json(url):
        return []

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    assert await scraper.get_data(_API_URL) is None


async def test_scrape_async_produces_shows(monkeypatch):
    """End-to-end: targets -> get_data -> transformer pipeline -> Shows."""
    scraper = StandUpMediaScraper(_club())
    records = [
        _record(ShowID="s1", ShowTm="2026-07-05T19:30:00"),
        _record(ShowID="s2", ShowTm="2026-07-05T21:00:00", ComicName="Open Mic Night"),
    ]

    async def fake_fetch_json(url):
        return records

    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    shows = await scraper.scrape_async()
    assert len(shows) == 2
    for show in shows:
        assert show.club_id == scraper.club.id
        assert show.date is not None and show.date.tzinfo is not None
        assert show.tickets
        assert show.tickets[0].purchase_url == _SOURCE_URL
