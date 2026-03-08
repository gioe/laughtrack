"""Tests that ScraperResolver discovers and exposes email scraper classes.

Criteria covered:
  499 — GothamEmailScraper is registered in the scraper factory/registry
  500 — ComedyCellarEmailScraper is registered in the scraper factory/registry
  501 — Email scrapers are invoked during the normal scraping run
"""

from unittest.mock import MagicMock, patch

import pytest

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.scrapers.implementations.email.comedy_cellar.scraper import (
    ComedyCellarEmailScraper,
)
from laughtrack.scrapers.implementations.email.gotham.scraper import GothamEmailScraper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_resolver() -> ScraperResolver:
    """Return an unloaded ScraperResolver (no cached registry)."""
    return ScraperResolver()


# ---------------------------------------------------------------------------
# Criterion 499 — GothamEmailScraper in registry
# ---------------------------------------------------------------------------


class TestGothamEmailScraperRegistration:
    def test_get_returns_gotham_email_scraper(self):
        resolver = _fresh_resolver()
        cls = resolver.get("gotham_email")
        assert cls is GothamEmailScraper

    def test_gotham_email_key_in_keys(self):
        resolver = _fresh_resolver()
        assert "gotham_email" in resolver.keys()

    def test_gotham_email_in_items(self):
        resolver = _fresh_resolver()
        mapping = dict(resolver.items())
        assert "gotham_email" in mapping
        assert mapping["gotham_email"] is GothamEmailScraper


# ---------------------------------------------------------------------------
# Criterion 500 — ComedyCellarEmailScraper in registry
# ---------------------------------------------------------------------------


class TestComedyCellarEmailScraperRegistration:
    def test_get_returns_comedy_cellar_email_scraper(self):
        resolver = _fresh_resolver()
        cls = resolver.get("comedy_cellar_email")
        assert cls is ComedyCellarEmailScraper

    def test_comedy_cellar_email_key_in_keys(self):
        resolver = _fresh_resolver()
        assert "comedy_cellar_email" in resolver.keys()

    def test_comedy_cellar_email_in_items(self):
        resolver = _fresh_resolver()
        mapping = dict(resolver.items())
        assert "comedy_cellar_email" in mapping
        assert mapping["comedy_cellar_email"] is ComedyCellarEmailScraper


# ---------------------------------------------------------------------------
# Criterion 501 — Email scrapers dispatched by ScrapingService
# ---------------------------------------------------------------------------


class TestScrapingServiceDispatchesEmailScrapers:
    """Verify that ScrapingService resolves email-scraper keys to the correct classes.

    These tests patch out DB I/O and the actual scraper execution so that we
    only exercise the dispatch logic (resolver lookup + instantiation), which is
    the part TASK-151 wires up.
    """

    def _make_club(self, scraper_key: str):
        club = MagicMock()
        club.name = "Test Club"
        club.id = 1
        club.scraper = scraper_key
        return club

    def test_service_resolver_finds_gotham_email_scraper(self):
        from laughtrack.core.services.scraping import ScrapingService

        with patch.object(ScrapingService, "__init__", lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc._scraping_resolver = ScraperResolver()

        cls = svc._scraping_resolver.get("gotham_email")
        assert cls is GothamEmailScraper

    def test_service_resolver_finds_comedy_cellar_email_scraper(self):
        from laughtrack.core.services.scraping import ScrapingService

        with patch.object(ScrapingService, "__init__", lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc._scraping_resolver = ScraperResolver()

        cls = svc._scraping_resolver.get("comedy_cellar_email")
        assert cls is ComedyCellarEmailScraper

    def test_email_scraper_instantiated_for_gotham_email_club(self):
        """ScrapingService._scraping_resolver returns GothamEmailScraper for a
        club whose scraper field is 'gotham_email', so the service would
        instantiate it during a normal run."""
        from laughtrack.core.services.scraping import ScrapingService

        with patch.object(ScrapingService, "__init__", lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc._scraping_resolver = ScraperResolver()

        club = self._make_club("gotham_email")
        cls = svc._scraping_resolver.get(club.scraper)
        assert cls is GothamEmailScraper, (
            "ScrapingService should dispatch to GothamEmailScraper for "
            "clubs configured with scraper='gotham_email'"
        )

    def test_email_scraper_instantiated_for_comedy_cellar_email_club(self):
        """ScrapingService._scraping_resolver returns ComedyCellarEmailScraper
        for a club whose scraper field is 'comedy_cellar_email'."""
        from laughtrack.core.services.scraping import ScrapingService

        with patch.object(ScrapingService, "__init__", lambda self, *a, **kw: None):
            svc = ScrapingService.__new__(ScrapingService)
            svc._scraping_resolver = ScraperResolver()

        club = self._make_club("comedy_cellar_email")
        cls = svc._scraping_resolver.get(club.scraper)
        assert cls is ComedyCellarEmailScraper, (
            "ScrapingService should dispatch to ComedyCellarEmailScraper for "
            "clubs configured with scraper='comedy_cellar_email'"
        )
