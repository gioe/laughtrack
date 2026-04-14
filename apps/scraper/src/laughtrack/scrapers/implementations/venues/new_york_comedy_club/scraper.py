"""
New York Comedy Club JSON-LD scraper with address-based location filtering.

NYCC operates three venues (Midtown, East Village, Upper West Side) on a single
shared calendar page at newyorkcomedyclub.com/calendar. This scraper extends the
generic JSON-LD pattern to filter events by matching the JSON-LD
location.address.streetAddress against the club's database address, so each club
record only receives its own venue's shows.
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import NewYorkComedyClubPageData
from .transformer import NewYorkComedyClubTransformer


class NewYorkComedyClubScraper(BaseScraper):
    """JSON-LD scraper that filters events by the club's street address."""

    key = "new_york_comedy_club"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            NewYorkComedyClubTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[NewYorkComedyClubPageData]:
        from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor

        try:
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(normalized_url)

            event_list = EventExtractor.extract_events(html_content)
            if not event_list:
                if html_content:
                    Logger.warn(
                        f"{self._log_prefix}: Page loaded but contained no JSON-LD events: {normalized_url}",
                        self.logger_context,
                    )
                return None

            # Filter events whose street address matches this club's address
            club_street = _normalize_street(self.club.address)
            filtered = []
            for event in event_list:
                event_street = _normalize_street(
                    event.location.address.street_address
                    if event.location and event.location.address
                    else ""
                )
                if club_street and event_street and club_street == event_street:
                    filtered.append(event)

            Logger.info(
                f"{self._log_prefix}: {len(filtered)}/{len(event_list)} events matched address '{self.club.address}'",
                self.logger_context,
            )

            if not filtered:
                return None

            return NewYorkComedyClubPageData(event_list=filtered)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error extracting data from {url}: {e}",
                self.logger_context,
            )
            return None


def _normalize_street(address: str) -> str:
    """Normalize a street address for comparison.

    Strips city/state/zip (first comma-delimited segment only),
    lowercases, and normalizes common abbreviations so that
    '85 E 4th St' matches '85 East 4th Street'.
    """
    if not address:
        return ""

    street = address.split(",")[0].strip().lower().rstrip(".")

    replacements = {
        " street": " st",
        " avenue": " ave",
        " boulevard": " blvd",
        " drive": " dr",
        " road": " rd",
        " place": " pl",
        " east ": " e ",
        " west ": " w ",
        " north ": " n ",
        " south ": " s ",
    }
    for old, new in replacements.items():
        street = street.replace(old, new)

    return street
