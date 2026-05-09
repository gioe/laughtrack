from dataclasses import dataclass

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.thundertix import ThunderTixPerformance
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.implementations.api.thundertix.data import ThunderTixPageData
from laughtrack.scrapers.implementations.api.thundertix.scraper import (
    GenericThunderTixScraper,
    ThunderTixCalendarConfig,
    ThunderTixCalendarScraper,
)


@dataclass
class _PageData(EventListContainer):
    event_list: list


def _club(
    source_url: str = "https://example.thundertix.com",
    metadata: dict | None = None,
) -> Club:
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
        platform="thundertix",
        scraper_key="thundertix",
        source_url=source_url,
        external_id=None,
        metadata=metadata or {},
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


# ---------------------------------------------------------------------------
# Engine-level tests (ThunderTixCalendarScraper) — exercised via a small
# anonymous subclass so the config can be hard-coded from the test fixture.
# ---------------------------------------------------------------------------


class _ConfigurableThunderTixScraper(ThunderTixCalendarScraper):
    key = "configurable_thundertix_test"
    thundertix_config = ThunderTixCalendarConfig(
        base_url="https://example.thundertix.com",
        event_factory=ThunderTixPerformance.from_api_response,
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
async def test_engine_applies_publicly_available_and_title_skip_filters(monkeypatch):
    class _SkipPrefixScraper(ThunderTixCalendarScraper):
        key = "thundertix_skip_test"
        thundertix_config = ThunderTixCalendarConfig(
            base_url="https://example.thundertix.com",
            event_factory=ThunderTixPerformance.from_api_response,
            page_data_factory=lambda events: _PageData(event_list=events),
            title_skip_prefixes=("CLASS:", "TRAINING CENTER:"),
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

    result = await _SkipPrefixScraper(_club()).get_data(
        "https://example.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"
    )

    assert [event.title for event in result.event_list] == ["Public Show"]


# ---------------------------------------------------------------------------
# GenericThunderTixScraper — config built per-instance from scraping_sources.
# ---------------------------------------------------------------------------


def test_generic_scraper_builds_config_from_club_source_url_only():
    """Bare base URL in source_url is used as-is; no skip-prefixes by default."""
    scraper = GenericThunderTixScraper(
        _club(source_url="https://postofficecafecabaret.thundertix.com")
    )

    assert scraper.thundertix_config.base_url == "https://postofficecafecabaret.thundertix.com"
    assert scraper.thundertix_config.title_skip_prefixes == ()


def test_generic_scraper_strips_calendar_path_from_source_url():
    """source_url ending in /reports/calendar is normalized to the venue root."""
    scraper = GenericThunderTixScraper(
        _club(source_url="https://theannoyance.thundertix.com/reports/calendar")
    )

    assert scraper.thundertix_config.base_url == "https://theannoyance.thundertix.com"


def test_generic_scraper_parses_title_skip_prefixes_metadata():
    """metadata.title_skip_prefixes (CSV) is parsed into a tuple of trimmed strings."""
    scraper = GenericThunderTixScraper(
        _club(
            source_url="https://theannoyance.thundertix.com",
            metadata={"title_skip_prefixes": "CLASS:, TRAINING CENTER:"},
        )
    )

    assert scraper.thundertix_config.title_skip_prefixes == ("CLASS:", "TRAINING CENTER:")


@pytest.mark.asyncio
async def test_generic_scraper_collects_12_weekly_urls_from_club_base():
    scraper = GenericThunderTixScraper(
        _club(source_url="https://theannoyance.thundertix.com")
    )

    urls = await scraper.collect_scraping_targets()

    assert len(urls) == 12
    for url in urls:
        assert url.startswith(
            "https://theannoyance.thundertix.com/reports/calendar?week=0&start="
        )


@pytest.mark.asyncio
async def test_generic_scraper_get_data_returns_thundertix_page_data(monkeypatch):
    """get_data() returns a ThunderTixPageData with publicly_available + skip-prefix filtering applied."""
    scraper = GenericThunderTixScraper(
        _club(
            source_url="https://theannoyance.thundertix.com",
            metadata={"title_skip_prefixes": "CLASS:,TRAINING CENTER:"},
        )
    )

    api_fixture = [
        _performance_dict(title="Public Show", event_id=1, performance_id=101),
        _performance_dict(title="CLASS: Intro to Improv", event_id=2, performance_id=102),
        _performance_dict(title="Private Event", event_id=4, performance_id=104, publicly_available=False),
    ]

    async def fake_fetch_json_list(self, url: str):
        return api_fixture

    monkeypatch.setattr(ThunderTixCalendarScraper, "fetch_json_list", fake_fetch_json_list)

    result = await scraper.get_data(
        "https://theannoyance.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"
    )

    assert isinstance(result, ThunderTixPageData)
    assert [event.title for event in result.event_list] == ["Public Show"]
    only_event = result.event_list[0]
    assert only_event.ticket_url == (
        "https://theannoyance.thundertix.com/orders/new?event_id=1&performance_id=101"
    )
