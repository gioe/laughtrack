"""HTML extraction for the Sports Drink OpenDate listing page."""

from typing import List, Optional

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.sports_drink import SportsDrinkEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class SportsDrinkExtractor:
    """
    Parses the OpenDate listing page for Sports Drink.

    The page at https://app.opendate.io/v/sports-drink-1939?per_page=500
    renders each upcoming show as a div.confirm-card element. Relevant fields:

    - p.mb-0.text-dark > a.stretched-link[href]  — event/ticket URL
    - p.mb-0.text-dark > a > strong              — show title
    - first p.mb-0 (no text-dark, no text-truncate) — date ("March 29, 2026")
    - second p.mb-0 (no text-dark, no text-truncate) — time ("Doors: X PM - Show: X PM")
    """

    @staticmethod
    def extract_events(html: str) -> List[SportsDrinkEvent]:
        """Extract all event cards from the OpenDate listing page."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[SportsDrinkEvent] = []

        for card in soup.find_all("div", class_="confirm-card"):
            event = SportsDrinkExtractor._parse_card(card)
            if event is not None:
                events.append(event)

        return events

    @staticmethod
    def _parse_card(card) -> Optional[SportsDrinkEvent]:
        """Parse a single div.confirm-card and return a SportsDrinkEvent or None."""
        body = card.find("div", class_="card-body")
        if not body:
            return None

        # Title and event URL from stretched-link anchor
        link = body.find("a", class_="stretched-link")
        if not link:
            Logger.debug("SportsDrinkExtractor: skipping card — no stretched-link anchor")
            return None

        event_url = (link.get("href") or "").strip()
        if not event_url:
            Logger.debug("SportsDrinkExtractor: skipping card — empty href")
            return None

        strong = link.find("strong")
        title = strong.get_text(strip=True) if strong else link.get_text(strip=True)
        if not title:
            Logger.debug("SportsDrinkExtractor: skipping card — empty title")
            return None

        # Collect the blue info paragraphs (not text-dark, not text-truncate)
        info_paras = [
            p for p in body.find_all("p", class_="mb-0")
            if "text-dark" not in (p.get("class") or [])
            and "text-truncate" not in (p.get("class") or [])
        ]

        if len(info_paras) < 2:
            Logger.debug(
                f"SportsDrinkExtractor: skipping '{title}' — fewer than 2 info paragraphs"
            )
            return None

        date_str = info_paras[0].get_text(strip=True)
        time_str = info_paras[1].get_text(strip=True)

        if not date_str or not time_str:
            Logger.debug(
                f"SportsDrinkExtractor: skipping '{title}' — empty date or time"
            )
            return None

        return SportsDrinkEvent(
            title=title,
            date_str=date_str,
            time_str=time_str,
            event_url=event_url,
        )
