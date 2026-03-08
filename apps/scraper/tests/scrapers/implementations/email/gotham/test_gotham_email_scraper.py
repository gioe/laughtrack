"""
Unit tests for GothamEmailScraper and GothamEmailExtractor.

Tests use a sample HTML newsletter fixture stored at
tests/fixtures/html/gotham_email_sample.html.
"""

import pathlib
from datetime import datetime, timezone

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.email_show_event import EmailShowEvent
from laughtrack.scrapers.base.email_base_scraper import EmailBaseScraper
from laughtrack.scrapers.implementations.email.gotham.extractor import GothamEmailExtractor
from laughtrack.scrapers.implementations.email.gotham.scraper import GothamEmailScraper

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FIXTURES_DIR = pathlib.Path(__file__).parents[4] / "fixtures" / "html"


def _load_fixture(name: str) -> str:
    return (_FIXTURES_DIR / name).read_text(encoding="utf-8")


def _make_club() -> Club:
    return Club(
        id=2,
        name="Gotham Comedy Club",
        address="208 W 23rd St, New York, NY 10011",
        website="https://www.gothamcomedy.com",
        scraping_url="gothamcomedy.com",
        popularity=80,
        zip_code="10011",
        phone_number="",
        visible=True,
    )


# ---------------------------------------------------------------------------
# Scraper class-attribute tests
# ---------------------------------------------------------------------------


class TestGothamEmailScraperAttributes:
    def test_key(self):
        assert GothamEmailScraper.key == "gotham_email"

    def test_sender_domain(self):
        assert GothamEmailScraper.sender_domain == "gothamcomedy.com"

    def test_inherits_from_email_base_scraper(self):
        assert issubclass(GothamEmailScraper, EmailBaseScraper)


# ---------------------------------------------------------------------------
# parse_email_html — integration with extractor
# ---------------------------------------------------------------------------


class TestGothamEmailScraperParseEmailHtml:
    def _make_scraper(self) -> GothamEmailScraper:
        club = _make_club()
        scraper = GothamEmailScraper.__new__(GothamEmailScraper)
        scraper._club = club
        scraper.logger_context = {}
        return scraper

    def test_returns_list_of_email_show_events(self):
        scraper = self._make_scraper()
        html = _load_fixture("gotham_email_sample.html")
        events = scraper.parse_email_html(html, "Gotham Newsletter", datetime.now(timezone.utc))
        assert isinstance(events, list)
        assert all(isinstance(e, EmailShowEvent) for e in events)

    def test_parses_two_shows_from_fixture(self):
        scraper = self._make_scraper()
        html = _load_fixture("gotham_email_sample.html")
        events = scraper.parse_email_html(html, "Gotham Newsletter", datetime.now(timezone.utc))
        assert len(events) == 2

    def test_headliner_names_extracted(self):
        scraper = self._make_scraper()
        html = _load_fixture("gotham_email_sample.html")
        events = scraper.parse_email_html(html, "Gotham Newsletter", datetime.now(timezone.utc))
        headliners = {e.headliner for e in events}
        assert "Jerry Seinfeld" in headliners
        assert "Jim Gaffigan" in headliners

    def test_ticket_links_contain_valid_domain(self):
        scraper = self._make_scraper()
        html = _load_fixture("gotham_email_sample.html")
        events = scraper.parse_email_html(html, "Gotham Newsletter", datetime.now(timezone.utc))
        for event in events:
            assert any(d in event.ticket_link for d in ("showclix.com", "gothamcomedy.com"))

    def test_dates_are_timezone_aware(self):
        scraper = self._make_scraper()
        html = _load_fixture("gotham_email_sample.html")
        events = scraper.parse_email_html(html, "Gotham Newsletter", datetime.now(timezone.utc))
        for event in events:
            assert event.date.tzinfo is not None

    def test_empty_html_returns_empty_list(self):
        scraper = self._make_scraper()
        events = scraper.parse_email_html("<html><body></body></html>", "No shows", datetime.now(timezone.utc))
        assert events == []


# ---------------------------------------------------------------------------
# Extractor unit tests
# ---------------------------------------------------------------------------


class TestGothamEmailExtractor:
    def test_extract_from_sample_fixture(self):
        html = _load_fixture("gotham_email_sample.html")
        events = GothamEmailExtractor().extract(html)
        assert len(events) == 2

    def test_event_has_required_fields(self):
        html = _load_fixture("gotham_email_sample.html")
        events = GothamEmailExtractor().extract(html)
        for e in events:
            assert e.headliner
            assert e.ticket_link
            assert e.date is not None

    def test_returns_empty_for_blank_html(self):
        events = GothamEmailExtractor().extract("<html></html>")
        assert events == []

    def test_block_based_layout(self):
        """Extractor handles div-block layouts as a fallback."""
        html = """
        <html><body>
          <div class="show-block">
            <span class="show-date">Saturday, March 8, 2026 - 8:00 PM</span>
            <span class="headliner">Jerry Seinfeld</span>
            <a href="https://www.showclix.com/event/jerry-seinfeld-gotham">Get Tickets</a>
          </div>
        </body></html>
        """
        events = GothamEmailExtractor().extract(html)
        assert len(events) == 1
        assert events[0].headliner == "Jerry Seinfeld"
        assert "showclix.com" in events[0].ticket_link

    def test_fallback_link_scanning(self):
        """Extractor finds shows via ticket link scanning when no class blocks exist."""
        html = """
        <html><body>
          <div>
            <p>Saturday, March 8, 2026 - 8:00 PM</p>
            <strong>Jerry Seinfeld</strong>
            <a href="https://www.gothamcomedy.com/events/jerry-show">Get Tickets</a>
          </div>
        </body></html>
        """
        events = GothamEmailExtractor().extract(html)
        assert len(events) == 1
        assert events[0].headliner == "Jerry Seinfeld"

    def test_to_show_produces_show_object(self):
        html = _load_fixture("gotham_email_sample.html")
        events = GothamEmailExtractor().extract(html)
        club = _make_club()
        for event in events:
            show = event.to_show(club, enhanced=False)
            assert show is not None
            assert show.club_id == club.id
            assert show.date is not None

    def test_show_format_compatible_with_web_scraper(self):
        """Shows produced by email scraper have same club_id and timezone as web scraper output."""
        html = _load_fixture("gotham_email_sample.html")
        events = GothamEmailExtractor().extract(html)
        club = _make_club()
        for event in events:
            show = event.to_show(club, enhanced=False)
            assert show is not None
            # Date must be timezone-aware (America/New_York) — same as web scraper
            assert show.date.tzinfo is not None
            # Club ID must match — used as upsert key alongside date
            assert show.club_id == club.id
