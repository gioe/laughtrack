"""Tests for the generic accesso ShoWare scraper."""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.showare import ShoWarePerformance
from laughtrack.scrapers.implementations.api.showare.scraper import GenericShoWareScraper


SOURCE_URL = "https://shucommunitytheatre.showare.com/default.asp"
BASE_URL = "https://shucommunitytheatre.showare.com"


def _club(metadata: dict | None = None) -> Club:
    club = Club(
        id=2578,
        name="SHU Community Theatre",
        address="1420 Post Rd, Fairfield, CT",
        website="https://www.shucommunitytheatre.org/",
        popularity=0,
        zip_code="06824",
        phone_number="",
        visible=True,
        timezone="America/New_York",
        city="Fairfield",
        state="CT",
    )
    club.active_scraping_source = ScrapingSource(
        id=1587,
        club_id=club.id,
        platform="custom",
        scraper_key="showare",
        source_url=SOURCE_URL,
        external_id=None,
        metadata=metadata or {},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _payload() -> dict:
    return {
        "performance": [
            {
                "EventID": 907,
                "PerformanceID": 907,
                "Event": "Ferris Bueller's Day Off screening event",
                "PerformanceName": "Ferris Bueller's Day Off",
                "PerformanceDateTime": "Thursday, June 11, 2026 5:30:00 PM",
                "PerformanceMinPrice": 12,
                "PerformanceMaxPrice": 12,
                "AvailableTickets": 100,
            },
            {
                "EventID": 898,
                "PerformanceID": 898,
                "Event": "Comedy Bang! Bang!",
                "PerformanceName": "Comedy Bang! Bang!",
                "PerformanceDateTime": "Sunday, June 28, 2026 8:00:00 PM",
                "PerformanceMinPrice": 56.5,
                "PerformanceMaxPrice": 76.5,
                "AvailableTickets": 42,
            },
            {
                "EventID": 898,
                "PerformanceID": 904,
                "Event": "Comedy Bang! Bang!",
                "PerformanceName": "Comedy Bang! Bang!",
                "PerformanceDateTime": "Sunday, June 28, 2026 8:00:00 PM",
                "PerformanceMinPrice": 176.5,
                "PerformanceMaxPrice": 176.5,
                "AvailableTickets": 10,
            },
            {
                "EventID": 901,
                "PerformanceID": 901,
                "Event": "Leslie Jones",
                "PerformanceName": "Leslie Jones",
                "PerformanceDateTime": "Friday, October 9, 2026 8:00:00 PM",
                "PerformanceMinPrice": 56.5,
                "PerformanceMaxPrice": 76.5,
                "AvailableTickets": 0,
            },
            {
                "EventID": -1,
                "PerformanceID": 1,
                "Event": "",
                "PerformanceDateTime": "Sunday, May 31, 2026 2:00:00 PM",
            },
        ]
    }


def test_performance_from_api_response_builds_detail_and_ticket_urls():
    event = ShoWarePerformance.from_api_response(_payload()["performance"][1], BASE_URL)

    assert event is not None
    assert event.title == "Comedy Bang! Bang!"
    assert event.detail_url == f"{BASE_URL}/eventperformances.asp?evt=898"
    assert event.ticket_url == f"{BASE_URL}/ordertickets.asp?p=898&src=default"


@pytest.mark.asyncio
async def test_scraper_fetches_performances_and_filters_movie_rows(monkeypatch):
    seen = {}

    async def fake_fetch_json(self, url: str, **kwargs):
        seen["url"] = url
        seen["headers"] = kwargs.get("headers")
        return _payload()

    monkeypatch.setattr(GenericShoWareScraper, "fetch_json", fake_fetch_json)

    scraper = GenericShoWareScraper(
        _club(
            metadata={
                "include_title_patterns": ["Comedy", "Leslie Jones"],
                "exclude_title_patterns": ["screening", "movie"],
            }
        )
    )

    targets = await scraper.collect_scraping_targets()
    page_data = await scraper.get_data(targets[0])

    assert "performancelist.asp" in seen["url"]
    assert seen["headers"]["Referer"] == f"{BASE_URL}/default.asp"
    assert page_data is not None
    assert [event.title for event in page_data.event_list] == [
        "Comedy Bang! Bang!",
        "Leslie Jones",
    ]
    assert page_data.event_list[0].performance_id == 898


def test_event_converts_to_show_with_local_timezone_and_ticket_price():
    raw_event = next(item for item in _payload()["performance"] if item.get("EventID") == 901)
    event = ShoWarePerformance.from_api_response(raw_event, BASE_URL)
    assert event is not None

    show = event.to_show(_club(), enhanced=False)

    assert show is not None
    assert show.name == "Leslie Jones"
    assert show.date.isoformat() == "2026-10-09T20:00:00-04:00"
    assert show.show_page_url == f"{BASE_URL}/eventperformances.asp?evt=901"
    assert show.tickets[0].purchase_url == f"{BASE_URL}/ordertickets.asp?p=901&src=default"
    assert show.tickets[0].price == 56.5
    assert show.tickets[0].sold_out is True
