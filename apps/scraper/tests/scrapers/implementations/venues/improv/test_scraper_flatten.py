import asyncio
import importlib.util
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.improv import ImprovEvent
from laughtrack.scrapers.implementations.venues.improv import scraper as improv_scraper_module
from laughtrack.scrapers.implementations.venues.improv.scraper import ImprovScraper
from laughtrack.scrapers.implementations.venues.improv.data import ImprovPageData
from laughtrack.scrapers.implementations.venues.improv.transformer import ImprovEventTransformer


class FakeBatchScraper:
    def __init__(self, logger_context, config=None):
        self.logger_context = logger_context
        self.config = config

    async def process_batch(self, items, processor, description=None):
        # Return nested lists with an empty sublist in the middle to verify flattening
        return [
            [_make_event("E1")],
            [],
            [_make_event("E2"), _make_event("E3")],
        ]


def _make_event(label: str) -> ImprovEvent:
    return ImprovEvent(
        name=f"Event {label}",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        url=f"https://www.ticketweb.com/event/addison-match-addison-improv-tickets/{label}?pl=addisonimprov&REFID=addisonWP",
        description="desc",
        location_name="Addison Improv",
    )


@pytest.mark.asyncio
async def test_improv_scraper_flattens_batch_results(monkeypatch):
    # Arrange: club and scraper
    club = Club(id=29, name='Addison Improv', address='123 St', website='https://example.com', popularity=0, zip_code='00000', phone_number='000-0000', visible=True, timezone='UTC', rate_limit=1.0, max_retries=1, timeout=5)
    club.active_scraping_source = ScrapingSource(id=1, club_id=club.id, platform='eventbrite', scraper_key='improv', source_url='https://improvtx.com/addison/calendar', external_id=None)
    club.scraping_sources = [club.active_scraping_source]
    scraper = ImprovScraper(club)

    # Patch network-dependent methods
    async def fake_fetch_html(self, url: str):
        return "<html></html>"

    def fake_get_next(html, anchor_id, base_url=None):
        return None  # stop after first page

    def fake_extract_ticket_links(html, base_url, ctx):
        return ["https://example.com/t1", "https://example.com/t2"]

    monkeypatch.setattr(ImprovScraper, "fetch_html", fake_fetch_html, raising=False)
    monkeypatch.setattr(improv_scraper_module.HtmlScraper, "get_link_url_by_id", fake_get_next, raising=False)
    monkeypatch.setattr(
        improv_scraper_module.ImprovExtractor,
        "extract_ticket_links",
        fake_extract_ticket_links,
        raising=False,
    )

    # Patch BatchScraper in the module under test
    monkeypatch.setattr(improv_scraper_module, "BatchScraper", FakeBatchScraper, raising=True)

    # Act
    result = await scraper.get_data("https://improv.test/calendar")

    # Assert
    assert isinstance(result, ImprovPageData)
    assert len(result.event_list) == 3
    assert all(isinstance(e, ImprovEvent) for e in result.event_list)
    assert [e.name for e in result.event_list] == ["Event E1", "Event E2", "Event E3"]


def test_improv_event_transformer_can_transform_improv_event():
    """Regression: ImprovEventTransformer.can_transform() must return True for ImprovEvent."""
    club = Club(id=1, name='Test Club', address='123 St', website='https://example.com', popularity=0, zip_code='00000', phone_number='000-0000', visible=True, timezone='UTC', rate_limit=1.0, max_retries=1, timeout=5)
    club.active_scraping_source = ScrapingSource(id=1, club_id=club.id, platform='eventbrite', scraper_key='improv', source_url='https://improv.test/calendar', external_id=None)
    club.scraping_sources = [club.active_scraping_source]
    transformer = ImprovEventTransformer(club)
    event = _make_event("X")
    assert transformer.can_transform(event), "ImprovEventTransformer must accept ImprovEvent instances"


@pytest.mark.asyncio
async def test_improv_scraper_filters_cross_venue_events(monkeypatch):
    club = Club(id=29, name='Addison Improv', address='123 St', website='https://example.com', popularity=0, zip_code='00000', phone_number='000-0000', visible=True, timezone='UTC', rate_limit=1.0, max_retries=1, timeout=5)
    club.active_scraping_source = ScrapingSource(id=1, club_id=club.id, platform='eventbrite', scraper_key='improv', source_url='https://improvtx.com/addison/calendar', external_id=None)
    club.scraping_sources = [club.active_scraping_source]
    scraper = ImprovScraper(club)

    matching = ImprovEvent(
        name="Addison Match",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        url="https://www.ticketweb.com/event/addison-match-addison-improv-tickets/1?pl=addisonimprov&REFID=addisonWP",
        location_name="Addison Improv",
        offers=[
            {
                "url": "https://www.ticketweb.com/event/addison-match-addison-improv-tickets/1?pl=addisonimprov&REFID=addisonWP",
                "price": "20",
                "name": "General Admission",
            }
        ],
    )
    cross_venue = ImprovEvent(
        name="Houston Leak",
        start_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
        url="https://www.ticketweb.com/event/houston-leak-houston-improv-tickets/2?pl=houstonimprov&REFID=houstonWP",
        location_name="Houston Improv",
        offers=[
            {
                "url": "https://www.ticketweb.com/event/houston-leak-houston-improv-tickets/2?pl=houstonimprov&REFID=houstonWP",
                "price": "20",
                "name": "General Admission",
            }
        ],
    )

    class FilteringBatchScraper:
        def __init__(self, logger_context, config=None):
            self.logger_context = logger_context
            self.config = config

        async def process_batch(self, items, processor, description=None):
            return [[matching], [cross_venue]]

    async def fake_fetch_html(self, url: str):
        return "<html></html>"

    def fake_get_next(html, anchor_id, base_url=None):
        return None

    def fake_extract_ticket_links(html, base_url, ctx):
        return ["https://example.com/t1", "https://example.com/t2"]

    monkeypatch.setattr(ImprovScraper, "fetch_html", fake_fetch_html, raising=False)
    monkeypatch.setattr(improv_scraper_module.HtmlScraper, "get_link_url_by_id", fake_get_next, raising=False)
    monkeypatch.setattr(
        improv_scraper_module.ImprovExtractor,
        "extract_ticket_links",
        fake_extract_ticket_links,
        raising=False,
    )
    monkeypatch.setattr(improv_scraper_module, "BatchScraper", FilteringBatchScraper, raising=True)

    result = await scraper.get_data(club.scraping_url)

    assert isinstance(result, ImprovPageData)
    assert [event.name for event in result.event_list] == ["Addison Match"]


def test_improv_scraper_url_fallback_rejects_other_club_ticketweb_urls():
    club = Club(id=29, name='Addison Improv', address='123 St', website='https://example.com', popularity=0, zip_code='00000', phone_number='000-0000', visible=True, timezone='UTC', rate_limit=1.0, max_retries=1, timeout=5)
    club.active_scraping_source = ScrapingSource(id=1, club_id=club.id, platform='eventbrite', scraper_key='improv', source_url='https://improvtx.com/addison/calendar', external_id=None)
    club.scraping_sources = [club.active_scraping_source]
    scraper = ImprovScraper(club)

    matching = ImprovEvent(
        name="Addison Match",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        url="https://www.ticketweb.com/event/addison-match-addison-improv-tickets/1?pl=addisonimprov&REFID=addisonWP",
        location_name="",
        offers=[],
    )
    cross_venue = ImprovEvent(
        name="Houston Leak",
        start_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
        url="https://www.ticketweb.com/event/houston-leak-houston-improv-tickets/2?pl=houstonimprov&REFID=houstonWP",
        location_name="",
        offers=[],
    )

    assert scraper._event_matches_current_club(matching) is True
    assert scraper._event_matches_current_club(cross_venue) is False
