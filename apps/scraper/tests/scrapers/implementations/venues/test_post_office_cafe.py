import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.post_office_cafe.data import PostOfficeCafePageData
from laughtrack.scrapers.implementations.venues.post_office_cafe.scraper import PostOfficeCafeScraper


CALENDAR_URL = "https://postofficecafecabaret.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"


def _club() -> Club:
    club = Club(
        id=999,
        name="Post Office Cafe & Cabaret",
        address="303 Commercial St",
        website="https://www.postofficecafe.net",
        popularity=0,
        zip_code="02657",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="",
        source_url="https://postofficecafecabaret.thundertix.com/reports/calendar",
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _performance_dict(title="Public Show", publicly_available=True) -> dict:
    return {
        "title": title,
        "start": "2026-03-24 20:00:00 -0400",
        "event_id": 207875,
        "performance_id": 3231744,
        "time_with_timezone": "Tue - Mar 24, 2026 - 8:00pm EDT",
        "truncated_url": "/events/207875",
        "order_products_url": "/orders/new?event_id=207875&performance_id=3231744",
        "order_tickets_url": None,
        "publicly_available": publicly_available,
        "is_sold_out": False,
    }


@pytest.mark.asyncio
async def test_post_office_cafe_thundertix_regression(monkeypatch):
    scraper = PostOfficeCafeScraper(_club())
    api_fixture = [
        _performance_dict(title="Public Show"),
        _performance_dict(title="CLASS: Cabaret Workshop"),
        _performance_dict(title="Private Event", publicly_available=False),
    ]

    async def fake_fetch_json_list(self, url: str):
        return api_fixture

    monkeypatch.setattr(PostOfficeCafeScraper, "fetch_json_list", fake_fetch_json_list)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, PostOfficeCafePageData)
    assert [event.title for event in result.event_list] == [
        "Public Show",
        "CLASS: Cabaret Workshop",
    ]
