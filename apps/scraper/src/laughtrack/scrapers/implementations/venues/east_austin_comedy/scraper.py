"""
East Austin Comedy scraper implementation.

East Austin Comedy (2505 E 6th St, Austin TX) is an intimate 82-seat BYOB comedy
room running shows nightly. Show availability is exposed via a Netlify serverless
function — one endpoint per weekday name:

  GET https://eastaustincomedy.com/.netlify/functions/availability?showDay={day}&offset=0

Each weekday call returns all upcoming dates for that day of the week, with show
times and seat availability.

Comedian lineups are not published on the website; ticket purchase is handled via
an embedded Square modal on the homepage (no per-show ticket URL).

Pipeline:
  1. collect_scraping_targets() → [scraping_url] (base class default)
  2. get_data(url)              → queries all 7 weekday endpoints and aggregates
                                  EastAustinComedyEvent objects
  3. transformation_pipeline   → EastAustinComedyEvent.to_show() → Show objects
"""

from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import EastAustinComedyPageData
from .extractor import EastAustinComedyEventExtractor
from .transformer import EastAustinComedyEventTransformer

_AVAILABILITY_BASE = (
    "https://eastaustincomedy.com/.netlify/functions/availability"
)
_DAY_NAMES = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]


class EastAustinComedyScraper(BaseScraper):
    """Scraper for East Austin Comedy (Austin, TX) via Netlify availability API."""

    key = "east_austin_comedy"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            EastAustinComedyEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[EastAustinComedyPageData]:
        """
        Query all 7 weekday availability endpoints and aggregate show slots.

        Args:
            url: Unused — kept for BaseScraper interface compatibility.
                 The scraper always hits the Netlify function directly.

        Returns:
            EastAustinComedyPageData containing all upcoming show slots, or None.
        """
        all_events = []
        seen: set = set()

        for day in _DAY_NAMES:
            api_url = f"{_AVAILABILITY_BASE}?showDay={day}&offset=0"
            try:
                data = await self.fetch_json(api_url)
            except Exception as e:
                Logger.warn(
                    f"{self._log_prefix}: error fetching {day}: {e}",
                    self.logger_context,
                )
                continue

            if not data:
                Logger.info(
                    f"{self._log_prefix}: no data for {day}",
                    self.logger_context,
                )
                continue

            events = EastAustinComedyEventExtractor.parse_availability(
                data, self.logger_context
            )
            for event in events:
                key = (event.date, event.time)
                if key not in seen:
                    seen.add(key)
                    all_events.append(event)

            Logger.debug(
                f"{self._log_prefix}: {day}: {len(events)} slots",
                self.logger_context,
            )

        if not all_events:
            Logger.info(
                f"{self._log_prefix}: no show slots found across all weekdays",
                self.logger_context,
            )
            return None

        Logger.info(
            f"{self._log_prefix}: {len(all_events)} total show slots",
            self.logger_context,
        )
        return EastAustinComedyPageData(event_list=all_events)
