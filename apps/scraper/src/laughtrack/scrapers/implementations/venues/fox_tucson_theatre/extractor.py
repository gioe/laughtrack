"""Extract official Fox Tucson Theatre event data."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

from laughtrack.core.entities.event.fox_tucson_theatre import FoxTucsonTheatreEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper


class FoxTucsonTheatreExtractor:
    """Parsers for foxtucson.com WordPress cards and Spektrix detail pages."""

    BASE_URL = "https://foxtucson.com"
    _COMEDY_CLASSES = {"comedy", "outburst-comedy"}
    _MONTHS = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    @classmethod
    def extract_events(
        cls,
        html_content: str,
        source_url: str = "https://foxtucson.com/events/",
        reference_date: Optional[date] = None,
    ) -> List[FoxTucsonTheatreEvent]:
        """Extract official comedy event cards from the calendar page."""
        if not html_content:
            return []

        soup = HtmlScraper._parse_html(html_content)
        events: List[FoxTucsonTheatreEvent] = []
        for card in soup.select("div.event-card"):
            card_classes = [str(value) for value in card.get("class", [])]
            if not cls._is_comedy_card(card_classes):
                continue

            title_tag = card.select_one(".details h1")
            title = title_tag.get_text(" ", strip=True) if title_tag else ""
            if not title:
                continue

            subtitle_tag = card.select_one(".details h2, .details h3, .subtitle")
            subtitle = subtitle_tag.get_text(" ", strip=True) if subtitle_tag else ""

            show_page_url = cls._extract_show_page_url(card, source_url)
            ticket_link = card.select_one(".tickets a[href]")
            ticket_url = cls._absolute_url(ticket_link.get("href"), source_url) if ticket_link else ""
            price_text = ticket_link.get_text(" ", strip=True) if ticket_link else ""

            show_datetime = cls._extract_card_datetime(card, reference_date=reference_date)
            if not show_page_url or not ticket_url or show_datetime is None:
                Logger.warn(
                    f"Skipping incomplete Fox Tucson event card title={title!r} show_url={show_page_url!r} ticket_url={ticket_url!r}"
                )
                continue

            events.append(
                FoxTucsonTheatreEvent(
                    title=title,
                    subtitle=subtitle,
                    date_time=show_datetime,
                    show_page_url=show_page_url,
                    ticket_url=ticket_url,
                    price_text=price_text,
                    card_classes=card_classes,
                )
            )

        return events

    @classmethod
    def extract_spektrix_iframe_url(
        cls, html_content: str, source_url: str = "https://foxtucson.com"
    ) -> Optional[str]:
        """Extract the Spektrix EventDetails iframe URL from a WordPress ticket page."""
        if not html_content:
            return None

        soup = HtmlScraper._parse_html(html_content)
        iframe = soup.find("iframe", src=lambda value: value and "EventDetails.aspx" in value)
        if not iframe:
            return None

        src = iframe.get("src", "")
        return cls._absolute_url(src, source_url)

    @staticmethod
    def extract_web_event_id(spektrix_event_url: Optional[str]) -> Optional[str]:
        if not spektrix_event_url:
            return None
        parsed = urlparse(spektrix_event_url)
        values = parse_qs(parsed.query).get("WebEventId")
        return values[0] if values else None

    @staticmethod
    def extract_spektrix_instance_ids(html_content: str) -> List[str]:
        """Extract Spektrix instance IDs from the EventDatesList options."""
        if not html_content:
            return []

        soup = HtmlScraper._parse_html(html_content)
        ids: List[str] = []
        for option in soup.select("select.EventDatesList option[value]"):
            value = option.get("value", "").strip()
            if value:
                ids.append(value)
        return ids

    @classmethod
    def _is_comedy_card(cls, card_classes: List[str]) -> bool:
        tokens = {value.lower() for value in card_classes}
        return bool(tokens & cls._COMEDY_CLASSES)

    @classmethod
    def _extract_show_page_url(cls, card, source_url: str) -> str:
        for link in card.select(".details a[href], a[href]"):
            href = link.get("href", "")
            if "/event/" in href and not href.rstrip("/").endswith("/tickets"):
                return cls._absolute_url(href, source_url)
        return ""

    @classmethod
    def _extract_card_datetime(
        cls, card, reference_date: Optional[date] = None
    ) -> Optional[datetime]:
        day_text = cls._select_text(card, ".day-of-month")
        month_text = cls._select_text(card, ".month")
        time_text = cls._select_text(card, ".time")
        if not day_text or not month_text or not time_text:
            return None

        try:
            month = cls._MONTHS[month_text.strip().lower()]
            day = int(day_text.strip())
            parsed_time = datetime.strptime(time_text.strip().lower(), "%I:%M %p").time()
        except (KeyError, ValueError):
            return None

        today = reference_date or date.today()
        year = today.year
        candidate = date(year, month, day)
        if candidate < today:
            year += 1
        return datetime.combine(date(year, month, day), parsed_time)

    @staticmethod
    def _select_text(card, selector: str) -> str:
        element = card.select_one(selector)
        return element.get_text(" ", strip=True) if element else ""

    @classmethod
    def _absolute_url(cls, url: str, source_url: str) -> str:
        base = source_url or cls.BASE_URL
        return urljoin(base, url.replace("&amp;", "&").strip())
