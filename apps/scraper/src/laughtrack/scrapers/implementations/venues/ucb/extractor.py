"""Extractor for UCB WP Grid Builder show cards."""

from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.ucb import UCBEvent


class UCBExtractor:
    """Parse rendered WP Grid Builder cards into UCB events."""

    @staticmethod
    def extract_events(
        html: str,
        *,
        source_url: str,
        location_slug: Optional[str] = None,
    ) -> List[UCBEvent]:
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[UCBEvent] = []
        for card in soup.select("article.wpgb-card"):
            event = UCBExtractor._extract_card(card, source_url=source_url, location_slug=location_slug)
            if event:
                events.append(event)

        return events

    @staticmethod
    def _extract_card(
        card: Tag,
        *,
        source_url: str,
        location_slug: Optional[str],
    ) -> Optional[UCBEvent]:
        class_names = [str(cls) for cls in card.get("class", [])]
        if location_slug and location_slug not in class_names:
            return None

        title_link = card.select_one(".ucb-event-post-title a[href]")
        title = title_link.get_text(" ", strip=True) if title_link else ""
        show_page_url = urljoin(source_url, str(title_link.get("href"))) if title_link else ""
        if not title or not show_page_url:
            return None

        date_el = card.select_one(".event-post-date")
        date_text = date_el.get_text(" ", strip=True) if date_el else ""
        if "@" not in date_text:
            return None

        location_terms = card.select(".ucb-event-post-location .wpgb-block-term")
        physical_locations = [
            term.get_text(" ", strip=True)
            for term in location_terms
            if term.get_text(" ", strip=True).lower() != "livestream"
        ]
        location_name = physical_locations[0] if physical_locations else ""
        if not location_name:
            return None

        buy_link = card.select_one(".ucb-buy-now a[href]")
        ticket_url = urljoin(source_url, str(buy_link.get("href"))) if buy_link else show_page_url

        description_el = card.select_one(".ucb-event-post-excerpt")
        description = description_el.get_text(" ", strip=True) if description_el else ""

        matched_slug = location_slug or UCBExtractor._first_location_slug(class_names)
        return UCBEvent(
            title=title,
            date_text=date_text,
            show_page_url=show_page_url,
            ticket_url=ticket_url,
            location_slug=matched_slug,
            location_name=location_name,
            description=description,
        )

    @staticmethod
    def _first_location_slug(class_names: List[str]) -> str:
        for class_name in class_names:
            if class_name.startswith("la-") or class_name.startswith("nyc-") or class_name in {"la", "nyc"}:
                return class_name
        return ""
