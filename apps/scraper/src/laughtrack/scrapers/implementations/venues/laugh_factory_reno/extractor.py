"""
Laugh Factory Reno data extraction utilities.

Parses the Laugh Factory CMS HTML page (www.laughfactory.com/reno) to extract
upcoming show listings.  Shows are server-rendered as `.show-sec.jokes` divs by
the Laugh Factory `getJokesHtml` JS template.

HTML structure per show:

    <div class="show-sec jokes">
      <div class="shedule">
        <span class="date">Wed\\xa0Mar 25</span>
        <span class="timing">7:00 PM</span>
        <div class="tickets">
          <a href="https://www.laughfactory.club/checkout/show/{punchup_id}"
             class="readmore-btn ticket-toggle-btn">Buy Tickets</a>
        </div>
      </div>
      <div class="show-content">
        <div class="show-top-content-sec">
          <h4>{show title}</h4>
          <div class="show-thumbnails-sec">
            <figure><figcaption>{comedian name}</figcaption></figure>
            ...
          </div>
        </div>
      </div>
    </div>

The date span contains a non-breaking space (\\xa0) between the weekday abbreviation
and the month-day string.  The weekday prefix is stripped before storing in the
TixologiEvent so the entity can infer the year independently.
"""

import re
from typing import List

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.tixologi import TixologiEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

_TICKET_URL_RE = re.compile(r"https://www\.laughfactory\.club/checkout/show/([^/?#]+)")


class LaughFactoryRenoEventExtractor:
    """Utility class for extracting Laugh Factory Reno event data from HTML."""

    @staticmethod
    def extract_shows(html_content: str, club_id: int, timezone: str) -> List[TixologiEvent]:
        """
        Parse `.show-sec.jokes` divs from the Laugh Factory Reno CMS page.

        Args:
            html_content: Raw HTML from www.laughfactory.com/reno
            club_id: Database ID for the club record
            timezone: IANA timezone string for date interpretation

        Returns:
            List of TixologiEvent objects (may be empty if no shows are listed)
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            show_divs = soup.select("div.show-sec.jokes")

            events: List[TixologiEvent] = []
            for div in show_divs:
                event = LaughFactoryRenoEventExtractor._parse_show_div(div, club_id, timezone)
                if event is not None:
                    events.append(event)

            return events

        except Exception as e:
            Logger.error(f"LaughFactoryRenoEventExtractor: failed to parse HTML: {e}")
            return []

    @staticmethod
    def _parse_show_div(div, club_id: int, timezone: str):
        """Parse a single `.show-sec.jokes` div into a TixologiEvent."""
        try:
            # --- Date ---
            date_span = div.select_one(".shedule span.date")
            if not date_span:
                return None
            raw_date = date_span.get_text()
            # Strip weekday prefix — "Wed\xa0Mar 25" → "Mar 25"
            if "\xa0" in raw_date:
                date_str = raw_date.split("\xa0", 1)[1].strip()
            else:
                # Fallback: skip first word
                parts = raw_date.strip().split(None, 1)
                date_str = parts[1] if len(parts) > 1 else raw_date.strip()

            # --- Time ---
            time_span = div.select_one(".shedule span.timing")
            time_str = time_span.get_text().strip() if time_span else "8:00 PM"

            # --- Ticket URL ---
            ticket_anchor = div.select_one(".tickets a.ticket-toggle-btn")
            ticket_url = ""
            punchup_id = None
            if ticket_anchor:
                ticket_url = ticket_anchor.get("href", "").strip()
                m = _TICKET_URL_RE.match(ticket_url)
                if m:
                    punchup_id = m.group(1)

            # --- Title ---
            title_tag = div.select_one(".show-top-content-sec h4")
            title = title_tag.get_text(strip=True) if title_tag else "Comedy Show"

            # --- Comedian names ---
            figcaptions = div.select(".show-thumbnails-sec figure figcaption")
            comedians = [fc.get_text(strip=True) for fc in figcaptions if fc.get_text(strip=True)]

            return TixologiEvent(
                club_id=club_id,
                title=title,
                date_str=date_str,
                time_str=time_str,
                ticket_url=ticket_url,
                timezone=timezone,
                comedians=comedians,
                punchup_id=punchup_id,
            )

        except Exception as e:
            Logger.error(f"LaughFactoryRenoEventExtractor: failed to parse show div: {e}")
            return None
