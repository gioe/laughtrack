"""
Parameterized test: every venue/API scraper that uses the pipeline must register
exactly one transformer in __init__. National/tour-dates scrapers (which fully
override scrape_async and bypass the pipeline) are excluded.
"""

import pytest

from laughtrack.core.entities.club.model import Club

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


def _base_club(**overrides) -> Club:
    """Return a minimal valid Club stub, optionally overriding fields."""
    defaults = dict(
        id=1,
        name="Test Club",
        address="",
        website="https://example.com",
        scraping_url="https://example.com/events",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )
    defaults.update(overrides)
    return Club(**defaults)


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
