"""Integration test confirming that the 'json_ld' scraper key resolves to JsonLdScraper.

ScraperMapping auto-discovers scraper classes by walking BaseScraper subclasses.
This test constructs a real ScraperMapping (with __init__ bypassed to avoid the DB
connection), lets module discovery run, and asserts that get_scraper_for_club()
returns JsonLdScraper for a club whose scraper field is 'json_ld'.
"""

from unittest.mock import patch

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.json_ld.scraper import JsonLdScraper


def _club() -> Club:
    _c = Club(id=1, name='Test JSON-LD Club', address='', website='https://example.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='json_ld', scraper_key='json_ld', source_url='https://example.com/events', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_mapping():
    """Return a ScraperMapping with __init__ bypassed but module discovery enabled."""
    from laughtrack.infrastructure.config.scraper_mapping import ScraperMapping

    with patch.object(ScraperMapping, "__init__", lambda self, *a, **kw: None):
        mapping = ScraperMapping.__new__(ScraperMapping)
        mapping._scraper_class_map = None
        mapping._club_mappings = {}
        mapping._scrapers_loaded = False  # allow real module discovery

    return mapping


class TestJsonLdRegistryIntegration:
    def test_json_ld_key_resolves_to_json_ld_scraper(self):
        """'json_ld' scraper key must resolve to JsonLdScraper via ScraperMapping."""
        mapping = _make_mapping()
        club = _club()

        result = mapping.get_scraper_for_club(club)

        assert result is JsonLdScraper, (
            f"Expected JsonLdScraper for scraper='json_ld', got {result}. "
            "Check that JsonLdScraper.key == 'json_ld' and that its module is "
            "discovered by ScraperMapping._import_scraper_modules()."
        )
