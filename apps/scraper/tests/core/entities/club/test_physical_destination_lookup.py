"""Real PostgreSQL destination lookup does not require a scraping source."""

import os
from unittest.mock import AsyncMock

import psycopg2
import pytest
from psycopg2.extras import RealDictCursor

from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.scrapers.implementations.api.seatengine.scraper import SeatEngineScraper
from tests.scrapers.implementations.api.seatengine.test_organizer_venue_routing import event, source_club


@pytest.fixture
def database(monkeypatch):
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL required for physical destination PostgreSQL regression")
    connection = psycopg2.connect(dsn)
    with connection.cursor() as cursor:
        # No scraping_sources table exists in this isolated fixture: physical
        # destinations must be readable without joining scrape configuration.
        cursor.execute("""
            CREATE TEMP TABLE clubs (
                id integer PRIMARY KEY, name text, address text, website text,
                popularity integer DEFAULT 0, zip_code text, phone_number text,
                visible boolean, timezone text, status text
            );
            INSERT INTO clubs VALUES
                (9001,'Physical theatre','1111 Prospect St','https://physical.example',
                 0,'46203','',true,'America/Indiana/Indianapolis','active'),
                (9002,'Hidden producer','','https://hidden.example',
                 0,'','',false,'America/New_York','active'),
                (9003,'Inactive theatre','','https://inactive.example',
                 0,'','',true,'America/New_York','closed');
        """)

    def execute(self, operation, params=None, return_results=False, **kwargs):
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(operation, params)
            return cursor.fetchall() if return_results else None

    monkeypatch.setattr(ClubHandler, "execute_with_cursor", execute)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_destination_lookup_returns_visible_active_source_less_clubs(database):
    handler = ClubHandler()
    clubs = handler.get_physical_clubs_by_ids([9003, 9002, 9001, 9999])
    assert [(club.id, club.name, club.timezone) for club in clubs] == [
        (9001, "Physical theatre", "America/Indiana/Indianapolis")
    ]
    assert clubs[0].scraping_sources == []
    assert handler.get_physical_clubs_by_ids([]) == []


@pytest.mark.asyncio
async def test_pipeline_routes_through_actual_source_less_destination_query(database):
    club = source_club()
    del club.source_metadata["seatengine_venue_routes"]["routes"]["102"]
    scraper = SeatEngineScraper(club)
    scraper.seatengine_client.fetch_events = AsyncMock(return_value=[event()])
    page = await scraper.get_data("618")
    shows = scraper.transform_data(page, "618")
    assert len(shows) == 1 and shows[0].club_id == 9001
    assert scraper.seatengine_client.routing_errors == []


@pytest.mark.asyncio
async def test_hidden_destination_is_held_without_fetching_account(database):
    club = source_club()
    routes = club.source_metadata["seatengine_venue_routes"]["routes"]
    del routes["102"]
    routes["101"]["club_id"] = 9002
    scraper = SeatEngineScraper(club)
    scraper.seatengine_client.fetch_events = AsyncMock(return_value=[event()])
    assert not (await scraper.get_data("618")).event_list
    scraper.seatengine_client.fetch_events.assert_not_called()
    assert scraper.seatengine_client.routing_errors
