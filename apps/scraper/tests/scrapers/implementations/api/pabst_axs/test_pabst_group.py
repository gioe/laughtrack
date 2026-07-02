from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.pabst_axs.group_scraper import (
    PabstTheaterGroupScraper,
)


_EVENTS_HTML = """
<html><body>
<div class="eventItem">
    <a href="https://www.pabsttheatergroup.com/events/detail/steve-hofstetter-2026"
       title="More Info for Steve Hofstetter">
        <img src="https://www.pabsttheatergroup.com/assets/img/2026.07.03-V-Steve-Hofstetter.png" />
    </a>
    <a href="https://www.axs.com/events/1049284/steve-hofstetter-tickets?skin=pabst"
       title="Buy Tickets for Steve Hofstetter">Buy</a>
    <a href="https://www.pabsttheatergroup.com/venues/detail/vivarium"
       class="location" title="Vivarium link">Vivarium</a>
</div>
<div class="eventItem">
    <a href="https://www.pabsttheatergroup.com/events/detail/elmiene-2026"
       title="More Info for Elmiene">
        <img src="https://www.pabsttheatergroup.com/assets/img/2026.07.09-T-Elmiene.png" />
    </a>
    <a href="https://www.axs.com/events/1395560/elmiene-tickets?skin=pabst"
       title="Buy Tickets for Elmiene">Buy</a>
    <a href="https://www.pabsttheatergroup.com/venues/detail/turner-hall-ballroom"
       class="location" title="Turner Hall Ballroom link">Turner Hall Ballroom</a>
</div>
</body></html>
"""

_NEXT_PAGE_HTML = """
<html><body>
<div class="eventItem">
    <a href="https://www.pabsttheatergroup.com/events/detail/anthony-jeselnik-2026"
       title="More Info for Anthony Jeselnik">
        <img src="https://www.pabsttheatergroup.com/assets/img/2026.11.13-R-Anthony-Jeselnik.png" />
    </a>
    <a href="https://www.axs.com/events/1395577/anthony-jeselnik-tickets?skin=pabst"
       title="Buy Tickets for Anthony Jeselnik">Buy</a>
    <a href="https://www.pabsttheatergroup.com/venues/detail/the-riverside-theater"
       class="location" title="The Riverside Theater link">The Riverside Theater</a>
</div>
</body></html>
"""


def _operator_proxy(metadata=None) -> Club:
    source = ScrapingSource(
        id=9,
        platform="custom",
        scraper_key="pabst_theater_group",
        source_url="https://www.pabsttheatergroup.com/events",
        source_target_id=4,
        source_target_name="Pabst Theater Group",
        source_target_slug="pabst-theater-group",
        source_target_type="operator",
        metadata=metadata or {},
    )
    club = Club(
        id=4,
        name="Pabst Theater Group",
        address="",
        website="https://www.pabsttheatergroup.com/events",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=False,
        timezone="America/Chicago",
        club_type="source_target",
        scraping_sources=[source],
        active_scraping_source=source,
        is_synthetic=True,
    )
    return club


def _venue_club(venue: dict) -> Club:
    return Club(
        id={"Vivarium": 9101, "Turner Hall Ballroom": 9120, "The Riverside Theater": 9123}[venue["name"]],
        name=venue["name"],
        address=venue.get("address", ""),
        website=venue.get("website", ""),
        popularity=0,
        zip_code=venue.get("zip_code", ""),
        phone_number="",
        visible=True,
        timezone=venue.get("timezone") or "America/Chicago",
        city=venue.get("city"),
        state=venue.get("state"),
        club_type="venue",
    )


def test_resolver_discovers_pabst_theater_group_scraper():
    assert ScraperResolver().get("pabst_theater_group") is PabstTheaterGroupScraper


@pytest.mark.asyncio
async def test_scrape_routes_each_event_to_its_physical_venue(monkeypatch):
    scraper = PabstTheaterGroupScraper(_operator_proxy())
    scraper.fetch_html = AsyncMock(return_value=_EVENTS_HTML)
    scraper.fetch_json = AsyncMock(return_value="")
    monkeypatch.setattr(scraper._club_handler, "upsert_discovered_venue", _venue_club)

    shows = await scraper.scrape_async()

    assert len(shows) == 2
    assert {show.name: show.club_id for show in shows} == {
        "Steve Hofstetter": 9101,
        "Elmiene": 9120,
    }


@pytest.mark.asyncio
async def test_scrape_walks_load_more_pages(monkeypatch):
    scraper = PabstTheaterGroupScraper(_operator_proxy())
    scraper.fetch_html = AsyncMock(return_value=_EVENTS_HTML)
    scraper.fetch_json = AsyncMock(side_effect=[_NEXT_PAGE_HTML, ""])
    monkeypatch.setattr(scraper._club_handler, "upsert_discovered_venue", _venue_club)

    shows = await scraper.scrape_async()

    assert {show.name for show in shows} == {"Steve Hofstetter", "Elmiene", "Anthony Jeselnik"}
    assert scraper.fetch_json.await_count == 1
    assert scraper.fetch_json.await_args_list[0].args[0] == (
        "https://www.pabsttheatergroup.com/events/events_ajax/12"
        "?category=0&venue=0&team=0&per_page=12&came_from_page=event-list-page"
    )


@pytest.mark.asyncio
async def test_comedy_filter_runs_before_venue_upsert(monkeypatch):
    scraper = PabstTheaterGroupScraper(
        _operator_proxy(metadata={"comedy_filter": True, "comedy_title_allowlist": ["steve hofstetter"]})
    )
    scraper.fetch_html = AsyncMock(return_value=_EVENTS_HTML)
    scraper.fetch_json = AsyncMock(return_value="")
    scraper._lineup_handler = MagicMock()
    scraper._lineup_handler.get_comedians_from_show_names.return_value = {}
    scraper._comedian_handler = MagicMock()
    scraper._comedian_handler.get_stored_popularity_by_names.return_value = {}
    upsert = MagicMock(side_effect=_venue_club)
    monkeypatch.setattr(scraper._club_handler, "upsert_discovered_venue", upsert)

    shows = await scraper.scrape_async()

    assert [show.name for show in shows] == ["Steve Hofstetter"]
    upsert.assert_called_once()
    assert upsert.call_args.args[0]["name"] == "Vivarium"
