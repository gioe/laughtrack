"""Registry for site-specific comedian website extractors."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}
_CANADIAN_PROVINCES = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
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


@dataclass(frozen=True)
class ComedianWebsiteTourEvent:
    """Normalized event parsed from a comedian-owned tour page."""

    venue_name: str
    start_date: datetime
    city: str
    region: str
    country: str
    ticket_url: str
    source_url: str
    platform_hint: str


class ComedianWebsiteExtractor(Protocol):
    """Protocol implemented by registered comedian website extractors."""

    strategy: str

    def extract_events(self, html: str, source_url: str) -> list[ComedianWebsiteTourEvent]:
        """Parse normalized tour events from fetched HTML."""


class BenBankasExtractor:
    """Extracts visible tour table rows from benbankas.com."""

    strategy = "ben_bankas"

    def extract_events(self, html: str, source_url: str) -> list[ComedianWebsiteTourEvent]:
        soup = BeautifulSoup(html or "", "html.parser")
        events: list[ComedianWebsiteTourEvent] = []
        for row in soup.select("tr.eventRow"):
            event = self._parse_row(row, source_url)
            if event is not None:
                events.append(event)
        return events

    def _parse_row(self, row, source_url: str) -> Optional[ComedianWebsiteTourEvent]:
        date_cell = row.select_one(".gigDate")
        show_cell = row.select_one(".td_show")
        location_cell = row.select_one(".location_space")
        if date_cell is None or show_cell is None or location_cell is None:
            return None

        date_text = _visible_text(date_cell)
        show_text = _visible_text(show_cell)
        location_text = _visible_text(location_cell)
        start_date = _parse_date_time(date_text, show_text)
        venue_name = _parse_venue_name(show_text)
        city, region = _parse_city_region(location_text)
        if start_date is None or not venue_name or not city or not region:
            return None

        country = _country_from_location_cell(location_cell, region)
        link = row.find("a", href=True)
        ticket_url = urljoin(source_url, link["href"].strip()) if link else source_url

        return ComedianWebsiteTourEvent(
            venue_name=venue_name,
            start_date=start_date,
            city=city,
            region=region,
            country=country,
            ticket_url=ticket_url,
            source_url=source_url,
            platform_hint=self.strategy,
        )


def get_extractor_for_url(url: str) -> Optional[ComedianWebsiteExtractor]:
    """Return a site-specific extractor for a comedian website URL."""
    try:
        hostname = (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return None
    if hostname == "benbankas.com":
        return BenBankasExtractor()
    return None


def has_registered_extractor(url: str) -> bool:
    """Return True when a URL is supported by a site-specific extractor."""
    return get_extractor_for_url(url) is not None


def _visible_text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def _parse_date_time(date_text: str, show_text: str) -> Optional[datetime]:
    date_match = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\b", date_text)
    time_match = re.search(r"@\s*(\d{1,2})(?::(\d{2}))?\s*([AP]M)\b", show_text, re.IGNORECASE)
    if not date_match or not time_match:
        return None

    month = _MONTHS.get(date_match.group(1).lower())
    if month is None:
        return None
    day = int(date_match.group(2))
    hour = int(time_match.group(1))
    minute = int(time_match.group(2) or 0)
    meridiem = time_match.group(3).upper()
    if meridiem == "PM" and hour != 12:
        hour += 12
    elif meridiem == "AM" and hour == 12:
        hour = 0

    now = datetime.now(tz=timezone.utc)
    year = now.year
    candidate = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    if candidate.date() < now.date():
        candidate = candidate.replace(year=year + 1)
    return candidate


def _parse_venue_name(show_text: str) -> str:
    return re.sub(r"\s*@\s*\d{1,2}(?::\d{2})?\s*[AP]M\b.*$", "", show_text, flags=re.IGNORECASE).strip()


def _parse_city_region(location_text: str) -> tuple[str, str]:
    match = re.search(r"(.+?),\s*([A-Za-z]{2})\b", location_text)
    if not match:
        return "", ""
    return match.group(1).strip(), match.group(2).upper()


def _country_from_location_cell(location_cell, region: str) -> str:
    image_text = " ".join(
        str(img.get("alt") or img.get("title") or "")
        for img in location_cell.find_all("img")
    ).lower()
    if "canada" in image_text:
        return "CA"
    if "us" in image_text or "united states" in image_text:
        return "US"
    if region in _US_STATES:
        return "US"
    if region in _CANADIAN_PROVINCES:
        return "CA"
    return ""
