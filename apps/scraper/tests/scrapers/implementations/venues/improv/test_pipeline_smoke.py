"""
Integration smoke test for the Improv scraper transformation pipeline.

Exercises ImprovPageData(ImprovEvent objects) -> transformation_pipeline.transform()
and asserts non-zero Show objects are produced.

This catches regressions where type mismatches cause can_transform() to return
False for every event, silently dropping all events with no runtime error
(the failure mode from TASK-521).
"""

import importlib.util
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.improv import ImprovEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.improv.data import ImprovPageData
from laughtrack.scrapers.implementations.venues.improv.scraper import ImprovScraper


def _club() -> Club:
    return Club(
        id=1,
        name="Test Improv Club",
        address="123 Comedy St",
        website="https://improv.test",
        scraping_url="https://improv.test/calendar",
        popularity=0,
        zip_code="00000",
        phone_number="000-0000",
        visible=True,
        timezone="America/New_York",
        scraper="improv",
        eventbrite_id=None,
        ticketmaster_id=None,
        seatengine_id=None,
        rate_limit=1.0,
        max_retries=1,
        timeout=5,
    )


def _make_event(name: str, url: str = "https://improv.test/show/1") -> ImprovEvent:
    return ImprovEvent(
        name=name,
        start_date=datetime(2026, 6, 15, 20, 0, tzinfo=timezone.utc),
        url=url,
        description="A great comedy show",
        performers=["Comedian A", "Comedian B"],
        offers=[{"url": "https://improv.test/tickets/1", "price": 20.0, "name": "General Admission"}],
    )


def test_transformation_pipeline_produces_shows_from_improv_events():
    """
    Core regression: transformation_pipeline.transform() must return at least one Show
    when given ImprovPageData with real ImprovEvent objects.

    If can_transform() returns False for ImprovEvent (e.g., due to a type mismatch
    between the transformer's generic parameter and the event type), transform()
    silently returns an empty list with no error.
    """
    club = _club()
    scraper = ImprovScraper(club)

    events = [
        _make_event("Saturday Night Stand-Up", "https://improv.test/show/1"),
        _make_event("Sunday Showcase", "https://improv.test/show/2"),
    ]
    page_data = ImprovPageData(event_list=events)

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows from ImprovPageData with "
        "ImprovEvent objects — check ImprovEventTransformer.can_transform() and that "
        "the transformer is registered with the correct generic type"
    )
    assert all(isinstance(s, Show) for s in shows), (
        f"Expected all items to be Show instances, got: {[type(s) for s in shows]}"
    )
    assert len(shows) == len(events), (
        f"Expected {len(events)} Shows (one per event), got {len(shows)}"
    )


def test_transformation_pipeline_preserves_event_names():
    """Show names produced by the pipeline match the source ImprovEvent names."""
    club = _club()
    scraper = ImprovScraper(club)

    events = [
        _make_event("Comedians on a Thursday", "https://improv.test/show/3"),
    ]
    page_data = ImprovPageData(event_list=events)

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert shows[0].name == "Comedians on a Thursday"
