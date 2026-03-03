import asyncio
from datetime import datetime, timezone

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.event import JsonLdEvent, Place, PostalAddress
from laughtrack.scrapers.implementations.venues.improv import scraper as improv_scraper_module
from laughtrack.scrapers.implementations.venues.improv.scraper import ImprovScraper
from laughtrack.scrapers.implementations.venues.improv.data import ImprovPageData


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


def _make_event(label: str) -> JsonLdEvent:
    return JsonLdEvent(
        name=f"Event {label}",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        location=Place(
            name="Test Venue",
            address=PostalAddress(
                street_address="123 St",
                address_locality="City",
                address_region="ST",
                postal_code="00000",
                address_country="US",
            ),
        ),
        offers=[],
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

    def fake_get_next(self, html, current_url, anchor_id=None):
        return None  # stop after first page

    def fake_extract_ticket_links(html, base_url, ctx):
        return ["https://example.com/t1", "https://example.com/t2"]

    monkeypatch.setattr(ImprovScraper, "fetch_html", fake_fetch_html, raising=False)
    monkeypatch.setattr(improv_scraper_module.Paginator, "get_url_by_anchor_id", fake_get_next, raising=False)
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
    assert all(isinstance(e, JsonLdEvent) for e in result.event_list)
    assert [e.name for e in result.event_list] == ["Event E1", "Event E2", "Event E3"]
