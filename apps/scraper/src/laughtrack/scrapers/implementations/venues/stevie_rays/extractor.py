"""HTML extraction for the Stevie Ray's Comedy Cabaret ticketing page."""

from typing import List, Optional

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.stevie_rays import StevieRaysEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

LISTING_URL = "https://tickets.chanhassendt.com/Online/default.asp?BOparam::WScontent::loadArticle::permalink=stevierays"


class StevieRaysExtractor:
    """
    Parses the Chanhassen Dinner Theatres ticketing page for Stevie Ray's.

    The page at:
      https://tickets.chanhassendt.com/Online/default.asp?BOparam::WScontent::loadArticle::permalink=stevierays

    renders each upcoming show as a div.result-box-item. Relevant fields:

    - div.item-name     — show title (always "Stevie Ray's Comedy Cabaret")
    - span.start-date   — date+time string (e.g. "Friday, April 03, 2026 @ 7:30 PM")

    No per-event ticket URL is available (Buy buttons open a JS modal with no href).
    The listing page URL is used as the ticket URL for all shows.
    """

    @staticmethod
    def extract_events(html: str, listing_url: str = LISTING_URL) -> List[StevieRaysEvent]:
        """Extract all event rows from the ticketing listing page."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[StevieRaysEvent] = []

        for row in soup.find_all("div", class_="result-box-item"):
            event = StevieRaysExtractor._parse_row(row, listing_url)
            if event is not None:
                events.append(event)

        return events

    @staticmethod
    def _parse_row(row, listing_url: str) -> Optional[StevieRaysEvent]:
        """Parse a single div.result-box-item and return a StevieRaysEvent or None."""
        title_el = row.find("div", class_="item-name")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            Logger.debug("StevieRaysExtractor: skipping row — no item-name")
            return None

        date_el = row.find("span", class_="start-date")
        start_date_str = date_el.get_text(strip=True) if date_el else ""
        if not start_date_str:
            Logger.debug(f"StevieRaysExtractor: skipping '{title}' — no start-date span")
            return None

        return StevieRaysEvent(
            title=title,
            start_date_str=start_date_str,
            ticket_url=listing_url,
        )
