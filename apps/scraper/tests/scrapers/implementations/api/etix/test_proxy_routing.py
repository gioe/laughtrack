"""Tests for generic Etix fetch routing."""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper


def _club() -> Club:
    club = Club(
        id=207,
        name="Dr. Grins Comedy Club",
        address="",
        website="https://www.thebob.com/dr-grins",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/Detroit",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="etix",
        scraper_key="dr_grins",
        source_url=(
            "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue"
            "?venue_id=35455&orderBy=1&pageNumber=1"
        ),
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


@pytest.mark.asyncio
async def test_etix_fetches_use_shared_etix_proxy_key(monkeypatch):
    """Venue-specific Etix subclasses still route HTTP through scraper_key='etix'."""
    scraper = EtixScraper(_club())
    fetch_html = AsyncMock(return_value="<html></html>")
    monkeypatch.setattr(scraper, "fetch_html", fetch_html)

    await scraper.collect_scraping_targets()

    assert fetch_html.await_args.kwargs["scraper_key"] == "etix"
