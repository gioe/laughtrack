"""
New York Comedy Club JSON-LD scraper with address-based location filtering.

NYCC operates three venues (Midtown, East Village, Upper West Side) on a single
shared calendar page at newyorkcomedyclub.com/calendar. This scraper extends the
generic JSON-LD pattern to filter events by matching the JSON-LD
location.address.streetAddress against the club's database address, so each club
record only receives its own venue's shows.
"""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.event import (
    JsonLdEvent,
    Offer,
    Person,
    Place,
    PostalAddress,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import NewYorkComedyClubPageData
from .transformer import NewYorkComedyClubTransformer


class NewYorkComedyClubScraper(BaseScraper):
    """JSON-LD scraper that filters events by the club's street address."""

    key = "new_york_comedy_club"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(
            NewYorkComedyClubTransformer(club)
        )

    async def get_data(self, url: str) -> Optional[NewYorkComedyClubPageData]:
        from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor

        try:
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(normalized_url)

            rendered_events = _extract_rendered_calendar_events(html_content, self.club.timezone)
            event_list = rendered_events or EventExtractor.extract_events(html_content)
            if not event_list:
                if html_content:
                    Logger.warn(
                        f"{self._log_prefix}: Page loaded but contained no JSON-LD events: {normalized_url}",
                        self.logger_context,
                    )
                return None

            # Filter events whose street address matches this club's address
            club_street = _normalize_street(self.club.address)
            filtered = []
            for event in event_list:
                event_street = _normalize_street(
                    event.location.address.street_address
                    if event.location and event.location.address
                    else ""
                )
                if club_street and event_street and club_street == event_street:
                    filtered.append(event)

            Logger.info(
                f"{self._log_prefix}: {len(filtered)}/{len(event_list)} events matched address '{self.club.address}'",
                self.logger_context,
            )

            if not filtered:
                return None

            return NewYorkComedyClubPageData(event_list=filtered)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error extracting data from {url}: {e}",
                self.logger_context,
            )
            return None


def _normalize_street(address: str) -> str:
    """Normalize a street address for comparison.

    Strips city/state/zip (first comma-delimited segment only),
    lowercases, and normalizes common abbreviations so that
    '85 E 4th St' matches '85 East 4th Street'.
    """
    if not address:
        return ""

    street = address.split(",")[0].strip().lower().rstrip(".")

    replacements = {
        " street": " st",
        " avenue": " ave",
        " boulevard": " blvd",
        " drive": " dr",
        " road": " rd",
        " place": " pl",
        " east ": " e ",
        " west ": " w ",
        " north ": " n ",
        " south ": " s ",
    }
    for old, new in replacements.items():
        street = street.replace(old, new)

    return street


_VENUE_STREET_BY_LABEL = {
    "midtown": "241 East 24th Street",
    "east village": "85 East 4th Street",
    "upper west side": "236 W 78th Street",
}

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _extract_rendered_calendar_events(html_content: str, timezone: str) -> list[JsonLdEvent]:
    """Extract current calendar cards rendered in the NYCC HTML.

    The page's JSON-LD can lag behind the visible calendar. The visible
    ``upcoming-container-list`` cards are the source of truth for current shows.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")
    base_year, base_month = _extract_calendar_base_date(soup)
    if not base_year or not base_month:
        return []

    events: list[JsonLdEvent] = []
    seen_urls: set[str] = set()
    for card in soup.select(".upcoming-container-list"):
        event = _event_from_rendered_card(card, base_year, base_month, timezone)
        if event is None or event.url in seen_urls:
            continue
        seen_urls.add(event.url)
        events.append(event)
    return events


def _extract_calendar_base_date(soup) -> tuple[Optional[int], Optional[int]]:
    title = soup.find("title")
    text = title.get_text(" ", strip=True) if title else ""
    match = re.search(r"for\s+([A-Za-z]+)\s+(\d{4})", text)
    if not match:
        meta = soup.find("meta", attrs={"name": "description"})
        text = meta.get("content", "") if meta else ""
        match = re.search(r"for\s+([A-Za-z]+)\s+(\d{4})", text)
    if not match:
        return None, None
    month = _MONTHS.get(match.group(1).lower())
    return int(match.group(2)), month


def _event_from_rendered_card(
    card,
    base_year: int,
    base_month: int,
    timezone: str,
) -> Optional[JsonLdEvent]:
    date_items = [item.get_text(" ", strip=True) for item in card.select(".event-date-ul li")]
    if len(date_items) < 3:
        return None

    start_date = _parse_card_datetime(date_items[1], date_items[2], base_year, base_month, timezone)
    if start_date is None:
        return None

    name_node = card.select_one(".scheduled-name a")
    raw_name = name_node.get_text(" ", strip=True) if name_node else ""
    name = _clean_card_name(raw_name)
    if not name:
        return None

    venue_node = card.select_one(".scheduled-venue")
    venue_label = venue_node.get_text(" ", strip=True) if venue_node else ""
    street_address = _VENUE_STREET_BY_LABEL.get(venue_label.lower(), "")

    href = name_node.get("href") if name_node else None
    if not href:
        link = card.find("a", href=True)
        href = link.get("href") if link else ""
    event_url = urljoin("https://newyorkcomedyclub.com", href)

    description_node = card.select_one(".scheduled-description")
    description = description_node.get_text(" ", strip=True) if description_node else ""
    performers = [Person(name=performer) for performer in _extract_performer_names(name)]

    return JsonLdEvent(
        name=name,
        start_date=start_date,
        location=Place(
            name=venue_label or "New York Comedy Club",
            address=PostalAddress(
                street_address=street_address,
                address_locality="New York",
                postal_code="",
                address_region="NY",
                address_country="US",
            ),
        ),
        offers=[
            Offer(
                url=event_url,
                price_currency="USD",
                price="0",
                availability="",
            )
        ],
        url=event_url,
        description=description,
        performers=performers,
        same_as=event_url,
    )


def _parse_card_datetime(
    month_day: str,
    time_text: str,
    base_year: int,
    base_month: int,
    timezone: str,
) -> Optional[datetime]:
    match = re.match(r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?", month_day.strip())
    if not match:
        return None
    month = _MONTHS.get(match.group(1).lower())
    if not month:
        return None
    day = int(match.group(2))
    year = base_year + 1 if month < base_month else base_year
    try:
        parsed_time = datetime.strptime(time_text.strip().upper(), "%I:%M%p").time()
        return datetime(year, month, day, parsed_time.hour, parsed_time.minute, tzinfo=ZoneInfo(timezone))
    except ValueError:
        return None


def _clean_card_name(raw_name: str) -> str:
    return re.sub(r"\s+at\s*$", "", raw_name).strip()


def _extract_performer_names(show_name: str) -> list[str]:
    name_source = show_name
    featured = re.search(r"\b(?:ft:?|featuring|w/|with)\s+(.+)$", show_name, re.IGNORECASE)
    if featured:
        name_source = featured.group(1)

    name_source = re.sub(r"\+?\s*special guests?.*$", "", name_source, flags=re.IGNORECASE)
    parts = [part.strip(" .") for part in re.split(r",|\s+\+\s+", name_source) if part.strip(" .")]
    return [part for part in parts if _looks_like_performer_name(part)]


def _looks_like_performer_name(name: str) -> bool:
    lower = name.lower()
    blocked = (
        "new york comedy club",
        "presents",
        "open mic",
        "comedy mob",
        "laughing buddha",
        "new jokes",
        "the lineup",
    )
    if any(token in lower for token in blocked):
        return False
    words = name.split()
    return 1 <= len(words) <= 5 and len(name) <= 60
