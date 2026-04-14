"""
Dr. Grins Comedy Club scraper (Grand Rapids, MI).

Now delegates to the generic EtixScraper. Dr. Grins sells tickets through
Etix — the venue page at etix.com/ticket/v/35455/drgrins-comedy-club-at-the-bob
is handled by the generic Etix HTML parser.
"""

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper


class DrGrinsScraper(EtixScraper):
    """Scraper for Dr. Grins Comedy Club (Grand Rapids, MI)."""

    key = "dr_grins"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
