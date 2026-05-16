from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.ticketmaster.data import TicketmasterPageData
from laughtrack.scrapers.implementations.api.ticketmaster.scraper import (
    FocusedTicketmasterComedyScraper,
    TicketmasterScraper,
)


def _club(scraper_key: str = "ticketmaster_comedy") -> Club:
    club = Club(
        id=2503,
        name="DAR Constitution Hall",
        address="1776 D St NW",
        website="https://www.dar.org/constitution-hall",
        popularity=0,
        zip_code="20006",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="ticketmaster",
        scraper_key=scraper_key,
        ticketmaster_id="KovZpaKdYe",
        source_url="https://www.ticketmaster.com/dar-constitution-hall-tickets-washington/venue/172008",
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _event(
    event_id: str,
    name: str,
    *,
    segment: str = "Arts & Theatre",
    genre: str = "Comedy",
    sub_genre: str = "Comedy",
) -> dict:
    return {
        "id": event_id,
        "name": name,
        "url": f"https://www.ticketmaster.com/event/{event_id}",
        "dates": {"start": {"localDate": "2026-08-01", "localTime": "20:00:00"}},
        "classifications": [
            {
                "segment": {"name": segment},
                "genre": {"name": genre},
                "subGenre": {"name": sub_genre},
            }
        ],
    }


@pytest.mark.asyncio
async def test_fetches_ticketmaster_events_with_comedy_classification():
    scraper = FocusedTicketmasterComedyScraper(_club())

    mock_client = MagicMock()
    mock_client.fetch_events = AsyncMock(return_value=[_event("evt-comedy", "Comedy Show")])
    with patch(
        "laughtrack.scrapers.implementations.api.ticketmaster.scraper.TicketmasterClient",
        return_value=mock_client,
    ):
        result = await scraper.get_data("https://app.ticketmaster.com/discovery/v2/events.json?venueId=KovZpaKdYe")

    assert isinstance(result, TicketmasterPageData)
    assert len(result.event_list) == 1
    mock_client.fetch_events.assert_awaited_once_with(
        "KovZpaKdYe",
        size=200,
        sort="date,asc",
        classificationName="Comedy",
    )


@pytest.mark.asyncio
async def test_excludes_non_comedy_and_add_on_events():
    scraper = FocusedTicketmasterComedyScraper(_club())
    comedy = _event("evt-comedy", "Ali Siddiq")
    music = _event("evt-music", "Averly Morillo", segment="Music", genre="Latin", sub_genre="Latin")
    addon = _event("evt-addon", "Ali Siddiq - VIP Club Access")

    mock_client = MagicMock()
    mock_client.fetch_events = AsyncMock(return_value=[comedy, music, addon])
    with patch(
        "laughtrack.scrapers.implementations.api.ticketmaster.scraper.TicketmasterClient",
        return_value=mock_client,
    ):
        result = await scraper.get_data("https://app.ticketmaster.com/discovery/v2/events.json?venueId=KovZpaKdYe")

    assert isinstance(result, TicketmasterPageData)
    assert [event["id"] for event in result.event_list] == ["evt-comedy"]


def test_live_nation_scraper_does_not_request_classification_filter():
    scraper = TicketmasterScraper(_club("live_nation"))

    mock_client = MagicMock()
    mock_client.fetch_events = AsyncMock(return_value=[])
    with patch(
        "laughtrack.scrapers.implementations.api.ticketmaster.scraper.TicketmasterClient",
        return_value=mock_client,
    ):
        import asyncio

        asyncio.run(scraper.get_data("https://app.ticketmaster.com/discovery/v2/events.json?venueId=KovZpaKdYe"))

    _, kwargs = mock_client.fetch_events.await_args
    assert "classificationName" not in kwargs


def test_focused_scraper_key_is_discoverable():
    assert ScraperResolver().get("ticketmaster_comedy") is FocusedTicketmasterComedyScraper
