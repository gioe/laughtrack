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
from urllib.parse import urljoin, urlparse, urlunparse
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
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.base.base_scraper import BaseScraper

from .data import NewYorkComedyClubPageData
from .transformer import NewYorkComedyClubTransformer


class NewYorkComedyClubScraper(BaseScraper):
    """JSON-LD scraper that filters events by the club's street address."""

    key = "new_york_comedy_club"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(NewYorkComedyClubTransformer(club))

    async def get_data(self, url: str) -> Optional[NewYorkComedyClubPageData]:
        from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor

        try:
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(normalized_url)

            json_ld_events = EventExtractor.extract_events(html_content)
            rendered_events = _extract_rendered_calendar_events(html_content, self.club.timezone)
            event_list = (
                _enrich_rendered_events_from_json_ld(rendered_events, json_ld_events)
                if rendered_events
                else json_ld_events
            )
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
                    event.location.address.street_address if event.location and event.location.address else ""
                )
                if club_street and event_street and club_street == event_street:
                    filtered.append(event)

            Logger.info(
                f"{self._log_prefix}: {len(filtered)}/{len(event_list)} events matched address '{self.club.address}'",
                self.logger_context,
            )

            if not filtered:
                return None

            await self._enrich_missing_prices_from_event_pages(filtered)

            return NewYorkComedyClubPageData(event_list=filtered)

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Error extracting data from {url}: {e}",
                self.logger_context,
            )
            return None

    async def _enrich_missing_prices_from_event_pages(self, events: list[JsonLdEvent]) -> None:
        page_html_by_url: dict[str, str] = {}
        for event in events:
            if not _event_has_missing_or_zero_price(event) or not event.url:
                continue

            event_url = URLUtils.normalize_url(event.url)
            if event_url not in page_html_by_url:
                page_html_by_url[event_url] = await self.fetch_html(event_url)

            offer = _cheapest_normal_offer_from_event_page(page_html_by_url[event_url], event_url)
            if offer is None:
                continue

            if event.offers:
                event.offers[0].price = offer.price
                event.offers[0].price_currency = offer.price_currency or event.offers[0].price_currency
                event.offers[0].availability = offer.availability or event.offers[0].availability
                event.offers[0].name = offer.name or event.offers[0].name
            else:
                event.offers = [offer]


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


def _enrich_rendered_events_from_json_ld(
    rendered_events: list[JsonLdEvent],
    json_ld_events: list[JsonLdEvent],
) -> list[JsonLdEvent]:
    json_ld_by_url = {key: event for event in json_ld_events for key in _event_url_keys(event) if key}
    if not json_ld_by_url:
        return rendered_events

    for event in rendered_events:
        json_ld_event = next(
            (json_ld_by_url[key] for key in _event_url_keys(event) if key in json_ld_by_url),
            None,
        )
        if json_ld_event is None:
            continue

        if not event.performers and json_ld_event.performers:
            event.performers = json_ld_event.performers

        if _event_has_missing_or_zero_price(event):
            json_ld_offer = _first_priced_offer(json_ld_event)
            if json_ld_offer:
                if event.offers:
                    event.offers[0].price = json_ld_offer.price
                    event.offers[0].price_currency = json_ld_offer.price_currency or event.offers[0].price_currency
                    event.offers[0].availability = json_ld_offer.availability or event.offers[0].availability
                    event.offers[0].name = json_ld_offer.name or event.offers[0].name
                else:
                    event.offers = [json_ld_offer]

    return rendered_events


def _event_url_keys(event: JsonLdEvent) -> list[str]:
    return [
        _canonical_event_url(url)
        for url in (event.url, event.same_as, *(offer.url for offer in event.offers or []))
        if url
    ]


def _canonical_event_url(url: str) -> str:
    parsed = urlparse(urljoin("https://newyorkcomedyclub.com", url))
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/")
    return urlunparse(("https", host, path, "", "", ""))


def _event_has_missing_or_zero_price(event: JsonLdEvent) -> bool:
    if not event.offers:
        return True
    return all(_is_missing_or_zero_price(offer.price) for offer in event.offers)


def _first_priced_offer(event: JsonLdEvent) -> Optional[Offer]:
    return next(
        (offer for offer in event.offers or [] if not _is_missing_or_zero_price(offer.price)),
        None,
    )


def _is_missing_or_zero_price(price: str) -> bool:
    if price in ("", None):
        return True
    try:
        return float(str(price).replace("$", "").strip()) == 0.0
    except ValueError:
        return False


def _cheapest_normal_offer_from_event_page(html_content: str, event_url: str) -> Optional[Offer]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content or "", "html.parser")
    offers = []
    for row in soup.select(".ticket-info-row"):
        name_node = row.select_one(".ticket-name-price")
        if not name_node:
            continue

        name = _ticket_name_from_row(name_node)
        if _is_special_offer_ticket(name):
            continue

        price_node = row.select_one(".breakdown-base-original") or row.select_one(".ticket-price.original")
        price = _parse_price_text(price_node.get_text(" ", strip=True) if price_node else "")
        if price is None or price == 0.0:
            continue

        offers.append(
            Offer(
                url=event_url,
                price_currency="USD",
                price=f"{price:.2f}",
                availability="https://schema.org/InStock",
                name=name or "General Admission",
            )
        )

    return min(offers, key=lambda offer: float(offer.price)) if offers else None


def _ticket_name_from_row(name_node) -> str:
    for nested in name_node.select(".ticket-price-wrapper"):
        nested.decompose()
    return _normalize_ticket_name(name_node.get_text(" ", strip=True))


def _normalize_ticket_name(name: str) -> str:
    normalized = " ".join((name or "").split())
    if normalized.isupper():
        return normalized.title()
    return normalized


def _is_special_offer_ticket(name: str) -> bool:
    normalized = name.lower()
    return "special offer" in normalized or "comp" in normalized or "free" in normalized


def _parse_price_text(text: str) -> Optional[float]:
    match = re.search(r"\$?\s*(\d+(?:\.\d{1,2})?)", text or "")
    if not match:
        return None
    return float(match.group(1))


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
    month = DateTimeUtils.month_name_to_number(match.group(1))
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
    month = DateTimeUtils.month_name_to_number(match.group(1))
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
