"""
Unit tests for ComedyCellarEmailScraper and ComedyCellarEmailExtractor.

Tests use a sample HTML newsletter fixture stored at
tests/fixtures/html/comedy_cellar_email_sample.html.
"""

import pathlib
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.email_show_event import EmailShowEvent
from laughtrack.scrapers.base.email_base_scraper import EmailBaseScraper
from laughtrack.scrapers.implementations.email.comedy_cellar.extractor import (
    ComedyCellarEmailExtractor,
)
from laughtrack.scrapers.implementations.email.comedy_cellar.scraper import (
    ComedyCellarEmailScraper,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FIXTURES_DIR = pathlib.Path(__file__).parents[4] / "fixtures" / "html"


def _load_fixture(name: str) -> str:
    return (_FIXTURES_DIR / name).read_text(encoding="utf-8")


def _make_club() -> Club:
    _c = Club(id=1, name='Comedy Cellar', address='117 MacDougal St, New York, NY 10012', website='https://www.comedycellar.com', popularity=100, zip_code='10012', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='comedycellar.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


# ---------------------------------------------------------------------------
# Scraper class-attribute tests
# ---------------------------------------------------------------------------


class TestComedyCellarEmailScraperAttributes:
    def test_key(self):
        assert ComedyCellarEmailScraper.key == "comedy_cellar_email"

    def test_sender_domain(self):
        assert ComedyCellarEmailScraper.sender_domain == "comedycellar.com"

    def test_inherits_from_email_base_scraper(self):
        assert issubclass(ComedyCellarEmailScraper, EmailBaseScraper)


# ---------------------------------------------------------------------------
# parse_email_html — integration with extractor
# ---------------------------------------------------------------------------


class TestComedyCellarEmailScraperParseEmailHtml:
    def _make_scraper(self) -> ComedyCellarEmailScraper:
        club = _make_club()
        scraper = ComedyCellarEmailScraper.__new__(ComedyCellarEmailScraper)
        scraper._club = club
        scraper.logger_context = {}
        return scraper

    def test_returns_list_of_email_show_events(self):
        scraper = self._make_scraper()
        html = _load_fixture("comedy_cellar_email_sample.html")
        events = scraper.parse_email_html(html, "Upcoming Shows", datetime.now(timezone.utc))
        assert isinstance(events, list)
        assert all(isinstance(e, EmailShowEvent) for e in events)

    def test_parses_two_shows_from_fixture(self):
        scraper = self._make_scraper()
        html = _load_fixture("comedy_cellar_email_sample.html")
        events = scraper.parse_email_html(html, "Upcoming Shows", datetime.now(timezone.utc))
        assert len(events) == 2

    def test_headliner_names_extracted(self):
        scraper = self._make_scraper()
        html = _load_fixture("comedy_cellar_email_sample.html")
        events = scraper.parse_email_html(html, "Upcoming Shows", datetime.now(timezone.utc))
        headliners = {e.headliner for e in events}
        assert "Dave Chappelle" in headliners
        assert "Chris Rock" in headliners

    def test_ticket_links_contain_comedycellar_domain(self):
        scraper = self._make_scraper()
        html = _load_fixture("comedy_cellar_email_sample.html")
        events = scraper.parse_email_html(html, "Upcoming Shows", datetime.now(timezone.utc))
        for event in events:
            assert "comedycellar.com" in event.ticket_link

    def test_dates_are_timezone_aware(self):
        scraper = self._make_scraper()
        html = _load_fixture("comedy_cellar_email_sample.html")
        events = scraper.parse_email_html(html, "Upcoming Shows", datetime.now(timezone.utc))
        for event in events:
            assert event.date.tzinfo is not None

    def test_empty_html_returns_empty_list(self):
        scraper = self._make_scraper()
        events = scraper.parse_email_html("<html><body></body></html>", "No shows", datetime.now(timezone.utc))
        assert events == []


# ---------------------------------------------------------------------------
# Extractor unit tests
# ---------------------------------------------------------------------------


class TestComedyCellarEmailExtractor:
    def test_extract_from_sample_fixture(self):
        html = _load_fixture("comedy_cellar_email_sample.html")
        events = ComedyCellarEmailExtractor().extract(html)
        assert len(events) == 2

    def test_event_has_required_fields(self):
        html = _load_fixture("comedy_cellar_email_sample.html")
        events = ComedyCellarEmailExtractor().extract(html)
        for e in events:
            assert e.headliner
            assert e.ticket_link
            assert e.date is not None

    def test_returns_empty_for_blank_html(self):
        events = ComedyCellarEmailExtractor().extract("<html></html>")
        assert events == []

    def test_fallback_link_scanning(self):
        """Extractor finds shows via ticket link scanning when no class blocks exist."""
        html = """
        <html><body>
          <div>
            <span>Friday, March 7, 2026 - 8:00 PM</span>
            <strong>Dave Chappelle</strong>
            <a href="https://www.comedycellar.com/reservations-newyork/?showid=99">Book</a>
          </div>
        </body></html>
        """
        events = ComedyCellarEmailExtractor().extract(html)
        assert len(events) == 1
        assert events[0].headliner == "Dave Chappelle"
        assert "comedycellar.com" in events[0].ticket_link

    def test_to_show_produces_show_object(self):
        html = _load_fixture("comedy_cellar_email_sample.html")
        events = ComedyCellarEmailExtractor().extract(html)
        club = _make_club()
        for event in events:
            show = event.to_show(club, enhanced=False)
            assert show is not None
            assert show.club_id == club.id
            assert show.date is not None
