"""Tests for the opt-in title-exclusion filter on EventbriteScraper (TASK-3246).

Mixed-use Eventbrite organizers (improv training centers, live-music venues)
post class/course/workshop listings to the same organizer feed as their public
shows. The shared eventbrite scraper would otherwise ingest those classes as
comedy "shows". The filter is opt-in per scraping_sources.metadata:

  - ``exclude_classes: true`` applies the built-in class/course/workshop patterns
  - ``exclude_title_patterns: [<regex>, ...]`` applies caller regexes

It is OFF by default, so every existing single-venue/organizer source is
unchanged. These tests cover both the organizer-mode and single-venue-mode
seams plus the default-off behavior.
"""

import importlib.util
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.eventbrite.scraper import EventbriteScraper


_LEELA_ORGANIZER_URL = "https://www.eventbrite.com/o/leela-815038611"


def _club_with_metadata(source_url: str, external_id: str, metadata: dict) -> Club:
    """Build a Club whose active Eventbrite scraping_source carries ``metadata``.

    ``source_metadata`` resolves through the active scraping_source, so the
    filter reads ``metadata`` from here. A ``/o/`` source_url activates
    organizer mode; any other URL stays single-venue.
    """
    club = Club(
        id=9001,
        name="Test Improv Center",
        address="",
        website="",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=False,
    )
    source = ScrapingSource(
        platform="eventbrite",
        scraper_key="eventbrite",
        source_url=source_url,
        external_id=external_id,
        metadata=metadata,
    )
    club.scraping_sources = [source]
    club.activate_scraping_source(source)
    return club


def _api_venue(venue_id: str = "V1", name: str = "The Studio", city: str = "San Francisco", region: str = "CA"):
    from unittest.mock import MagicMock

    address = MagicMock()
    address.address_1 = "450 Geary St"
    address.city = city
    address.region = region
    address.postal_code = "94102"

    venue = MagicMock()
    venue.id = venue_id
    venue.name = name
    venue.address = address
    return venue


def _event(name: str, url: str, api_venue) -> EventbriteEvent:
    return EventbriteEvent(
        name=name,
        event_url=url,
        start_date="2026-07-15T02:30:00Z",
        location_name=api_venue.name,
        venue_id=api_venue.id,
        venue_city=api_venue.address.city,
        venue_state=api_venue.address.region,
        venue_zip=api_venue.address.postal_code,
        data_source_type="api",
        _api_venue=api_venue,
    )


def _venue_club() -> Club:
    club = Club(
        id=7001,
        name="The Studio",
        address="450 Geary St",
        website="",
        popularity=0,
        zip_code="94102",
        phone_number="",
        visible=True,
        city="San Francisco",
        state="CA",
        timezone="America/Los_Angeles",
    )
    club.scraping_sources = [
        ScrapingSource(
            id=7001,
            club_id=7001,
            platform="eventbrite",
            scraper_key="eventbrite",
            source_url="https://www.eventbrite.com",
            external_id="700100",
        )
    ]
    return club


# Mixed feed: 3 class/course listings + 2 real shows, all at one venue.
def _mixed_feed(api_venue):
    return [
        _event("Drop-In Improv Class — Thursdays", "https://eventbrite.com/e/c1", api_venue),
        _event("Improv 1: Let's Play! (Beginner Course)", "https://eventbrite.com/e/c2", api_venue),
        _event("Improv 2: Authentic Relationships", "https://eventbrite.com/e/c3", api_venue),
        _event("Friday Night Stand-Up Showcase", "https://eventbrite.com/e/s1", api_venue),
        _event("The Armando — Student Showcase", "https://eventbrite.com/e/s2", api_venue),
    ]


@pytest.mark.asyncio
async def test_organizer_mode_excludes_class_events_when_exclude_classes_set():
    """exclude_classes drops the 3 class listings; only the 2 shows pass through."""
    club = _club_with_metadata(_LEELA_ORGANIZER_URL, "815038611", {"exclude_classes": True})
    venue = _api_venue()
    feed = _mixed_feed(venue)
    venue_club = _venue_club()

    scraper = EventbriteScraper(club)
    assert scraper._is_organizer_mode is True
    with patch.object(
        scraper.eventbrite_client, "fetch_all_events", new=AsyncMock(return_value=feed)
    ), patch.object(
        scraper._club_handler, "upsert_for_eventbrite_venue", return_value=venue_club
    ):
        shows = await scraper.scrape_async()

    names = sorted(s.name for s in shows)
    assert names == ["Friday Night Stand-Up Showcase", "The Armando — Student Showcase"]
    assert all(isinstance(s, Show) for s in shows)


@pytest.mark.asyncio
async def test_organizer_mode_keeps_all_events_when_filter_off_by_default():
    """No metadata → no filtering: every event (classes included) becomes a Show."""
    club = _club_with_metadata(_LEELA_ORGANIZER_URL, "815038611", {})
    venue = _api_venue()
    feed = _mixed_feed(venue)
    venue_club = _venue_club()

    scraper = EventbriteScraper(club)
    with patch.object(
        scraper.eventbrite_client, "fetch_all_events", new=AsyncMock(return_value=feed)
    ), patch.object(
        scraper._club_handler, "upsert_for_eventbrite_venue", return_value=venue_club
    ):
        shows = await scraper.scrape_async()

    assert len(shows) == len(feed) == 5


@pytest.mark.asyncio
async def test_exclude_title_patterns_custom_regex_drops_matches():
    """A caller-supplied regex drops only the events whose title matches it."""
    club = _club_with_metadata(
        _LEELA_ORGANIZER_URL, "815038611", {"exclude_title_patterns": [r"open mic"]}
    )
    venue = _api_venue()
    feed = [
        _event("Open Mic Night", "https://eventbrite.com/e/1", venue),
        _event("Headliner Stand-Up Show", "https://eventbrite.com/e/2", venue),
    ]
    venue_club = _venue_club()

    scraper = EventbriteScraper(club)
    with patch.object(
        scraper.eventbrite_client, "fetch_all_events", new=AsyncMock(return_value=feed)
    ), patch.object(
        scraper._club_handler, "upsert_for_eventbrite_venue", return_value=venue_club
    ):
        shows = await scraper.scrape_async()

    assert [s.name for s in shows] == ["Headliner Stand-Up Show"]


@pytest.mark.asyncio
async def test_single_venue_mode_applies_filter_in_get_data():
    """The single-venue get_data path also honors the filter."""
    club = _club_with_metadata(
        "https://www.eventbrite.com/_internal/venue/page", "VENUE1", {"exclude_classes": True}
    )
    venue = _api_venue()
    feed = _mixed_feed(venue)

    scraper = EventbriteScraper(club)
    assert scraper._is_organizer_mode is False
    with patch.object(
        scraper.eventbrite_client, "fetch_all_events", new=AsyncMock(return_value=feed)
    ):
        page = await scraper.get_data(club.eventbrite_id)

    kept = [e.name for e in page.event_list]
    assert kept == ["Friday Night Stand-Up Showcase", "The Armando — Student Showcase"]


@pytest.mark.asyncio
async def test_include_title_patterns_keeps_only_matching_comedy_events():
    """include_title_patterns keeps ONLY comedy on a mixed Blues/Jazz/Comedy feed.

    Models TASK-3205 (Deja Blue): one Eventbrite organizer feed carries music
    acts named after the band/DJ alongside comedy shows. A comedy include
    filter keeps the two comedy titles and drops the three music acts.
    """
    club = _club_with_metadata(
        _LEELA_ORGANIZER_URL,
        "815038611",
        {"include_title_patterns": [r"comedy", r"stand[\s-]?up", r"comedian"]},
    )
    venue = _api_venue()
    feed = [
        _event("Aki Kumar", "https://eventbrite.com/e/m1", venue),
        _event("DJ Carmaa", "https://eventbrite.com/e/m2", venue),
        _event("Isaiah Band", "https://eventbrite.com/e/m3", venue),
        _event("Summer Heat Comedy Show", "https://eventbrite.com/e/c1", venue),
        _event("Live at Deja Blue: Comedy All Stars", "https://eventbrite.com/e/c2", venue),
    ]
    venue_club = _venue_club()

    scraper = EventbriteScraper(club)
    with patch.object(
        scraper.eventbrite_client, "fetch_all_events", new=AsyncMock(return_value=feed)
    ), patch.object(
        scraper._club_handler, "upsert_for_eventbrite_venue", return_value=venue_club
    ):
        shows = await scraper.scrape_async()

    assert sorted(s.name for s in shows) == [
        "Live at Deja Blue: Comedy All Stars",
        "Summer Heat Comedy Show",
    ]


@pytest.mark.asyncio
async def test_include_and_exclude_patterns_compose():
    """include + exclude compose: must match include AND not match exclude."""
    club = _club_with_metadata(
        _LEELA_ORGANIZER_URL,
        "815038611",
        {
            "include_title_patterns": [r"comedy"],
            "exclude_title_patterns": [r"open mic"],
        },
    )
    venue = _api_venue()
    feed = [
        _event("Comedy Showcase", "https://eventbrite.com/e/1", venue),
        _event("Open Mic Comedy", "https://eventbrite.com/e/2", venue),
        _event("Jazz Trio", "https://eventbrite.com/e/3", venue),
    ]
    venue_club = _venue_club()

    scraper = EventbriteScraper(club)
    with patch.object(
        scraper.eventbrite_client, "fetch_all_events", new=AsyncMock(return_value=feed)
    ), patch.object(
        scraper._club_handler, "upsert_for_eventbrite_venue", return_value=venue_club
    ):
        shows = await scraper.scrape_async()

    # "Comedy Showcase" survives; "Open Mic Comedy" matches include but is
    # dropped by exclude; "Jazz Trio" never matches include.
    assert [s.name for s in shows] == ["Comedy Showcase"]


def test_invalid_custom_regex_is_skipped_without_crashing():
    """A malformed regex is dropped with a warning; valid patterns still apply."""
    club = _club_with_metadata(
        _LEELA_ORGANIZER_URL, "815038611", {"exclude_title_patterns": ["(unclosed", r"workshop"]}
    )
    scraper = EventbriteScraper(club)
    patterns = scraper._title_exclusion_patterns()
    # Only the valid "workshop" pattern compiles.
    assert len(patterns) == 1
    assert patterns[0].search("Improv Workshop") is not None
