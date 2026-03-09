"""Integration tests verifying that ScrapingService wires ProxyPool into scrapers and clients."""

import os
from unittest.mock import MagicMock, patch

import pytest

from laughtrack.foundation.models.operation_result import DatabaseOperationResult
from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(proxy_pool=None):
    """Create a ScrapingService with __init__ bypassed, injecting a proxy_pool."""
    from laughtrack.core.services.scraping import ScrapingService
    with patch.object(ScrapingService, "__init__", lambda self, *a, **kw: None):
        svc = ScrapingService.__new__(ScrapingService)
        svc.success_rate_threshold = 70.0
        svc.proxy_pool = proxy_pool
        svc._scraping_resolver = MagicMock()
        mock_rp = MagicMock()
        mock_rp.insert_club_result.return_value = DatabaseOperationResult()
        svc._result_processor = mock_rp
    return svc


def _make_club(name="Club", scraper_key="test_scraper"):
    club = MagicMock()
    club.name = name
    club.scraper = scraper_key
    club.id = 1
    club.as_context.return_value = {}
    return club


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestProxyPoolWiredIntoScrapers:
    def test_pool_forwarded_to_scraper_constructor(self):
        """ScrapingService passes proxy_pool to the scraper class constructor."""
        pool = ProxyPool(proxies=["http://proxy1:8080"])
        svc = _make_service(proxy_pool=pool)

        received_kwargs = {}

        def scraper_factory(club, **kw):
            received_kwargs.update(kw)
            s = MagicMock()
            s.scrape_with_result.return_value = ClubScrapingResult(
                club_name=club.name, shows=[], execution_time=0.0
            )
            return s

        svc._scraping_resolver.get.return_value = scraper_factory
        svc._scrape_clubs_with_metrics([_make_club()])

        assert "proxy_pool" in received_kwargs
        assert received_kwargs["proxy_pool"] is pool

    def test_none_pool_forwarded_when_env_unset(self):
        """When SCRAPER_PROXY_LIST is unset, proxy_pool is None and scraping proceeds."""
        svc = _make_service(proxy_pool=None)

        received_kwargs = {}

        def scraper_factory(club, **kw):
            received_kwargs.update(kw)
            s = MagicMock()
            s.scrape_with_result.return_value = ClubScrapingResult(
                club_name=club.name, shows=[MagicMock()], execution_time=0.0
            )
            return s

        svc._scraping_resolver.get.return_value = scraper_factory
        _, summary, _ = svc._scrape_clubs_with_metrics([_make_club()])

        assert received_kwargs.get("proxy_pool") is None
        # Scraping still succeeds without a proxy
        assert summary.per_club[0].ok == 1

    def test_from_env_returns_none_when_env_unset(self):
        """ProxyPool.from_env() returns None when SCRAPER_PROXY_LIST is not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SCRAPER_PROXY_LIST", None)
            pool = ProxyPool.from_env()
        assert pool is None

    def test_pool_stored_on_service(self):
        """proxy_pool attribute on ScrapingService holds the value from from_env()."""
        fake_pool = ProxyPool(proxies=["http://proxy1:8080"])

        with patch("laughtrack.core.services.scraping.ProxyPool") as MockPool, \
             patch("laughtrack.core.services.scraping.ClubHandler"), \
             patch("laughtrack.core.services.scraping.ClubSelector"), \
             patch("laughtrack.core.services.scraping.ScraperResolver"), \
             patch("laughtrack.core.services.scraping.build_services"):
            MockPool.from_env.return_value = fake_pool
            from importlib import import_module, reload
            import laughtrack.core.services.scraping as svc_module
            from laughtrack.core.services.scraping import ScrapingService
            svc = ScrapingService.__new__(ScrapingService)
            ScrapingService.__init__(svc)
            assert svc.proxy_pool is fake_pool
