"""Regression: per-scraper __init__ RPS overrides survive BaseScraper.__init__.

TASK-2570 shipped three scraper subclasses that bump their venue host's RPS
above the 1.0 default at construction time (modeled on SeatEngineClassic's
TASK-2556 pattern): JsonLdScraper, SquarespaceScraper, FoxTucsonTheatreScraper.
TASK-2577 then migrated all four (those three plus SeatEngineClassic) onto a
shared BaseScraper._register_host_rps helper; these tests pin that the
post-migration behavior is unchanged from the inline-override pattern.

Each override must be:
  (a) applied (the registered RPS matches the constant declared in the module),
  (b) keyed to the club's own scraping_domain (so distinct venues don't share),
  (c) the winning value when a DEFAULT_DOMAIN_CONFIGS-style entry already
      registers a lower RPS for the same host — the helper runs from each
      subclass's __init__ AFTER super().__init__, so it has the last word
      (TASK-2580).

Each test uses a unique fake host so the singleton RateLimiter's per-domain
state from one test does not leak into another's assertion. The cross-scraper
empty-domain-guard coverage lives once on the helper in
test_base_scraper_rate_limit.py — no need to repeat it per subclass.
"""

import importlib.util

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.squarespace.scraper import (
    SquarespaceScraper,
    _SQUARESPACE_HOST_RPS,
)
from laughtrack.scrapers.implementations.venues.fox_tucson_theatre.scraper import (
    FoxTucsonTheatreScraper,
    _FOX_TUCSON_HOST_RPS,
)
from laughtrack.utilities.infrastructure.rate_limiter import RateLimiter


def _make_club(*, scraping_url: str, name: str = "Test Club", scraper_key: str = "") -> Club:
    club = Club(
        id=1,
        name=name,
        address="",
        website=scraping_url,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key=scraper_key,
        source_url=scraping_url,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


@pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed (JsonLdScraper imports it transitively)",
)
class TestJsonLdRpsOverride:
    def test_init_applies_host_rps_override(self):
        from laughtrack.scrapers.implementations.json_ld.scraper import (
            JsonLdScraper,
            _JSON_LD_HOST_RPS,
        )

        club = _make_club(
            scraping_url="https://huntsville-levity-rps.example.com/calendar",
            name="Huntsville Levity (test)",
            scraper_key="json_ld",
        )
        scraper = JsonLdScraper(club)
        assert (
            scraper.rate_limiter.get_domain_limit("huntsville-levity-rps.example.com")
            == _JSON_LD_HOST_RPS
        )

    def test_subclass_override_beats_existing_low_domain_config(self):
        from laughtrack.scrapers.implementations.json_ld.scraper import (
            JsonLdScraper,
            _JSON_LD_HOST_RPS,
        )

        host = "coastal-creative-rps.example.com"
        RateLimiter().set_domain_limit(host, 0.5)
        club = _make_club(
            scraping_url=f"https://{host}/calendar",
            name="Coastal Creative (test)",
            scraper_key="json_ld",
        )
        scraper = JsonLdScraper(club)
        assert scraper.rate_limiter.get_domain_limit(host) == _JSON_LD_HOST_RPS


class TestSquarespaceRpsOverride:
    def test_init_applies_host_rps_override(self):
        club = _make_club(
            scraping_url="https://den-theatre-rps.example.com/api/open/GetItemsByMonth?collectionId=abc",
            name="The Den Theatre (test)",
            scraper_key="squarespace",
        )
        scraper = SquarespaceScraper(club)
        assert (
            scraper.rate_limiter.get_domain_limit("den-theatre-rps.example.com")
            == _SQUARESPACE_HOST_RPS
        )

    def test_subclass_override_beats_existing_low_domain_config(self):
        host = "elysian-rps.example.com"
        RateLimiter().set_domain_limit(host, 0.5)
        club = _make_club(
            scraping_url=f"https://{host}/api/open/GetItemsByMonth?collectionId=xyz",
            name="The Elysian Theater (test)",
            scraper_key="squarespace",
        )
        scraper = SquarespaceScraper(club)
        assert scraper.rate_limiter.get_domain_limit(host) == _SQUARESPACE_HOST_RPS


class TestFoxTucsonRpsOverride:
    def test_init_applies_host_rps_override(self):
        club = _make_club(
            scraping_url="https://fox-tucson-rps.example.com/events/",
            name="Fox Tucson Theatre (test)",
            scraper_key="fox_tucson_theatre",
        )
        scraper = FoxTucsonTheatreScraper(club)
        assert (
            scraper.rate_limiter.get_domain_limit("fox-tucson-rps.example.com")
            == _FOX_TUCSON_HOST_RPS
        )

    def test_subclass_override_beats_existing_low_domain_config(self):
        host = "fox-tucson-existing-config-rps.example.com"
        RateLimiter().set_domain_limit(host, 0.5)
        club = _make_club(
            scraping_url=f"https://{host}/events/",
            name="Fox Tucson Theatre (test, pre-seeded)",
            scraper_key="fox_tucson_theatre",
        )
        scraper = FoxTucsonTheatreScraper(club)
        assert scraper.rate_limiter.get_domain_limit(host) == _FOX_TUCSON_HOST_RPS


class TestRpsValuesArePinned:
    """The per-scraper constants are referenced in module docstrings + commit
    rationale (TASK-2570). Pin them so an accidental drift triggers a test
    failure rather than a silent behavior change."""

    def test_squarespace_rps_is_two(self):
        assert _SQUARESPACE_HOST_RPS == 2.0

    def test_fox_tucson_rps_is_two(self):
        assert _FOX_TUCSON_HOST_RPS == 2.0

    @pytest.mark.skipif(
        importlib.util.find_spec("curl_cffi") is None,
        reason="curl_cffi not installed (JsonLdScraper imports it transitively)",
    )
    def test_json_ld_rps_is_two(self):
        from laughtrack.scrapers.implementations.json_ld.scraper import (
            _JSON_LD_HOST_RPS,
        )

        assert _JSON_LD_HOST_RPS == 2.0
