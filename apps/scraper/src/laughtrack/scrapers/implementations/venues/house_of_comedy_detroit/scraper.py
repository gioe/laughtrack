"""Scraper for Detroit House of Comedy."""

from laughtrack.scrapers.implementations.venues.house_of_comedy_phoenix.scraper import (
    HouseOfComedyPhoenixScraper,
)

_DEFAULT_SOURCE_URL = "https://detroit.houseofcomedy.net/upcoming-comedy-shows/"
_DEFAULT_AJAX_URL = "https://detroit.houseofcomedy.net/wp-admin/admin-ajax.php"


class HouseOfComedyDetroitScraper(HouseOfComedyPhoenixScraper):
    """Fetch Detroit shows from the House of Comedy WordPress AJAX endpoint."""

    key = "house_of_comedy_detroit"
    default_source_url = _DEFAULT_SOURCE_URL
    default_ajax_url = _DEFAULT_AJAX_URL
