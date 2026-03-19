"""
Unit tests for BushwickComedyClubScraper.__init__ domain guard.

Verifies that a ValueError is raised immediately when scraping_url is
blank or produces an invalid domain, preventing wasted retry cycles.
"""

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.bushwick.scraper import (
    BushwickComedyClubScraper,
)


def _club(**overrides) -> Club:
    defaults = dict(
        id=19,
        name="Bushwick Comedy Club",
        address="",
        website="https://www.bushwickcomedy.com",
        scraping_url="https://www.bushwickcomedy.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    defaults.update(overrides)
    return Club(**defaults)


def test_valid_scraping_url_does_not_raise():
    scraper = BushwickComedyClubScraper(_club())
    assert scraper.domain == "https://www.bushwickcomedy.com"


def test_blank_scraping_url_raises_value_error():
    with pytest.raises(ValueError, match="Bushwick: scraping_url is missing or produced an invalid domain"):
        BushwickComedyClubScraper(_club(scraping_url=""))


def test_scraping_url_without_protocol_raises_value_error():
    with pytest.raises(ValueError, match="Bushwick: scraping_url is missing or produced an invalid domain"):
        BushwickComedyClubScraper(_club(scraping_url="www.bushwickcomedy.com"))
