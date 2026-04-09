"""
Comedy Club Haug scraper (Rotterdam, Netherlands).

Comedy Club Haug is a stand-up comedy club in Rotterdam. It uses Craft CMS
with a Next.js frontend and Stager (stager.co) for ticketing.

All event data is embedded in the /shows page as a React Server Components
(RSC) streaming payload. A single page fetch yields the full event list
with artist lineups, dates, and ticket URLs — no pagination or individual
page fetches needed.

Pipeline:
  1. collect_scraping_targets() → [club.scraping_url]  (https://comedyclubhaug.com/shows)
  2. get_data(url):
       a. Fetch /shows page via Playwright (JS-rendered Next.js)
       b. Parse RSC payload → extract shows array
       c. Filter: active events only, skip sold out
       d. Build ComedyClubHaugEvent per show
  3. transformation_pipeline → ComedyClubHaugEvent.to_show() → Show objects
"""

from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.comedy_club_haug import ComedyClubHaugEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import ComedyClubHaugPageData
from .extractor import ComedyClubHaugExtractor
from .transformer import ComedyClubHaugEventTransformer


class ComedyClubHaugScraper(BaseScraper):
    """Scraper for Comedy Club Haug (Rotterdam) via Craft CMS + Stager."""

    key = "comedy_club_haug"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            ComedyClubHaugEventTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[ComedyClubHaugPageData]:
        """
        Fetch the Comedy Club Haug shows page and extract all upcoming events.

        Args:
            url: The shows page URL (from club.scraping_url).

        Returns:
            ComedyClubHaugPageData with extracted events, or None on failure.
        """
        try:
            html = await self.fetch_html(url)
            if not html:
                Logger.warn(
                    f"{self._log_prefix}: empty response for {url}",
                    self.logger_context,
                )
                return None

            raw_events = ComedyClubHaugExtractor.extract_shows(html)
            if not raw_events:
                Logger.info(
                    f"{self._log_prefix}: no events found in RSC payload",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: extracted {len(raw_events)} raw events from page",
                self.logger_context,
            )

            events: List[ComedyClubHaugEvent] = []
            for raw in raw_events:
                status = raw.get("eventStatus", "")
                if status != "active":
                    continue

                title = raw.get("eventTitle", "")
                if not title:
                    continue

                start_time = raw.get("eventProgramStart", "")
                end_time = raw.get("eventProgramEnd", "")
                if not start_time:
                    continue

                # Extract performer names from artists array
                performers: List[str] = []
                for artist in raw.get("artists", []):
                    if isinstance(artist, dict) and artist.get("title"):
                        performers.append(artist["title"])

                # Ticket URL from Stager
                ticket_url = raw.get("eventTicketLink", "")
                # Strip UTM params for cleaner URLs
                if ticket_url and "?" in ticket_url:
                    ticket_url = ticket_url.split("?")[0]

                # Show page URL on the venue website
                show_page_url = raw.get("url", "")

                events.append(
                    ComedyClubHaugEvent(
                        title=title,
                        subtitle=raw.get("eventSubtitle", ""),
                        start_time=start_time,
                        end_time=end_time,
                        ticket_url=ticket_url,
                        show_page_url=show_page_url,
                        performers=performers,
                    )
                )

            if not events:
                Logger.info(
                    f"{self._log_prefix}: no active events after filtering",
                    self.logger_context,
                )
                return None

            Logger.info(
                f"{self._log_prefix}: {len(events)} active events with tickets",
                self.logger_context,
            )
            return ComedyClubHaugPageData(event_list=events)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: error fetching {url}: {e}",
                self.logger_context,
            )
            return None
