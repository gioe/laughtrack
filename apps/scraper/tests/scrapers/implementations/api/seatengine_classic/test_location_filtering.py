"""
Tests for seatengine_classic location label extraction and filtering.

Covers:
  - SeatEngineClassicExtractor._location_labels() — event-label span extraction
  - SeatEngineClassicScraper._parse_location_filter() — #location= fragment parsing
  - SeatEngineClassicScraper.get_data() — location-based show filtering
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

from laughtrack.scrapers.implementations.api.seatengine_classic.extractor import (
    SeatEngineClassicExtractor,
)

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.seatengine_classic.scraper import SeatEngineClassicScraper
from laughtrack.scrapers.implementations.api.seatengine_classic.data import SeatEngineClassicPageData


BASE_URL = "https://example.seatengine.com"
SCRAPING_URL = f"{BASE_URL}/events"


def _club(scraping_url: str = SCRAPING_URL) -> Club:
    _c = Club(id=999, name='Test Venue', address='123 Main St', website='https://example.com', popularity=0, zip_code='00000', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=scraping_url, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _html_with_labels(*labels: str, event_name: str = "Comedy Night") -> str:
    """Build Layout 2 HTML with optional event-labels div."""
    labels_html = ""
    if labels:
        spans = "".join(f'<span class="event-label">{lbl}</span>' for lbl in labels)
        labels_html = f'<div class="event-labels">{spans}</div>'
    return f"""
    <html><body>
    <div class="event-list-item">
      <h3 class="el-header"><a href="/events/1">{event_name}</a></h3>
      {labels_html}
      <h6 class="event-date">Thu Mar 26 2026, 7:30 PM</h6>
      <a class="btn btn-primary" href="/shows/100">Buy Tickets</a>
    </div>
    </body></html>
    """


def _multi_location_html() -> str:
    """Two events: one labelled 'Downtown', the other 'Uptown'."""
    return """
    <html><body>
    <div class="event-list-item">
      <h3 class="el-header"><a href="/events/1">Downtown Show</a></h3>
      <div class="event-labels"><span class="event-label">Downtown</span></div>
      <h6 class="event-date">Fri Mar 27 2026, 8:00 PM</h6>
      <a class="btn btn-primary" href="/shows/200">Buy Tickets</a>
    </div>
    <div class="event-list-item">
      <h3 class="el-header"><a href="/events/2">Uptown Show</a></h3>
      <div class="event-labels"><span class="event-label">Uptown</span></div>
      <h6 class="event-date">Sat Mar 28 2026, 9:00 PM</h6>
      <a class="btn btn-primary" href="/shows/201">Buy Tickets</a>
    </div>
    </body></html>
    """


# ---------------------------------------------------------------------------
# _location_labels() — extracts event-label spans from HTML
# ---------------------------------------------------------------------------


class TestLocationLabels:
    """Tests for SeatEngineClassicExtractor._location_labels()."""

    def test_extracts_single_label(self):
        html = _html_with_labels("Downtown")
        shows = SeatEngineClassicExtractor.extract_shows(html, BASE_URL)
        assert len(shows) == 1
        assert shows[0]["location_labels"] == ["Downtown"]

    def test_extracts_multiple_labels(self):
        html = _html_with_labels("Downtown", "Main Stage")
        shows = SeatEngineClassicExtractor.extract_shows(html, BASE_URL)
        assert shows[0]["location_labels"] == ["Downtown", "Main Stage"]

    def test_no_labels_div_omits_key(self):
        html = _html_with_labels()  # no labels
        shows = SeatEngineClassicExtractor.extract_shows(html, BASE_URL)
        assert len(shows) == 1
        assert "location_labels" not in shows[0]

    def test_empty_span_text_is_skipped(self):
        html = """
        <html><body>
        <div class="event-list-item">
          <h3 class="el-header"><a href="/events/1">Show</a></h3>
          <div class="event-labels">
            <span class="event-label">Downtown</span>
            <span class="event-label">  </span>
            <span class="event-label"></span>
          </div>
          <h6 class="event-date">Thu Mar 26 2026, 7:30 PM</h6>
          <a class="btn btn-primary" href="/shows/100">Buy Tickets</a>
        </div>
        </body></html>
        """
        shows = SeatEngineClassicExtractor.extract_shows(html, BASE_URL)
        assert shows[0]["location_labels"] == ["Downtown"]


# ---------------------------------------------------------------------------
# _parse_location_filter() — parses #location= fragments
# ---------------------------------------------------------------------------


class TestParseLocationFilter:
    """Tests for SeatEngineClassicScraper._parse_location_filter()."""

    def test_extracts_location_from_fragment(self):
        result = SeatEngineClassicScraper._parse_location_filter(
            "https://example.com/events#location=Downtown"
        )
        assert result == "Downtown"

    def test_decodes_url_encoded_fragment(self):
        result = SeatEngineClassicScraper._parse_location_filter(
            "https://example.com/events#location=6th%20and%20Proctor"
        )
        assert result == "6th and Proctor"

    def test_returns_none_without_fragment(self):
        result = SeatEngineClassicScraper._parse_location_filter(
            "https://example.com/events"
        )
        assert result is None

    def test_returns_none_for_non_location_fragment(self):
        result = SeatEngineClassicScraper._parse_location_filter(
            "https://example.com/events#section=comedy"
        )
        assert result is None

    def test_strips_whitespace(self):
        result = SeatEngineClassicScraper._parse_location_filter(
            "https://example.com/events#location=%20Downtown%20"
        )
        assert result == "Downtown"

    def test_empty_location_value_returns_falsy(self):
        """Empty #location= returns a falsy value (won't trigger filtering)."""
        result = SeatEngineClassicScraper._parse_location_filter(
            "https://example.com/events#location="
        )
        assert not result


# ---------------------------------------------------------------------------
# get_data() — filters shows by location label when filter is set
# ---------------------------------------------------------------------------


class TestGetDataLocationFiltering:
    """Tests for location filtering in SeatEngineClassicScraper.get_data()."""

    @pytest.mark.asyncio
    async def test_filters_shows_by_location_label(self):
        scraper = SeatEngineClassicScraper(
            _club(f"{SCRAPING_URL}#location=Downtown")
        )
        scraper.fetch_html = AsyncMock(return_value=_multi_location_html())

        result = await scraper.get_data(SCRAPING_URL)

        assert isinstance(result, SeatEngineClassicPageData)
        assert len(result.event_list) == 1
        assert result.event_list[0]["name"] == "Downtown Show"

    @pytest.mark.asyncio
    async def test_filter_is_case_insensitive(self):
        scraper = SeatEngineClassicScraper(
            _club(f"{SCRAPING_URL}#location=downtown")
        )
        scraper.fetch_html = AsyncMock(return_value=_multi_location_html())

        result = await scraper.get_data(SCRAPING_URL)

        assert len(result.event_list) == 1
        assert result.event_list[0]["name"] == "Downtown Show"

    @pytest.mark.asyncio
    async def test_no_filter_returns_all_shows(self):
        scraper = SeatEngineClassicScraper(_club())
        scraper.fetch_html = AsyncMock(return_value=_multi_location_html())

        result = await scraper.get_data(SCRAPING_URL)

        assert len(result.event_list) == 2

    @pytest.mark.asyncio
    async def test_filter_with_no_matching_shows_returns_empty(self):
        scraper = SeatEngineClassicScraper(
            _club(f"{SCRAPING_URL}#location=Midtown")
        )
        scraper.fetch_html = AsyncMock(return_value=_multi_location_html())

        result = await scraper.get_data(SCRAPING_URL)

        assert isinstance(result, SeatEngineClassicPageData)
        assert result.event_list == []

    @pytest.mark.asyncio
    async def test_filter_matches_substring_in_label(self):
        """Filter 'Down' should match label 'Downtown'."""
        scraper = SeatEngineClassicScraper(
            _club(f"{SCRAPING_URL}#location=Down")
        )
        scraper.fetch_html = AsyncMock(return_value=_multi_location_html())

        result = await scraper.get_data(SCRAPING_URL)

        assert len(result.event_list) == 1
        assert result.event_list[0]["name"] == "Downtown Show"

    @pytest.mark.asyncio
    async def test_shows_without_labels_excluded_when_filter_set(self):
        """Shows that have no location_labels are excluded when a filter is active."""
        html = """
        <html><body>
        <div class="event-list-item">
          <h3 class="el-header"><a href="/events/1">Labelled Show</a></h3>
          <div class="event-labels"><span class="event-label">Downtown</span></div>
          <h6 class="event-date">Fri Mar 27 2026, 8:00 PM</h6>
          <a class="btn btn-primary" href="/shows/200">Buy Tickets</a>
        </div>
        <div class="event-list-item">
          <h3 class="el-header"><a href="/events/2">No Label Show</a></h3>
          <h6 class="event-date">Sat Mar 28 2026, 9:00 PM</h6>
          <a class="btn btn-primary" href="/shows/201">Buy Tickets</a>
        </div>
        </body></html>
        """
        scraper = SeatEngineClassicScraper(
            _club(f"{SCRAPING_URL}#location=Downtown")
        )
        scraper.fetch_html = AsyncMock(return_value=html)

        result = await scraper.get_data(SCRAPING_URL)

        assert len(result.event_list) == 1
        assert result.event_list[0]["name"] == "Labelled Show"
