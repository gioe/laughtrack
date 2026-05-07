"""Tests for Rick Bronson's House of Comedy Phoenix WordPress AJAX scraper."""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.house_of_comedy_phoenix import (
    HouseOfComedyPhoenixEvent,
)
from laughtrack.scrapers.implementations.venues.house_of_comedy_phoenix.data import (
    HouseOfComedyPhoenixPageData,
)
from laughtrack.scrapers.implementations.venues.house_of_comedy_phoenix.extractor import (
    HouseOfComedyPhoenixExtractor,
)
from laughtrack.scrapers.implementations.venues.house_of_comedy_phoenix.scraper import (
    HouseOfComedyPhoenixScraper,
)


_SOURCE_URL = "https://az.houseofcomedy.net/upcoming-comedy-shows/"
_AJAX_URL = "https://az.houseofcomedy.net/wp-admin/admin-ajax.php"
_SAMPLE_HTML = """
<div class="comedy_show_card for_grid">
  <a class="comedy_show_image" href="https://embed.showclix.com/event/k-von-may-15">
    <img src="https://az.houseofcomedy.net/wp-content/uploads/sites/2/2026/05/kvon.jpg">
  </a>
  <h3 class="comedy_show_title">K-von</h3>
  <div class="comedy_show_date">Fri, May 15</div>
  <div class="comedy_show_time">7:30 PM</div>
  <a class="comedy_show_button" href="https://embed.showclix.com/event/k-von-may-15">Get Tickets</a>
</div>
<div class="comedy_show_card for_grid">
  <h3 class="comedy_show_title">K-von</h3>
  <div class="comedy_show_date">Fri, May 15</div>
  <div class="comedy_show_time">9:45 PM</div>
  <a href="https://www.showclix.com/event/k-von-may-15-late">Tickets</a>
</div>
"""


def _club() -> Club:
    club = Club(
        id=601,
        name="Rick Bronson's House of Comedy Phoenix",
        address="5350 E High St #105",
        website="https://az.houseofcomedy.net/",
        popularity=0,
        zip_code="85054",
        phone_number="480-420-3553",
        visible=True,
        timezone="America/Phoenix",
    )
    club.active_scraping_source = ScrapingSource(
        id=601,
        club_id=club.id,
        platform="custom",
        scraper_key="house_of_comedy_phoenix",
        source_url=_SOURCE_URL,
        metadata={"ajax_url": _AJAX_URL},
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_extractor_parses_ajax_showclix_cards():
    events = HouseOfComedyPhoenixExtractor.extract_events(
        _SAMPLE_HTML,
        year=2026,
        source_url=_SOURCE_URL,
    )

    assert [(event.title, event.date, event.time) for event in events] == [
        ("K-von", "2026-05-15", "7:30 PM"),
        ("K-von", "2026-05-15", "9:45 PM"),
    ]
    assert events[0].ticket_url == "https://www.showclix.com/event/k-von-may-15"
    assert events[1].ticket_url == "https://www.showclix.com/event/k-von-may-15-late"


@pytest.mark.asyncio
async def test_get_data_posts_to_wordpress_ajax_and_returns_page_data(monkeypatch):
    scraper = HouseOfComedyPhoenixScraper(_club())

    async def fake_post_form(self, url: str, data, **kwargs):
        assert url == _AJAX_URL
        assert data["action"] == "get_comedy_shows"
        assert data["month"] == 5
        assert data["year"] == 2026
        assert data["per_page"] == -1
        return _SAMPLE_HTML

    monkeypatch.setattr(HouseOfComedyPhoenixScraper, "post_form", fake_post_form)

    result = await scraper.get_data("2026-05")

    assert isinstance(result, HouseOfComedyPhoenixPageData)
    assert len(result.event_list) == 2


@pytest.mark.asyncio
async def test_get_data_returns_none_when_wordpress_ajax_fails(monkeypatch):
    scraper = HouseOfComedyPhoenixScraper(_club())

    async def fake_post_form(self, url: str, data, **kwargs):
        raise RuntimeError("blocked")

    monkeypatch.setattr(HouseOfComedyPhoenixScraper, "post_form", fake_post_form)

    assert await scraper.get_data("2026-05") is None


def test_to_show_sets_phoenix_time_and_showclix_ticket_url():
    event = HouseOfComedyPhoenixEvent(
        title="K-von",
        date="2026-05-15",
        time="7:30 PM",
        ticket_url="https://www.showclix.com/event/k-von-may-15",
        source_url=_SOURCE_URL,
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "K-von"
    assert show.date.year == 2026
    assert show.date.month == 5
    assert show.date.day == 15
    assert show.date.hour == 19
    assert show.date.minute == 30
    assert str(show.date.tzinfo) == "America/Phoenix"
    assert show.show_page_url == "https://www.showclix.com/event/k-von-may-15"
    assert show.tickets[0].purchase_url == "https://www.showclix.com/event/k-von-may-15"
