from dataclasses import dataclass

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.annoyance import AnnoyancePerformance
from laughtrack.core.entities.event.post_office_cafe import PostOfficeCafePerformance
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.implementations.api.thundertix.scraper import (
    ThunderTixCalendarConfig,
    ThunderTixCalendarScraper,
)


@dataclass
class _PageData(EventListContainer):
    event_list: list


def _club() -> Club:
    club = Club(
        id=999,
        name="ThunderTix Test Venue",
        address="123 Test St",
        website="https://example.com",
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
        source_url="https://example.thundertix.com/reports/calendar",
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _performance_dict(
    title="Public Show",
    event_id=1,
    performance_id=101,
    publicly_available=True,
) -> dict:
    return {
        "title": title,
        "start": "2026-03-24 20:00:00 -0500",
        "event_id": event_id,
        "performance_id": performance_id,
        "time_with_timezone": "Tue - Mar 24, 2026 - 8:00pm CDT",
        "truncated_url": f"/events/{event_id}",
        "order_products_url": f"/orders/new?event_id={event_id}&performance_id={performance_id}",
        "order_tickets_url": None,
        "publicly_available": publicly_available,
        "is_sold_out": False,
    }


class _ConfigurableThunderTixScraper(ThunderTixCalendarScraper):
    key = "configurable_thundertix_test"
    thundertix_config = ThunderTixCalendarConfig(
        base_url="https://example.thundertix.com",
        event_factory=AnnoyancePerformance.from_api_response,
        page_data_factory=lambda events: _PageData(event_list=events),
        weeks_ahead=3,
        current_week_start_ts=lambda: 1743292800,
    )


@pytest.mark.asyncio
async def test_builds_weekly_calendar_targets_from_config():
    scraper = _ConfigurableThunderTixScraper(_club())

    urls = await scraper.collect_scraping_targets()

    assert urls == [
        "https://example.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600",
        "https://example.thundertix.com/reports/calendar?week=0&start=1743897600&end=1744502400",
        "https://example.thundertix.com/reports/calendar?week=0&start=1744502400&end=1745107200",
    ]


@pytest.mark.asyncio
async def test_applies_venue_specific_filter_rules(monkeypatch):
    class AnnoyanceThunderTixScraper(ThunderTixCalendarScraper):
        key = "annoyance_test"
        thundertix_config = ThunderTixCalendarConfig(
            base_url="https://theannoyance.thundertix.com",
            event_factory=AnnoyancePerformance.from_api_response,
            page_data_factory=lambda events: _PageData(event_list=events),
            title_skip_prefixes=("CLASS:", "TRAINING CENTER:"),
        )

    class PostOfficeThunderTixScraper(ThunderTixCalendarScraper):
        key = "post_office_test"
        thundertix_config = ThunderTixCalendarConfig(
            base_url="https://postofficecafecabaret.thundertix.com",
            event_factory=PostOfficeCafePerformance.from_api_response,
            page_data_factory=lambda events: _PageData(event_list=events),
        )

    api_fixture = [
        _performance_dict(title="Public Show", event_id=1, performance_id=101),
        _performance_dict(title="CLASS: Intro to Improv", event_id=2, performance_id=102),
        _performance_dict(title="TRAINING CENTER: Advanced Scene Work", event_id=3, performance_id=103),
        _performance_dict(title="Private Event", event_id=4, performance_id=104, publicly_available=False),
    ]

    async def fake_fetch_json_list(self, url: str):
        return api_fixture

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_json_list", fake_fetch_json_list)

    annoyance_result = await AnnoyanceThunderTixScraper(_club()).get_data(
        "https://theannoyance.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"
    )
    post_office_result = await PostOfficeThunderTixScraper(_club()).get_data(
        "https://postofficecafecabaret.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"
    )

    assert [event.title for event in annoyance_result.event_list] == ["Public Show"]
    assert [event.title for event in post_office_result.event_list] == [
        "Public Show",
        "CLASS: Intro to Improv",
        "TRAINING CENTER: Advanced Scene Work",
    ]
