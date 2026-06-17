"""Tests for Upright Citizens Brigade's WP Grid Builder scraper."""

from unittest.mock import AsyncMock

import pytz

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.ucb import UCBEvent
from laughtrack.scrapers.implementations.venues.ucb.extractor import UCBExtractor
from laughtrack.scrapers.implementations.venues.ucb.scraper import UCBScraper


HTML = """
<div class="wp-grid-builder">
  <article class="wpgb-card ucb-card wpgb-post-1 la-franklin online">
    <div class="wpgb-block event-post-date">Wednesday, June 17, 2026 @ 7:00 PM</div>
    <div class="wpgb-block ucb-event-post-location">
      <span class="wpgb-block-term" data-id="65">LA - FRANKLIN</span>
      <span class="wpgb-block-term" data-id="67">Livestream</span>
    </div>
    <h3 class="wpgb-block ucb-event-post-title">
      <a href="https://ucbcomedy.com/show/franklin-show/">Franklin Show</a>
    </h3>
    <div class="wpgb-block ucb-event-post-excerpt"><p>A Franklin description.</p></div>
    <div class="wpgb-block ucb-buy-now">
      <a href="https://ucbcomedy.com/show/franklin-show/" aria-label="Buy Now">Buy Now</a>
    </div>
  </article>
  <article class="wpgb-card ucb-card wpgb-post-2 la-annex">
    <div class="wpgb-block event-post-date">Thursday, June 18, 2026 @ 8:00 PM</div>
    <div class="wpgb-block ucb-event-post-location">
      <span class="wpgb-block-term" data-id="64">LA - ANNEX</span>
    </div>
    <h3 class="wpgb-block ucb-event-post-title">
      <a href="/show/annex-show/">Annex Show</a>
    </h3>
    <div class="wpgb-block ucb-buy-now">
      <a href="/show/annex-show/" aria-label="Read more">Read more</a>
    </div>
  </article>
  <article class="wpgb-card ucb-card wpgb-post-3 la-franklin">
    <div class="wpgb-block event-post-date">Friday, June 12 - Sunday, June 14, 2026</div>
    <div class="wpgb-block ucb-event-post-location">
      <span class="wpgb-block-term" data-id="65">LA - FRANKLIN</span>
    </div>
    <h3 class="wpgb-block ucb-event-post-title"><a href="/show/festival/">Festival</a></h3>
  </article>
</div>
"""


def _make_club(location_slug="la-franklin"):
    source = ScrapingSource(
        id=1,
        club_id=8834,
        platform="custom",
        scraper_key="ucb",
        source_url="https://ucbcomedy.com/shows/",
        metadata={"location_slug": location_slug},
    )
    club = Club(
        id=8834,
        name="Upright Citizens Brigade Theatre",
        address="5919 Franklin Ave",
        website="https://ucbcomedy.com",
        popularity=0,
        zip_code="90028",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
        city="Los Angeles",
        state="CA",
        scraping_sources=[source],
        active_scraping_source=source,
    )
    return club


class TestUCBExtractor:
    def test_filters_to_requested_location_and_skips_date_ranges(self):
        events = UCBExtractor.extract_events(
            HTML,
            source_url="https://ucbcomedy.com/shows/",
            location_slug="la-franklin",
        )

        assert [event.title for event in events] == ["Franklin Show"]
        assert events[0].location_name == "LA - FRANKLIN"
        assert events[0].ticket_url == "https://ucbcomedy.com/show/franklin-show/"

    def test_supports_relative_urls(self):
        events = UCBExtractor.extract_events(
            HTML,
            source_url="https://ucbcomedy.com/shows/",
            location_slug="la-annex",
        )

        assert [event.title for event in events] == ["Annex Show"]
        assert events[0].show_page_url == "https://ucbcomedy.com/show/annex-show/"


class TestUCBEvent:
    def test_to_show_localizes_to_club_timezone(self):
        event = UCBEvent(
            title="Franklin Show",
            date_text="Wednesday, June 17, 2026 @ 7:00 PM",
            show_page_url="https://ucbcomedy.com/show/franklin-show/",
            ticket_url="https://ucbcomedy.com/show/franklin-show/",
            location_slug="la-franklin",
            location_name="LA - FRANKLIN",
            description="A Franklin description.",
        )

        show = event.to_show(_make_club())

        assert show is not None
        local = show.date.astimezone(pytz.timezone("America/Los_Angeles"))
        assert (local.year, local.month, local.day, local.hour, local.minute) == (2026, 6, 17, 19, 0)
        assert show.room == "LA - FRANKLIN"
        assert show.tickets[0].price is None


class TestUCBScraper:
    async def test_builds_location_filtered_target(self):
        scraper = UCBScraper(_make_club("la-franklin"))

        targets = await scraper.collect_scraping_targets()

        assert targets == ["https://ucbcomedy.com/shows/?_filter_locations=la-franklin"]

    async def test_get_data_extracts_configured_location(self):
        scraper = UCBScraper(_make_club("la-annex"))
        scraper.fetch_html = AsyncMock(return_value=HTML)

        page = await scraper.get_data("https://ucbcomedy.com/shows/?_filter_locations=la-annex")

        assert page is not None
        assert [event.title for event in page.event_list] == ["Annex Show"]
