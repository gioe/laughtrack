"""
HTML extraction for The Bit Theater Odoo event pages.

The Bit Theater (bitimprov.org) runs on Odoo CMS. The events listing page
at /event renders Schema.org-annotated article cards inside <a> wrappers.

Each article card provides:
  - Event name (itemprop="name")
  - Start date (meta itemprop="startDate" with UTC ISO datetime)
  - Category badges (span.badge elements — e.g., "Stand-up", "Short Form", "Play")
  - Event URL (parent <a> href)

The detail page at /event/{slug}/ adds:
  - Price (span itemprop="price")
  - End date (meta itemprop="endDate")

Pagination uses /event/page/N links in a <ul class="pagination"> element.
"""

import re
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.the_bit_theater import BitTheaterEvent, is_comedy_relevant
from laughtrack.foundation.infrastructure.logger.logger import Logger

_BASE_URL = "https://www.bitimprov.org"


class BitTheaterExtractor:
    """Extracts show data from The Bit Theater's Odoo event pages."""

    @staticmethod
    def extract_listing_events(
        html: str,
    ) -> Tuple[List[BitTheaterEvent], Optional[str]]:
        """
        Extract events from an Odoo event listing page.

        Returns:
            Tuple of (list of comedy-relevant BitTheaterEvents, next_page_url or None).
        """
        if not html:
            return [], None

        soup = BeautifulSoup(html, "html.parser")
        events: List[BitTheaterEvent] = []

        for article in soup.select("article"):
            event = BitTheaterExtractor._parse_article(article)
            if event is not None:
                events.append(event)

        next_url = BitTheaterExtractor._find_next_page(soup)
        return events, next_url

    @staticmethod
    def _parse_article(article: Tag) -> Optional[BitTheaterEvent]:
        """Parse a single article card into a BitTheaterEvent, or None if filtered out."""
        # Event name
        name_el = article.select_one("[itemprop=name]")
        if not name_el:
            return None
        title = name_el.get_text(strip=True)
        if not title:
            return None

        # Start date from meta tag
        start_meta = article.select_one("meta[itemprop=startDate]")
        start_dt = start_meta["content"] if start_meta and start_meta.get("content") else None
        if not start_dt:
            return None

        # Category badges (exclude pagination badges)
        badges = [
            b.get_text(strip=True)
            for b in article.select("span.badge")
            if "pagination" not in b.get("class", [])
        ]

        # Filter: only comedy-relevant events
        if not is_comedy_relevant(badges):
            return None

        # Event URL from parent <a> tag
        parent_link = article.find_parent("a", href=True)
        href = parent_link["href"] if parent_link else None
        if not href:
            return None

        # Normalize: strip /register suffix, ensure full URL
        href = re.sub(r"/register/?$", "/", href)
        if href.startswith("/"):
            href = _BASE_URL + href

        return BitTheaterEvent(
            title=title,
            start_datetime_utc=start_dt,
            event_url=href,
            categories=badges,
        )

    @staticmethod
    def _find_next_page(soup: BeautifulSoup) -> Optional[str]:
        """Find the next pagination page URL, if any."""
        pager = soup.select_one("ul.pagination")
        if not pager:
            return None

        # The active page is marked with class "active"; find the next sibling <li>
        active = pager.select_one("li.page-item.active")
        if not active:
            return None

        next_li = active.find_next_sibling("li", class_="page-item")
        if not next_li or "disabled" in next_li.get("class", []):
            return None

        link = next_li.select_one("a.page-link[href]")
        if not link:
            return None

        href = link["href"]
        if href.startswith("/"):
            href = _BASE_URL + href

        return href

    @staticmethod
    def extract_detail_price(html: str) -> Optional[float]:
        """
        Extract the ticket price from an event detail page.

        Returns:
            Price as float, or None if not found.
        """
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        # Odoo uses itemprop="price" in a hidden span
        price_el = soup.select_one("[itemprop=price]")
        if price_el:
            try:
                return float(price_el.get_text(strip=True))
            except (ValueError, TypeError):
                pass

        # Fallback: look for $XX pattern in the ticket section
        ticket_section = soup.select_one("#o_wevent_tickets, #modal_ticket_registration")
        if ticket_section:
            price_match = re.search(r"\$\s*([\d.]+)", ticket_section.get_text())
            if price_match:
                try:
                    return float(price_match.group(1))
                except (ValueError, TypeError):
                    pass

        return None
