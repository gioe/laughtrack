"""
HTML extractor for The Comedy Store calendar pages.

Each day page at thecomedystore.com/{location}/calendar/YYYY-MM-DD renders a
list of show-item divs.  Supported locations: West Hollywood (no prefix) and
La Jolla (/la-jolla).  For each item the extractor reads:
  - title            from h2.show-title > a  (desktop section)
  - datetime_slug    from that anchor's href: /{location}/calendar/show/{id}/{slug}
  - room             from h3.text-white.text-uppercase (excluding the aria-hidden abbreviation)
  - ticket_url       from the first showclix.com/event/ anchor; falls back to the
                     comedy store show-page URL when the show is sold out or free
  - sold_out         True when a "SOLD OUT" alert is present in the item
"""

import re
from typing import List

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.comedy_store import ComedyStoreEvent


_SHOWCLIX_RE = re.compile(r"showclix\.com/event/", re.IGNORECASE)
_SHOW_HREF_RE = re.compile(r"^(?:/[^/]+)?/calendar/show/\d+/(.+)$")
_SLUG_DT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[tT]\d{6}[+-]\d{4}")


class ComedyStoreEventExtractor:
    """Static extractor for Comedy Store daily calendar HTML."""

    @staticmethod
    def extract_shows(html: str) -> List[ComedyStoreEvent]:
        """Parse a Comedy Store calendar day page and return all show events.

        Each show-item div is parsed once (using the desktop section to avoid
        duplicating the mobile/desktop title that appears twice in the markup).
        Shows are deduplicated by datetime slug.
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[ComedyStoreEvent] = []
        seen_slugs: set = set()

        for item in soup.find_all("div", class_=lambda c: c and "show-item" in c.split()):
            # Use the desktop section (d-none d-sm-block) to avoid duplicate title
            desktop = item.find(
                "div",
                class_=lambda c: c and "d-none" in c.split() and "d-sm-block" in c.split(),
            )
            if desktop is None:
                desktop = item  # fall back to the full item if structure differs

            # --- title + datetime slug ---
            title_a = desktop.find("a", href=_SHOW_HREF_RE)
            if title_a is None:
                continue

            m = _SHOW_HREF_RE.match(title_a["href"])
            if not m:
                continue
            slug = m.group(1)  # e.g. "2026-03-25t200000-0700-bassem-friends..."

            # Only keep the datetime portion of the slug
            dt_m = _SLUG_DT_RE.match(slug)
            if not dt_m:
                continue
            datetime_slug = dt_m.group(0)

            # Dedup by full slug (unique per show) — not datetime only, because
            # multiple shows can start at the same time in different rooms.
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            title = title_a.get_text(strip=True)
            if not title:
                continue

            # --- room ---
            room = ""
            room_h3 = desktop.find(
                "h3",
                class_=lambda c: c and "text-white" in c.split() and "text-uppercase" in c.split(),
            )
            if room_h3:
                for abbr_span in room_h3.find_all("span", {"aria-hidden": "true"}):
                    abbr_span.decompose()
                room = room_h3.get_text(strip=True)

            # --- ticket URL ---
            ticket_a = item.find("a", href=_SHOWCLIX_RE)
            if ticket_a:
                ticket_url = ticket_a["href"].rstrip('"').strip()
            else:
                # sold-out or free — use the Comedy Store show page
                ticket_url = f"https://thecomedystore.com{title_a['href']}"

            # --- sold out ---
            sold_out = bool(
                item.find(string=re.compile(r"SOLD\s+OUT", re.IGNORECASE))
            )

            events.append(
                ComedyStoreEvent(
                    title=title,
                    datetime_slug=datetime_slug,
                    ticket_url=ticket_url,
                    room=room,
                    sold_out=sold_out,
                )
            )

        return events
