import asyncio
import importlib.util
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
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
        url=f"https://example.com/{label}",
        description="desc",
    )


@pytest.mark.asyncio
async def test_improv_scraper_flattens_batch_results(monkeypatch):
    # Arrange: club and scraper
    club = Club(
        id=1,
        name="Test Club",
        address="123 St",
        website="https://example.com",
        scraping_url="https://improv.test/calendar",
        popularity=0,
        zip_code="00000",
        phone_number="000-0000",
        visible=True,
        timezone="UTC",
        scraper="improv",
        eventbrite_id=None,
        ticketmaster_id=None,
        seatengine_id=None,
        rate_limit=1.0,
        max_retries=1,
        timeout=5,
    )
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
    club = Club(
        id=1,
        name="Test Club",
        address="123 St",
        website="https://example.com",
        scraping_url="https://improv.test/calendar",
        popularity=0,
        zip_code="00000",
        phone_number="000-0000",
        visible=True,
        timezone="UTC",
        scraper="improv",
        eventbrite_id=None,
        ticketmaster_id=None,
        seatengine_id=None,
        rate_limit=1.0,
        max_retries=1,
        timeout=5,
    )
    transformer = ImprovEventTransformer(club)
    event = _make_event("X")
    assert transformer.can_transform(event), "ImprovEventTransformer must accept ImprovEvent instances"
