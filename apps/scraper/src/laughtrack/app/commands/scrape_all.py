"""Command facade to scrape all active clubs."""

from typing import List

from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.core.services.scraping import ScrapingService


def run() -> List[ClubScrapingResult]:
    service = ScrapingService()
    return service.scrape_all_clubs()
