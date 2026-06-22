"""Pipeline smoke tests for the Tix.com scraper (TASK-3172).

Covers org-id extraction from the public ticket-sales URL, parsing the grouped
JSON feed (date / price / ticket URL across multiple groups), and the opt-in
comedy_filter that isolates a venue's recurring comedy series from its
musical/theatre calendar. The fixture mirrors the real
api_ots/onlinesales/events/organization/<id> shape and includes one comedy
production so the filter's keep-path is exercised even when the live
Playhouse on Park feed is between comedy seasons.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.tix_com.data import TixComPageData
from laughtrack.scrapers.implementations.api.tix_com.extractor import TixComExtractor
from laughtrack.scrapers.implementations.api.tix_com.scraper import TixComScraper

SOURCE_URL = "https://www.tix.com/ticket-sales/playhouseonpark/2704"
API_URL = "https://www.tix.com/api_ots/onlinesales/events/organization/2704"


def _event(event_id: int, name: str, date: str, price, category="Theatre", sub="Musical") -> dict:
    return {
        "EventId": event_id,
        "ProductionName": name,
        "EventDate": date,
        "MinPrice": price,
        "MaxPrice": price,
        "Category": category,
        "SubCategory": sub,
        "VenueName": "Playhouse on Park",
        "VenueCity": "West Hartford",
        "VenueState": "CT",
        "ProductionDescription": f"<p>{name} description</p>",
        "SuppressPrices": False,
    }


# Two groups, mirroring the real groupedEvents shape: a multi-date musical run
# plus a one-off Comedy Nights date.
_PAYLOAD = {
    "payload": {
        "groupedEvents": [
            [
                _event(1431940, "THE WILD PARTY", "2026-07-08T19:30:00", 38.5),
                _event(1431941, "THE WILD PARTY", "2026-07-09T14:00:00", 38.5),
            ],
            [
                _event(1500001, "Comedy Nights at the Park", "2026-09-12T20:00:00", 25.0, "Comedy", "Stand-Up"),
            ],
        ]
    }
}


def _club(comedy_filter: bool = False, url: str = SOURCE_URL) -> Club:
    _c = Club(id=888, name="Playhouse on Park", address='244 Park Rd', website='http://www.playhouseonpark.org/', popularity=0, zip_code='06119', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(
        id=1, club_id=_c.id, platform='custom', scraper_key='tix_com',
        source_url=url, metadata=({"comedy_filter": True} if comedy_filter else {}),
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_extractor_parses_grouped_events():
    events = TixComExtractor.extract_events(_PAYLOAD["payload"], ticket_base_url=SOURCE_URL)
    assert len(events) == 3  # flattened across both groups
    wild = next(e for e in events if e.event_id == 1431940)
    assert wild.title == "THE WILD PARTY"
    assert (wild.date.year, wild.date.month, wild.date.day, wild.date.hour) == (2026, 7, 8, 19)
    assert wild.price == 38.5
    assert wild.show_page_url == "https://www.tix.com/ticket-sales/playhouseonpark/2704/event/1431940"
    assert wild.description == "THE WILD PARTY description"


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.tix.com/ticket-sales/playhouseonpark/2704", "2704"),
        ("https://www.tix.com/ticket-sales/playhouseonpark/2704/", "2704"),
        ("https://www.tix.com/ticket-sales/v2/group/2704", "2704"),
    ],
)
def test_org_id_extracted_from_url(url, expected):
    scraper = TixComScraper(_club(url=url))
    assert scraper._org_id == expected
    assert scraper.validate_configuration() is True


@pytest.mark.asyncio
async def test_get_data_without_filter_keeps_all_events():
    scraper = TixComScraper(_club(comedy_filter=False))
    assert scraper._comedy_filter is False
    scraper.fetch_json = AsyncMock(return_value=_PAYLOAD)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, TixComPageData)
    assert len(result.event_list) == 3


@pytest.mark.asyncio
async def test_get_data_with_filter_keeps_only_comedy():
    scraper = TixComScraper(_club(comedy_filter=True))
    # Stub the DB-backed known-comedian fallback so the test stays DB-free; the
    # keyword pass alone keeps "Comedy Nights" and drops the musical.
    scraper._lineup_handler = MagicMock()
    scraper._lineup_handler.get_comedians_from_show_names.return_value = {}
    scraper.fetch_json = AsyncMock(return_value=_PAYLOAD)

    result = await scraper.get_data(API_URL)

    assert isinstance(result, TixComPageData)
    assert [e.title for e in result.event_list] == ["Comedy Nights at the Park"]


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_payload():
    scraper = TixComScraper(_club())
    scraper.fetch_json = AsyncMock(return_value={"payload": {"groupedEvents": []}})
    assert await scraper.get_data(API_URL) is None


def test_event_to_show_builds_show_with_ticket():
    events = TixComExtractor.extract_events(_PAYLOAD["payload"], ticket_base_url=SOURCE_URL)
    comedy = next(e for e in events if e.event_id == 1500001)
    show = comedy.to_show(_club())
    assert show is not None
    assert show.name == "Comedy Nights at the Park"
    assert show.show_page_url.endswith("/event/1500001")
    assert len(show.tickets) == 1
