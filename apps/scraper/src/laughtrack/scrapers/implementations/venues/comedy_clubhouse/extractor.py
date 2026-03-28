"""HTML extraction for The Comedy Clubhouse TicketSource listing page."""

from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.comedy_clubhouse import (
    ComedyClubhouseEvent,
    TICKETSOURCE_BASE,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ComedyClubhouseExtractor:
    """
    Parses the TicketSource listing page for The Comedy Clubhouse.

    The page at https://www.ticketsource.com/thecomedyclubhouse renders each
    upcoming show as a ``div.eventRow`` element.  Relevant fields:

    - ``div.eventTitle > a > span[itemprop="name"]``   — show title
    - ``div.eventTitle > a[href]``                     — show page path
    - ``div.dateTime[content]``                        — ISO start datetime
      (e.g. "2026-03-28T19:30", local Chicago time)
    - ``div.event-btn > a[href]``                      — ticket purchase path
    """

    @staticmethod
    def extract_events(html: str) -> List[ComedyClubhouseEvent]:
        """Extract all event cards from the TicketSource listing page."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[ComedyClubhouseEvent] = []

        for row in soup.find_all("div", class_="eventRow"):
            event = ComedyClubhouseExtractor._parse_row(row)
            if event is not None:
                events.append(event)

        return events

    @staticmethod
    def _parse_row(row) -> Optional[ComedyClubhouseEvent]:
        """Parse a single div.eventRow and return a ComedyClubhouseEvent or None."""
        # Title
        title_tag = row.find("span", itemprop="name")
        if not title_tag:
            Logger.debug("ComedyClubhouseExtractor: skipping row — no title span")
            return None
        title = title_tag.get_text(strip=True)

        # Show page URL — urljoin handles both relative and absolute hrefs safely
        title_link = row.find("div", class_="eventTitle")
        show_url = ""
        if title_link:
            a_tag = title_link.find("a", itemprop="url")
            if a_tag and a_tag.get("href"):
                show_url = urljoin(TICKETSOURCE_BASE, a_tag["href"])

        # ISO start datetime from content= attribute
        datetime_div = row.find("div", class_="dateTime")
        if not datetime_div:
            Logger.debug(
                f"ComedyClubhouseExtractor: skipping '{title}' — no dateTime div"
            )
            return None
        start_iso = datetime_div.get("content", "").strip()
        if not start_iso:
            Logger.debug(
                f"ComedyClubhouseExtractor: skipping '{title}' — empty content attribute"
            )
            return None

        # Ticket purchase URL — urljoin handles both relative and absolute hrefs safely
        btn_div = row.find("div", class_="event-btn")
        if not btn_div:
            Logger.debug(
                f"ComedyClubhouseExtractor: skipping '{title}' — no event-btn div"
            )
            return None
        btn_a = btn_div.find("a")
        ticket_href = (btn_a.get("href") or "").strip() if btn_a else ""
        if not ticket_href:
            Logger.debug(
                f"ComedyClubhouseExtractor: skipping '{title}' — no ticket href"
            )
            return None
        ticket_url = urljoin(TICKETSOURCE_BASE, ticket_href)

        return ComedyClubhouseEvent(
            title=title,
            start_iso=start_iso,
            show_url=show_url,
            ticket_url=ticket_url,
        )
