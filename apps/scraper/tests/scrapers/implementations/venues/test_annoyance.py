import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.annoyance.data import AnnoyancePageData
from laughtrack.scrapers.implementations.venues.annoyance.scraper import AnnoyanceTheatreScraper


CALENDAR_URL = "https://theannoyance.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"


def _club() -> Club:
    club = Club(
        id=999,
        name="The Annoyance Theatre",
        address="851 W. Belmont Ave",
        website="https://www.theannoyance.com",
        popularity=0,
        zip_code="60657",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="",
        source_url="https://theannoyance.thundertix.com/reports/calendar",
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _performance_dict(title="Tuesday Musical Improv", publicly_available=True) -> dict:
    return {
        "title": title,
        "start": "2026-03-24 20:00:00 -0500",
        "event_id": 207875,
        "performance_id": 3231744,
        "time_with_timezone": "Tue - Mar 24, 2026 - 8:00pm CDT",
        "truncated_url": "/events/207875",
        "order_products_url": "/orders/new?event_id=207875&performance_id=3231744",
        "order_tickets_url": None,
        "publicly_available": publicly_available,
        "is_sold_out": False,
    }


@pytest.mark.asyncio
async def test_annoyance_thundertix_regression(monkeypatch):
    scraper = AnnoyanceTheatreScraper(_club())
    api_fixture = [
        _performance_dict(title="Tuesday Musical Improv"),
        _performance_dict(title="CLASS: Intro to Improv"),
        _performance_dict(title="TRAINING CENTER: Advanced Scene Work"),
        _performance_dict(title="Private Event", publicly_available=False),
    ]

    async def fake_fetch_json_list(self, url: str):
        return api_fixture

    monkeypatch.setattr(AnnoyanceTheatreScraper, "fetch_json_list", fake_fetch_json_list)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, AnnoyancePageData)
    assert [event.title for event in result.event_list] == ["Tuesday Musical Improv"]
