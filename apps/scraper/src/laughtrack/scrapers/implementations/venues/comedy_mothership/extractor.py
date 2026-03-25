"""Comedy Mothership data extraction utilities."""

import re
from typing import List

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.comedy_mothership import ComedyMothershipEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

_SHOW_ID_RE = re.compile(r"/shows/(\d+)")
_GENERIC_TITLE_RE = re.compile(
    r"\b(showcase|open mic|roast battle|story warz|best of|bottom of|kill tony|mothership|episode)\b"
    r"|presents:",
    re.IGNORECASE,
)
_AND_FRIENDS_RE = re.compile(r"\s+and\s+friends?\s*$", re.IGNORECASE)


class ComedyMothershipEventExtractor:
    """Utility class for extracting Comedy Mothership event data from HTML."""

    @staticmethod
    def extract_shows(html_content: str, timezone: str) -> List[ComedyMothershipEvent]:
        """
        Parse show list items from the Comedy Mothership shows page HTML.

        Args:
            html_content: Raw HTML from comedymothership.com/shows
            timezone: IANA timezone string (e.g. "America/Chicago")

        Returns:
            List of ComedyMothershipEvent objects
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            share_links = soup.find_all(
                "a",
                href=lambda h: h and "/shows/" in h and "comedymothership.com" in h,
            )
            events: List[ComedyMothershipEvent] = []
            seen_ids: set = set()
            for link in share_links:
                m = _SHOW_ID_RE.search(link["href"])
                if not m:
                    continue
                show_id = m.group(1)
                if show_id in seen_ids:
                    continue
                seen_ids.add(show_id)

                li = link.find_parent("li")
                if li is None:
                    continue

                event = ComedyMothershipEventExtractor._parse_show_item(li, show_id, timezone)
                if event is not None:
                    events.append(event)
            return events
        except Exception as e:
            Logger.error(f"ComedyMothershipEventExtractor: failed to parse HTML: {e}")
            return []

    @staticmethod
    def _parse_show_item(li, show_id: str, timezone: str):
        """Parse a single show <li> into a ComedyMothershipEvent."""
        try:
            date_div = li.find("div", class_="h6")
            date_str = date_div.get_text(strip=True) if date_div else ""

            title_h3 = li.find("h3")
            title = title_h3.get_text(strip=True) if title_h3 else "Comedy Show"

            details_ul = li.find("ul")
            time_str = ""
            room = ""
            if details_ul:
                items = details_ul.find_all("li")
                if items:
                    time_str = items[0].get_text(strip=True)
                if len(items) > 1:
                    room = items[1].get_text(strip=True)

            buttons = li.find_all("button")
            sold_out = any(
                "sold out" in (b.get_text(strip=True) or "").lower() for b in buttons
            )

            performers = ComedyMothershipEventExtractor._extract_performers(title)

            return ComedyMothershipEvent(
                show_id=show_id,
                title=title,
                date_str=date_str,
                time_str=time_str,
                room=room,
                timezone=timezone,
                performers=performers,
                sold_out=sold_out,
            )
        except Exception as e:
            Logger.error(
                f"ComedyMothershipEventExtractor: failed to parse show item id={show_id}: {e}"
            )
            return None

    @staticmethod
    def _extract_performers(title: str) -> List[str]:
        """
        Derive comedian name(s) from the show title.

        - "[Name] and Friends" → ["[Name]"]
        - Generic titles (Showcase, Open Mic, etc.) → []
        - Otherwise → [title] (assumed to be comedian's name)
        """
        if _GENERIC_TITLE_RE.search(title):
            return []
        name = _AND_FRIENDS_RE.sub("", title).strip()
        return [name] if name else []
