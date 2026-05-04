"""Tests for EventbriteScraper organizer-mode and the synthetic-proxy
production-company path that drives it (TASK-1891).



Covers the full Encore Comedy flow:
- _extract_eventbrite_organizer_id parses the seed-data URL into an organizer id.
- _build_synthetic_proxy_for_company constructs an in-memory Club whose only
  ScrapingSource targets the Eventbrite organizer endpoint.
- EventbriteScraper, given that synthetic proxy, runs organizer-mode scraping:
  groups the API events by venue, upserts one clubs row per distinct venue, and
  returns one Show per event whose club_id is the per-venue club id (NOT the
  proxy's id) so multi-venue organizers stop forcing every event under a single
  fake aggregator club.
- ScrapingService.scrape_one's existing production_company_id stamping path
  applies on top of these per-venue Shows because the stamp comes from the
  proxy Club (carries _production_company_id), not from each Show's own club_id.
"""

import importlib.util
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.core.entities.production_company.model import ProductionCompany
from laughtrack.core.entities.show.model import Show
from laughtrack.core.services.scraping import (
    _build_synthetic_proxy_for_company,
    _extract_eventbrite_organizer_id,
)
from laughtrack.scrapers.implementations.api.eventbrite.scraper import EventbriteScraper


_ENCORE_ORGANIZER_URL = "https://www.eventbrite.com/o/encore-comedy/72313162423/"


def _encore_company() -> ProductionCompany:
    return ProductionCompany(
        id=4,
        name="Encore Comedy",
        slug="encore-comedy",
        scraping_url=_ENCORE_ORGANIZER_URL,
        website="https://encorecomedyshows.com/home/",
        visible=True,
        show_name_keywords=[],
        venue_club_ids=[],
    )


def _api_venue(venue_id: str, name: str, city: str, region: str, postal: str = "23832"):
    """Duck-typed Eventbrite API venue (mirrors EventbriteVenue + EventbriteAddress)."""
    address = MagicMock()
    address.address_1 = "11500 Iron Bridge Rd"
    address.city = city
    address.region = region
    address.postal_code = postal

    venue = MagicMock()
    venue.id = venue_id
    venue.name = name
    venue.address = address
    return venue


def _domain_event(name: str, url: str, api_venue) -> EventbriteEvent:
    """Build a domain EventbriteEvent the way from_api_model would, so to_show
    has the structured venue fields and the _api_venue reference set."""
    return EventbriteEvent(
        name=name,
        event_url=url,
        start_date="2026-06-15T23:00:00Z",
        description="Live stand-up at Bull Pen Tap House",
        location_name=api_venue.name,
        location_address=", ".join(
            p for p in [api_venue.address.address_1, api_venue.address.city, api_venue.address.region] if p
        ),
        venue_id=api_venue.id,
        venue_city=api_venue.address.city,
        venue_state=api_venue.address.region,
        venue_zip=api_venue.address.postal_code,
        data_source_type="api",
        _api_venue=api_venue,
    )


def _fake_venue_club(club_id: int, name: str, city: str, state: str) -> Club:
    """The shape ClubHandler.upsert_for_eventbrite_venue would return."""
    club = Club(
        id=club_id,
        name=name,
        address="11500 Iron Bridge Rd",
        website="",
        popularity=0,
        zip_code="23832",
        phone_number="",
        visible=True,
        city=city,
        state=state,
        timezone="America/New_York",
    )
    club.scraping_sources = [
        ScrapingSource(
            id=club_id,
            club_id=club_id,
            platform="eventbrite",
            scraper_key="eventbrite",
            source_url="https://www.eventbrite.com",
            external_id=str(int(club_id) * 100),
        )
    ]
    return club


# ---------------------------------------------------------------------------
# _extract_eventbrite_organizer_id
# ---------------------------------------------------------------------------


def test_extract_organizer_id_handles_path_segment_form():
    assert (
        _extract_eventbrite_organizer_id(_ENCORE_ORGANIZER_URL) == "72313162423"
    )


def test_extract_organizer_id_handles_slug_suffix_form():
    # Improbable Comedy uses the legacy /o/<slug>-<id> shape (production_companies id=2).
    assert (
        _extract_eventbrite_organizer_id(
            "https://www.eventbrite.com/o/improbable-comedy-10899180919"
        )
        == "10899180919"
    )


def test_extract_organizer_id_returns_none_for_non_eventbrite_urls():
    assert _extract_eventbrite_organizer_id("") is None
    assert _extract_eventbrite_organizer_id(None) is None
    assert (
        _extract_eventbrite_organizer_id(
            "https://www.etix.com/ticket/v/26727/the-lounge-at-world-stage"
        )
        is None
    )


# ---------------------------------------------------------------------------
# _build_synthetic_proxy_for_company
# ---------------------------------------------------------------------------


def test_synthetic_proxy_carries_eventbrite_source_and_pc_metadata():
    company = _encore_company()
    proxy = _build_synthetic_proxy_for_company(company)
    assert proxy is not None
    # Negative id ensures the synthetic Club is never persisted by ShowService.
    assert proxy.id == -company.id
    # Single Eventbrite scraping_source with the parsed organizer id.
    assert len(proxy.scraping_sources) == 1
    source = proxy.scraping_sources[0]
    assert source.platform == "eventbrite"
    assert source.scraper_key == "eventbrite"
    assert source.external_id == "72313162423"
    assert source.source_url == _ENCORE_ORGANIZER_URL
    # eventbrite_id property resolves through scraping_sources.
    assert proxy.eventbrite_id == "72313162423"
    # production_company_id and ref are tagged so scrape_one can stamp shows.
    assert getattr(proxy, "_production_company_id") == company.id
    assert getattr(proxy, "_production_company") is company


def test_synthetic_proxy_returns_none_when_url_unsupported():
    bad = ProductionCompany(
        id=99,
        name="Unsupported Co",
        slug="unsupported-co",
        scraping_url="https://www.etix.com/ticket/v/12345/some-venue",
    )
    assert _build_synthetic_proxy_for_company(bad) is None


def test_synthetic_proxy_returns_none_for_eventbrite_org_url_without_digits():
    """The ``>=6 digits`` guard in _extract_eventbrite_organizer_id must reject
    Eventbrite ``/o/`` URLs that contain no parseable id, otherwise the
    synthetic proxy would activate organizer mode with an empty external_id and
    the Eventbrite client would issue a malformed ``/organizers//events/`` call."""
    no_id = ProductionCompany(
        id=98,
        name="No-ID Org",
        slug="no-id-org",
        scraping_url="https://www.eventbrite.com/o/some-org",
    )
    assert _build_synthetic_proxy_for_company(no_id) is None
    short_id = ProductionCompany(
        id=97,
        name="Too-Short Org",
        slug="too-short-org",
        scraping_url="https://www.eventbrite.com/o/some-org/12345",
    )
    # Five digits is below the 6-digit minimum the regex enforces.
    assert _build_synthetic_proxy_for_company(short_id) is None


def test_pc_stamp_skips_shows_when_keywords_dont_match():
    """Per-venue Shows from organizer mode must NOT be stamped with
    production_company_id when the company has show_name_keywords AND the
    show name doesn't match. Encore Comedy itself has empty keywords so every
    show matches, but the orchestrator's stamping branch is shared with
    keyword-filtered companies (e.g. Laff House id=1) and the per-venue path
    is new — verify the existing matches_show_name guard still kicks in."""
    company = ProductionCompany(
        id=1,
        name="Laff House",
        slug="laff-house",
        scraping_url=_ENCORE_ORGANIZER_URL,
        show_name_keywords=["comedy", "stand-up", "improv"],
    )
    proxy = _build_synthetic_proxy_for_company(company)
    assert proxy is not None

    show_date = datetime(2026, 6, 15, 23, 0, tzinfo=timezone.utc)
    matching = Show(
        name="Stand-up Comedy Night",
        club_id=2001,
        date=show_date,
        show_page_url="",
        lineup=[],
        tickets=[],
    )
    non_matching = Show(
        name="Karaoke and DJ Set",
        club_id=2002,
        date=show_date,
        show_page_url="",
        lineup=[],
        tickets=[],
    )

    # Mirror the stamping branch in ScrapingService.scrape_one.
    for show in (matching, non_matching):
        if company.matches_show_name(show.name):
            show.production_company_id = company.id

    assert matching.production_company_id == company.id
    # The non-matching show keeps production_company_id unset, which is the
    # whole point of the keyword filter — it would otherwise be stamped onto
    # an unrelated event surfaced by the same per-venue scrape.
    assert non_matching.production_company_id is None


# ---------------------------------------------------------------------------
# EventbriteScraper organizer-mode end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_organizer_mode_routes_each_event_to_its_own_venue_club():
    """The Encore organizer feed has events at distinct venues; each Show's
    club_id must point at the per-venue clubs row, not at the synthetic proxy."""
    proxy = _build_synthetic_proxy_for_company(_encore_company())
    assert proxy is not None

    bull_pen = _api_venue(
        venue_id="V_BULL_PEN", name="Bull Pen Tap House", city="Chesterfield", region="VA"
    )
    silver_diner = _api_venue(
        venue_id="V_SILVER", name="Silver Diner", city="Cabin John", region="MD", postal="20818"
    )

    api_events = [
        _domain_event(
            name="Encore Comedy at Bull Pen Tap House",
            url="https://www.eventbrite.com/e/bull-pen-1",
            api_venue=bull_pen,
        ),
        _domain_event(
            name="Encore Comedy at Bull Pen Tap House (late show)",
            url="https://www.eventbrite.com/e/bull-pen-2",
            api_venue=bull_pen,
        ),
        _domain_event(
            name="Encore Comedy at Silver Diner",
            url="https://www.eventbrite.com/e/silver-1",
            api_venue=silver_diner,
        ),
    ]

    bull_pen_club = _fake_venue_club(1001, "Bull Pen Tap House", "Chesterfield", "VA")
    silver_club = _fake_venue_club(1002, "Silver Diner", "Cabin John", "MD")

    def _upsert(api_venue):
        if api_venue.id == "V_BULL_PEN":
            return bull_pen_club
        if api_venue.id == "V_SILVER":
            return silver_club
        return None

    scraper = EventbriteScraper(proxy)
    assert scraper._is_organizer_mode is True

    with patch.object(
        scraper.eventbrite_client, "fetch_all_events", new=AsyncMock(return_value=api_events)
    ), patch.object(
        scraper._club_handler, "upsert_for_eventbrite_venue", side_effect=_upsert
    ) as upsert_mock:
        shows = await scraper.scrape_async()

    # One upsert per distinct venue (not per event).
    assert upsert_mock.call_count == 2

    # One Show per event, each carrying the per-venue club_id (NOT the proxy id).
    assert len(shows) == 3
    assert all(isinstance(s, Show) for s in shows)

    bull_pen_shows = [s for s in shows if s.club_id == bull_pen_club.id]
    silver_shows = [s for s in shows if s.club_id == silver_club.id]
    assert len(bull_pen_shows) == 2
    assert len(silver_shows) == 1
    # Sanity: the synthetic proxy id never leaks into a persisted Show.
    assert all(s.club_id > 0 for s in shows)

    # Event identity and venue-level location data are preserved on the Show.
    silver_show = silver_shows[0]
    assert silver_show.name == "Encore Comedy at Silver Diner"
    assert silver_show.show_page_url == "https://www.eventbrite.com/e/silver-1"


@pytest.mark.asyncio
async def test_organizer_mode_skips_events_with_missing_venue():
    """Events without expanded venue data (rare API edge case) are dropped with
    a warning rather than crashing the scrape."""
    proxy = _build_synthetic_proxy_for_company(_encore_company())
    assert proxy is not None

    bull_pen = _api_venue(
        venue_id="V_BULL_PEN", name="Bull Pen Tap House", city="Chesterfield", region="VA"
    )
    good = _domain_event(
        name="Encore at Bull Pen", url="https://www.eventbrite.com/e/bull-pen-3", api_venue=bull_pen
    )
    orphan = EventbriteEvent(
        name="Orphan event",
        event_url="https://www.eventbrite.com/e/orphan",
        start_date="2026-06-15T23:00:00Z",
        data_source_type="api",
        _api_venue=None,
    )

    bull_pen_club = _fake_venue_club(1001, "Bull Pen Tap House", "Chesterfield", "VA")

    scraper = EventbriteScraper(proxy)
    with patch.object(
        scraper.eventbrite_client, "fetch_all_events", new=AsyncMock(return_value=[good, orphan])
    ), patch.object(
        scraper._club_handler, "upsert_for_eventbrite_venue", return_value=bull_pen_club
    ):
        shows = await scraper.scrape_async()

    assert len(shows) == 1
    assert shows[0].club_id == bull_pen_club.id
    assert shows[0].name == "Encore at Bull Pen"


@pytest.mark.asyncio
async def test_organizer_mode_skips_venue_when_upsert_fails():
    """A DB error upserting one venue's club must not drop other venues' shows."""
    proxy = _build_synthetic_proxy_for_company(_encore_company())
    assert proxy is not None

    bull_pen = _api_venue(
        venue_id="V_BULL_PEN", name="Bull Pen Tap House", city="Chesterfield", region="VA"
    )
    silver = _api_venue(
        venue_id="V_SILVER", name="Silver Diner", city="Cabin John", region="MD", postal="20818"
    )
    api_events = [
        _domain_event("Bull Pen show", "https://www.eventbrite.com/e/1", bull_pen),
        _domain_event("Silver show", "https://www.eventbrite.com/e/2", silver),
    ]

    bull_pen_club = _fake_venue_club(1001, "Bull Pen Tap House", "Chesterfield", "VA")

    def _upsert(api_venue):
        if api_venue.id == "V_BULL_PEN":
            return bull_pen_club
        raise RuntimeError("transient DB failure")

    scraper = EventbriteScraper(proxy)
    with patch.object(
        scraper.eventbrite_client, "fetch_all_events", new=AsyncMock(return_value=api_events)
    ), patch.object(
        scraper._club_handler, "upsert_for_eventbrite_venue", side_effect=_upsert
    ):
        shows = await scraper.scrape_async()

    # The successful venue still produces a show.
    assert len(shows) == 1
    assert shows[0].club_id == bull_pen_club.id


@pytest.mark.asyncio
async def test_single_venue_mode_falls_through_to_standard_pipeline():
    """When the source URL has no eventbrite.com/o/ segment, scrape_async defers
    to BaseScraper so single-venue scrapes keep their existing behavior (no
    per-event upsert)."""
    venue_club = Club(
        id=42,
        name="Single Venue",
        address="",
        website="",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )
    venue_only = ScrapingSource(
        platform="eventbrite",
        scraper_key="eventbrite",
        source_url="https://www.eventbrite.com/_internal/venue/page",
        external_id="VENUE123",
    )
    venue_club.scraping_sources = [venue_only]
    venue_club.activate_scraping_source(venue_only)

    scraper = EventbriteScraper(venue_club)
    assert scraper._is_organizer_mode is False
    # We don't run the full base pipeline here (it would hit the network); we
    # only assert routing chooses BaseScraper.scrape_async over the organizer
    # branch by stubbing out super().scrape_async().
    with patch(
        "laughtrack.scrapers.implementations.api.eventbrite.scraper.BaseScraper.scrape_async",
        new=AsyncMock(return_value=[]),
    ) as base_call:
        result = await scraper.scrape_async()
    assert result == []
    base_call.assert_awaited_once()


# ---------------------------------------------------------------------------
# Production-company stamping (verifies the orchestrator's existing pc_id stamp
# applies cleanly to per-venue Shows produced in organizer mode)
# ---------------------------------------------------------------------------


def test_production_company_stamp_applies_to_per_venue_shows():
    """ScrapingService.scrape_one stamps production_company_id on every show in
    a result based on the proxy Club's _production_company_id, regardless of
    each Show's own club_id. Verifying that here without the orchestrator
    machinery: a synthetic proxy carries the tag, per-venue Shows carry their
    venue club_id, and the stamp is applied uniformly."""
    company = _encore_company()
    proxy = _build_synthetic_proxy_for_company(company)
    assert proxy is not None

    bull_pen_club = _fake_venue_club(1001, "Bull Pen Tap House", "Chesterfield", "VA")
    silver_club = _fake_venue_club(1002, "Silver Diner", "Cabin John", "MD")
    show_date = datetime(2026, 6, 15, 23, 0, tzinfo=timezone.utc)
    shows = [
        Show(name="Bull Pen show", club_id=bull_pen_club.id, date=show_date, show_page_url="", lineup=[], tickets=[]),
        Show(name="Silver Diner show", club_id=silver_club.id, date=show_date, show_page_url="", lineup=[], tickets=[]),
    ]

    pc_id = getattr(proxy, "_production_company_id", None)
    pc = getattr(proxy, "_production_company", None)
    assert pc_id == company.id
    assert pc is company

    # Mirror the stamping branch in ScrapingService.scrape_one.
    for show in shows:
        if pc is None or pc.matches_show_name(show.name):
            show.production_company_id = pc_id

    # Every show is tagged regardless of the venue it points at.
    assert shows[0].production_company_id == company.id
    assert shows[1].production_company_id == company.id
    # Per-venue club_ids are preserved (not overwritten by the proxy id).
    assert shows[0].club_id == bull_pen_club.id
    assert shows[1].club_id == silver_club.id
