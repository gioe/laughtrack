"""Comedy Works Downtown data extraction utilities."""

import re
from typing import List, Optional, Set

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.comedy_works_downtown import (
    ComedyWorksDowntownEvent,
    ComedyWorksDowntownShowtime,
)

_SLUG_RE = re.compile(r"/comedians/([\w-]+)")
_SECTION_ID_RE = re.compile(r"seating-sections-(\d+)")
_PRICE_RE = re.compile(r"\$(\d+(?:\.\d{2})?)")
_AGE_RE = re.compile(r"(\d+\+)")


class ComedyWorksDowntownExtractor:
    """Utility class for extracting Comedy Works Downtown event data from HTML."""

    @staticmethod
    def extract_comedian_slugs(html_content: str) -> List[str]:
        """
        Parse the events list page and return unique comedian slugs for Downtown shows.

        Args:
            html_content: HTML from /events?downtown=1

        Returns:
            Deduplicated list of comedian URL slugs (e.g. ["craig-conant", "nico-carney"])
        """
        soup = BeautifulSoup(html_content, "html.parser")
        boxes = soup.select("li.comedian-box")

        seen: Set[str] = set()
        slugs: List[str] = []

        for box in boxes:
            link = box.select_one("h2.comedian-box-title a")
            if not link:
                continue
            href = link.get("href", "")
            m = _SLUG_RE.search(href)
            if not m:
                continue
            slug = m.group(1)
            if slug not in seen:
                seen.add(slug)
                slugs.append(slug)

        return slugs

    @staticmethod
    def extract_events_from_detail(html_content: str, slug: str) -> List[ComedyWorksDowntownEvent]:
        """
        Parse a comedian detail page and extract all Downtown showtimes.

        Returns one ComedyWorksDowntownEvent per showtime (flattened for the
        pipeline's one-event-one-show contract).

        Args:
            html_content: HTML from /comedians/{slug}
            slug: The comedian's URL slug

        Returns:
            List of ComedyWorksDowntownEvent, one per Downtown showtime
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract comedian name
        h1 = soup.select_one("div.comedian-intro h1")
        name = h1.get_text(strip=True) if h1 else slug.replace("-", " ").title()

        # Find the Downtown ticket-location section
        showtimes = ComedyWorksDowntownExtractor._extract_downtown_showtimes(soup)

        return [
            ComedyWorksDowntownEvent(slug=slug, name=name, showtime=st)
            for st in showtimes
        ]

    @staticmethod
    def _extract_downtown_showtimes(soup: BeautifulSoup) -> List[ComedyWorksDowntownShowtime]:
        """Extract showtimes from the Downtown location section only."""
        # Find the Downtown club-title to scope to the right location
        downtown_title = soup.select_one("p.club-title.club-downtown")

        if downtown_title:
            # Navigate up to ticket-location container, then find its sibling show-times
            ticket_loc = downtown_title.find_parent("div", class_="ticket-location")
            if ticket_loc:
                show_list = ticket_loc.find_next_sibling("ul", class_="show-times")
            else:
                show_list = None
        else:
            # Fallback: if there's only one show-times list, use it
            all_lists = soup.select("ul.show-times")
            show_list = all_lists[0] if len(all_lists) == 1 else None

        if not show_list:
            return []

        items = show_list.find_all("li", recursive=False)
        showtimes: List[ComedyWorksDowntownShowtime] = []

        for item in items:
            st = ComedyWorksDowntownExtractor._parse_showtime(item)
            if st:
                showtimes.append(st)

        return showtimes

    @staticmethod
    def _parse_showtime(li: Tag) -> Optional[ComedyWorksDowntownShowtime]:
        """Parse a single showtime <li> element."""
        # Date/time: "Thursday, Apr 16 2026  7:15PM"
        day_el = li.select_one("p.show-day")
        datetime_str = day_el.get_text(strip=True) if day_el else ""
        if not datetime_str:
            return None

        # Age restriction from show-meta: "No Passes |     21+"
        meta_el = li.select_one("p.show-meta")
        meta_text = meta_el.get_text(strip=True) if meta_el else ""
        age_match = _AGE_RE.search(meta_text)
        age_restriction = age_match.group(1) if age_match else ""

        # Overall sold-out from button
        btn = li.select_one("button.seating-section-toggle")
        overall_sold_out = btn is not None and "sold-out" in btn.get("class", [])

        # Section ID
        sections_div = li.select_one("div.showtime-sections")
        section_id = ""
        if sections_div:
            sid = sections_div.get("id", "")
            m = _SECTION_ID_RE.search(sid)
            if m:
                section_id = m.group(1)

        # Ticket tiers
        tiers = []
        for fieldset in li.select("fieldset.ticket-select"):
            name_el = fieldset.select_one("span.product-name")
            price_el = fieldset.select_one("span.product-price")
            tier_sold = "sold-out" in fieldset.get("class", [])

            tier_name = name_el.get_text(strip=True) if name_el else "General Admission"
            tier_price = 0.0
            if price_el:
                pm = _PRICE_RE.search(price_el.get_text(strip=True))
                if pm:
                    tier_price = float(pm.group(1))

            tiers.append({
                "name": tier_name,
                "price": tier_price,
                "sold_out": tier_sold,
            })

        return ComedyWorksDowntownShowtime(
            datetime_str=datetime_str,
            age_restriction=age_restriction,
            sold_out=overall_sold_out,
            tiers=tiers,
            section_id=section_id,
        )
