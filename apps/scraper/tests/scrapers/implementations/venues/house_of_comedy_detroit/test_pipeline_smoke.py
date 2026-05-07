"""Tests for Detroit House of Comedy WordPress AJAX scraper."""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.house_of_comedy_detroit.scraper import (
    HouseOfComedyDetroitScraper,
)
from laughtrack.scrapers.implementations.venues.house_of_comedy_phoenix.data import (
    HouseOfComedyPhoenixPageData,
)
from laughtrack.scrapers.implementations.venues.house_of_comedy_phoenix.extractor import (
    HouseOfComedyPhoenixExtractor,
)


_SOURCE_URL = "https://detroit.houseofcomedy.net/upcoming-comedy-shows/"
_AJAX_URL = "https://detroit.houseofcomedy.net/wp-admin/admin-ajax.php"
_SAMPLE_HTML = """
<div class='grid-view-comedy_show_item for_grid'>
  <p class='grid-view-event-date'>Tue <span>12</span></p>
  <a href='https://detroit.houseofcomedy.net/events/tune-up-tuesdays-176/'>
    <img class='grid-view-show_img' alt='Tune Up Tuesdays'>
  </a>
  <div class='grid-view-upcoming_details_warpper'>
    <h4 class='grid-view-comedy_show_title'><span>Tune Up Tuesdays</span></h4>
    <div class='grid-view-parent_time multiple_swap Tune_Up_Tuesdays'>
      <a href='https://detroit.houseofcomedy.net/events/tune-up-tuesdays-176/'>
        <span class='grid-view-times'>07:30 PM</span>
      </a>
    </div>
  </div>
  <a href='https://detroit.houseofcomedy.net/events/tune-up-tuesdays-176/' class='grid-view-buy_ticket_btn'>Buy Tickets</a>
</div>
"""


def _club() -> Club:
    club = Club(
        id=602,
        name="Detroit House of Comedy",
        address="2301 Woodward Ave",
        website="https://detroit.houseofcomedy.net/",
        popularity=0,
        zip_code="48201",
        phone_number="",
        visible=True,
        timezone="America/Detroit",
    )
    club.active_scraping_source = ScrapingSource(
        id=602,
        club_id=club.id,
        platform="custom",
        scraper_key="house_of_comedy_detroit",
        source_url=_SOURCE_URL,
        metadata={"ajax_url": _AJAX_URL},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_extractor_parses_detroit_grid_event_links():
    events = HouseOfComedyPhoenixExtractor.extract_events(
        _SAMPLE_HTML,
        year=2026,
        month=5,
        source_url=_SOURCE_URL,
    )

    assert [(event.title, event.date, event.time) for event in events] == [
        ("Tune Up Tuesdays", "2026-05-12", "7:30 PM"),
    ]
    assert events[0].ticket_url == "https://detroit.houseofcomedy.net/events/tune-up-tuesdays-176/"


@pytest.mark.asyncio
async def test_get_data_posts_to_detroit_wordpress_ajax(monkeypatch):
    scraper = HouseOfComedyDetroitScraper(_club())

    async def fake_post_form(self, url: str, data, **kwargs):
        assert url == _AJAX_URL
        assert data["action"] == "get_comedy_shows"
        assert data["month"] == 5
        assert data["year"] == 2026
        assert data["per_page"] == -1
        return _SAMPLE_HTML

    monkeypatch.setattr(HouseOfComedyDetroitScraper, "post_form", fake_post_form)

    result = await scraper.get_data("2026-05")

    assert isinstance(result, HouseOfComedyPhoenixPageData)
    assert len(result.event_list) == 1
