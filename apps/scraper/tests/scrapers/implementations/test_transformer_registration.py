"""
Parameterized test: every venue/API scraper that uses the pipeline must register
exactly one transformer in __init__. National/tour-dates scrapers (which fully
override scrape_async and bypass the pipeline) are excluded.
"""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource

# ---------------------------------------------------------------------------
# Scrapers under test
# ---------------------------------------------------------------------------

from laughtrack.scrapers.implementations.api.eventbrite.scraper import EventbriteScraper
from laughtrack.scrapers.implementations.api.seatengine.scraper import SeatEngineScraper
from laughtrack.scrapers.implementations.api.ticketmaster.scraper import TicketmasterScraper
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper
from laughtrack.scrapers.implementations.venues.broadway_comedy_club.scraper import BroadwayComedyClubScraper
from laughtrack.scrapers.implementations.api.ovationtix.scraper import OvationTixScraper
from laughtrack.scrapers.implementations.api.wix_events.scraper import WixEventsScraper
from laughtrack.scrapers.implementations.api.squadup.scraper import SquadUpScraper
from laughtrack.scrapers.implementations.venues.comedy_cellar.scraper import ComedyCellarScraper
from laughtrack.scrapers.implementations.venues.comedy_key_west.scraper import ComedyKeyWestScraper
from laughtrack.scrapers.implementations.venues.gotham.scraper import GothamComedyClubScraper
from laughtrack.scrapers.implementations.venues.grove_34.scraper import Grove34Scraper
from laughtrack.scrapers.implementations.venues.improv.scraper import ImprovScraper
from laughtrack.scrapers.implementations.venues.rodneys.scraper import RodneysComedyClubScraper
from laughtrack.scrapers.implementations.venues.st_marks.scraper import StMarksScraper
from laughtrack.scrapers.implementations.venues.standup_ny.scraper import StandupNYScraper
from laughtrack.scrapers.implementations.venues.the_stand.scraper import TheStandNYCScraper
from laughtrack.scrapers.implementations.venues.uptown_theater.scraper import UptownTheaterScraper
from laughtrack.scrapers.implementations.venues.west_side.scraper import WestSideScraper

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_LEGACY_KWARGS = ("scraping_url", "scraper", "eventbrite_id", "seatengine_id",
                  "ticketmaster_id", "ovationtix_client_id", "wix_comp_id",
                  "squadup_user_id")


def _base_club(**overrides) -> Club:
    """Return a minimal valid Club stub, optionally overriding fields."""
    defaults = dict(
        id=1,
        name="Test Club",
        address="",
        website="https://example.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )
    legacy = {"scraping_url": "https://example.com/events"}
    for k in _LEGACY_KWARGS:
        if k in overrides:
            legacy[k] = overrides.pop(k)
    defaults.update(overrides)
    club = Club(**defaults)

    # Resolve platform from the external-id legacy kwarg present in `legacy`.
    eventbrite_id = legacy.get("eventbrite_id")
    seatengine_id = legacy.get("seatengine_id")
    ticketmaster_id = legacy.get("ticketmaster_id")
    ovationtix_client_id = legacy.get("ovationtix_client_id")
    wix_comp_id = legacy.get("wix_comp_id")
    squadup_user_id = legacy.get("squadup_user_id")
    scraper = legacy.get("scraper")
    if eventbrite_id is not None:
        platform, external_id = "eventbrite", eventbrite_id
    elif seatengine_id is not None:
        platform = "seatengine_v3" if scraper == "seatengine_v3" else "seatengine"
        external_id = seatengine_id
    elif ticketmaster_id is not None:
        platform, external_id = "ticketmaster", ticketmaster_id
    elif ovationtix_client_id is not None:
        platform, external_id = "ovationtix", ovationtix_client_id
    elif wix_comp_id is not None:
        platform, external_id = "wix_events", wix_comp_id
    elif squadup_user_id is not None:
        platform, external_id = "squadup", squadup_user_id
    elif scraper:
        platform, external_id = scraper, None
    else:
        platform, external_id = "custom", None
    club.active_scraping_source = ScrapingSource(
        id=1, club_id=club.id, platform=platform,
        scraper_key=scraper or "",
        source_url=legacy.get("scraping_url"),
        external_id=external_id,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


# Each entry: (ScraperClass, club_kwargs_overrides)
PIPELINE_SCRAPERS = [
    # API scrapers — each needs the corresponding venue ID
    (EventbriteScraper, {"eventbrite_id": "EB123"}),
    (SeatEngineScraper, {"seatengine_id": "SE123"}),
    (TicketmasterScraper, {"ticketmaster_id": "TM123"}),
    # JSON-LD generic scraper
    (JsonLdScraper, {}),
    # Platform scrapers (consolidated)
    (OvationTixScraper, {"ovationtix_client_id": "12345"}),
    (WixEventsScraper, {"wix_comp_id": "comp-test"}),
    (SquadUpScraper, {"squadup_user_id": "99999"}),
    # Venue-specific scrapers
    (BroadwayComedyClubScraper, {}),
    (ComedyCellarScraper, {}),
    (ComedyKeyWestScraper, {}),
    (GothamComedyClubScraper, {}),
    (Grove34Scraper, {}),
    (ImprovScraper, {}),
    (RodneysComedyClubScraper, {}),
    (StMarksScraper, {}),
    (StandupNYScraper, {}),
    (TheStandNYCScraper, {}),
    (UptownTheaterScraper, {}),
    (WestSideScraper, {}),
]

_ids = [cls.__name__ for cls, _ in PIPELINE_SCRAPERS]

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scraper_cls,club_overrides", PIPELINE_SCRAPERS, ids=_ids)
def test_scraper_registers_exactly_one_transformer(scraper_cls, club_overrides):
    """Each pipeline scraper must register exactly one transformer in __init__."""
    club = _base_club(**club_overrides)
    scraper = scraper_cls(club)
    assert len(scraper.transformation_pipeline.transformers) == 1, (
        f"{scraper_cls.__name__} registered "
        f"{len(scraper.transformation_pipeline.transformers)} transformers — expected 1"
    )
