"""Generic SimpleTix scraper for clubs using SimpleTix for ticketing.

SimpleTix event pages embed a JavaScript `var timeArray = [...]` containing
individual show times with IDs. This scraper fetches the event page, extracts
the timeArray, parses each entry into a show with the event title and ticket
URL pointing back to the SimpleTix page.
"""

from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.simpletix import SimpleTixEvent
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from .data import SimpleTixPageData
from .extractor import SimpleTixExtractor
from .transformer import SimpleTixTransformer


class SimpleTixScraper(BaseScraper):
    """Generic scraper for SimpleTix-powered event pages."""

    key = "simpletix"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(SimpleTixTransformer(club))

    async def collect_scraping_targets(self) -> List[str]:
        """Return the club's scraping_url as the single target."""
        if not self.club.scraping_url:
            Logger.error(
                f"{self._log_prefix}: No scraping_url configured",
                self.logger_context,
            )
            return []
        return [self.club.scraping_url]

    async def get_data(self, target: str) -> Optional[SimpleTixPageData]:
        """Fetch the SimpleTix event page and extract show times."""
        html = await self.fetch_html(target)
        if not html:
            return None

        time_entries, title, price = SimpleTixExtractor.extract_events(html)

        if not time_entries:
            Logger.warn(
                f"{self._log_prefix}: No timeArray entries found on {target}"
            )
            return None

        event_name = title or self.club.name
        now = datetime.now()

        events = []
        for entry in time_entries:
            start_date = SimpleTixExtractor.parse_time_entry(entry.get("Time", ""))
            if not start_date:
                continue

            # Skip past events
            if start_date < now:
                continue

            events.append(SimpleTixEvent(
                name=event_name,
                start_date=start_date,
                show_page_url=target,
                ticket_url=target,
                price=price,
                performers=[],
            ))

        Logger.info(
            f"{self._log_prefix}: Found {len(events)} upcoming shows "
            f"(from {len(time_entries)} total time entries)",
            self.logger_context,
        )

        return SimpleTixPageData(event_list=events)
