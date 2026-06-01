"""Regression: BaseScraper.__init__ must not stomp DEFAULT_DOMAIN_CONFIGS."""

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.base.base_scraper import BaseScraper


class _ConcreteScraper(BaseScraper):
    key = "test"

    async def get_data(self, target):
        return None


def _make_club(scraping_url: str, *, rate_limit=None) -> Club:
    kwargs = dict(
        id=1, name="Test Club", address="", website=scraping_url, popularity=0,
        zip_code="", phone_number="", visible=True,
    )
    if rate_limit is not None:
        kwargs["rate_limit"] = rate_limit
    club = Club(**kwargs)
    club.active_scraping_source = ScrapingSource(
        id=1, club_id=club.id, platform="custom", scraper_key="",
        source_url=scraping_url, external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


class TestBaseScraperRateLimitOverride:
    def test_default_domain_config_survives_init_when_club_has_no_explicit_rate_limit(self):
        """An explicit DEFAULT_DOMAIN_CONFIGS entry (eastvillecomedy.com=2.0)
        must survive BaseScraper.__init__ for a club whose scraping_domain
        matches, when the club itself has no explicit rate_limit override."""
        club = _make_club("https://eastvillecomedy.com/shows")
        scraper = _ConcreteScraper(club=club)
        assert scraper.rate_limiter.get_domain_limit("eastvillecomedy.com") == 2.0

    def test_explicit_club_rate_limit_overrides_default_domain_config(self):
        """When a club provides an explicit rate_limit, it must win over the
        DEFAULT_DOMAIN_CONFIGS entry for the same domain."""
        club = _make_club("https://eastvillecomedy.com/shows", rate_limit=0.5)
        scraper = _ConcreteScraper(club=club)
        assert scraper.rate_limiter.get_domain_limit("eastvillecomedy.com") == 0.5

    def test_unknown_domain_falls_back_to_default_rps(self):
        """A club with no DEFAULT_DOMAIN_CONFIGS entry and no explicit
        rate_limit must inherit the RateLimiter's default RPS (1.0)."""
        club = _make_club("https://unknownvenue.example.com/shows")
        scraper = _ConcreteScraper(club=club)
        assert scraper.rate_limiter.get_domain_limit("unknownvenue.example.com") == 1.0
