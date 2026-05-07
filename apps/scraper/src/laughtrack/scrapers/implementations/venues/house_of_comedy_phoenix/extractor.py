"""Extraction for House of Comedy Phoenix WordPress AJAX show cards."""

import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.house_of_comedy_phoenix import (
    HouseOfComedyPhoenixEvent,
    normalize_showclix_url,
)

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

_SHOWCLIX_RE = re.compile(r"https?://(?:embed|www)\.showclix\.com/event/[^\s\"'<>]+", re.I)
_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2}\s*[AP]\.?M\.?)\b", re.I)
_DATE_RE = re.compile(
    r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?\.?,?\s*"
    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\.?\s+(\d{1,2})\b",
    re.I,
)


class HouseOfComedyPhoenixExtractor:
    """Parse show cards returned by the Phoenix WordPress get_comedy_shows action."""

    @staticmethod
    def extract_events(html: str, *, year: int, source_url: str) -> List[HouseOfComedyPhoenixEvent]:
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        containers = HouseOfComedyPhoenixExtractor._event_containers(soup)
        if not containers:
            containers = [soup]

        events: List[HouseOfComedyPhoenixEvent] = []
        seen: set[tuple[str, str, str, str]] = set()
        for container in containers:
            event = HouseOfComedyPhoenixExtractor._parse_container(container, year=year, source_url=source_url)
            if event is None:
                continue
            key = (event.title, event.date, event.time, event.ticket_url)
            if key in seen:
                continue
            seen.add(key)
            events.append(event)
        return events

    @staticmethod
    def _event_containers(soup: BeautifulSoup) -> List[Tag]:
        selectors = (
            ".comedy_show_card",
            ".comedy_show_item",
            ".comedy_show_event",
            ".comedy-show-card",
            ".event-card",
        )
        matches: List[Tag] = []
        seen_ids: set[int] = set()
        for selector in selectors:
            for tag in soup.select(selector):
                tag_id = id(tag)
                if tag_id not in seen_ids:
                    seen_ids.add(tag_id)
                    matches.append(tag)
        if matches:
            return matches

        for link in soup.find_all("a", href=_SHOWCLIX_RE):
            card = link.find_parent(["article", "li", "div"])
            if isinstance(card, Tag) and id(card) not in seen_ids:
                seen_ids.add(id(card))
                matches.append(card)
        return matches

    @staticmethod
    def _parse_container(container: Tag, *, year: int, source_url: str) -> Optional[HouseOfComedyPhoenixEvent]:
        ticket_url = HouseOfComedyPhoenixExtractor._ticket_url(container)
        if not ticket_url:
            return None

        text = " ".join(container.get_text(" ", strip=True).split())
        title = HouseOfComedyPhoenixExtractor._title(container, ticket_url=ticket_url)
        date = HouseOfComedyPhoenixExtractor._date(text, year=year)
        time = HouseOfComedyPhoenixExtractor._time(text)
        if not title or not date or not time:
            return None

        return HouseOfComedyPhoenixEvent(
            title=title,
            date=date,
            time=time,
            ticket_url=ticket_url,
            source_url=source_url,
        )

    @staticmethod
    def _ticket_url(container: Tag) -> str:
        hrefs = [str(a.get("href") or "") for a in container.find_all("a", href=True)]
        haystack = " ".join(hrefs + [str(container)])
        match = _SHOWCLIX_RE.search(haystack)
        if not match:
            return ""
        return normalize_showclix_url(match.group(0).rstrip("/"))

    @staticmethod
    def _title(container: Tag, *, ticket_url: str) -> str:
        selectors = (
            ".comedy_show_title",
            ".show_title",
            ".event-title",
            "h1",
            "h2",
            "h3",
            "h4",
        )
        for selector in selectors:
            element = container.select_one(selector)
            if element:
                title = " ".join(element.get_text(" ", strip=True).split())
                if title and "ticket" not in title.lower():
                    return title

        for link in container.find_all("a", href=True):
            if ticket_url.endswith(str(link.get("href") or "").rstrip("/").split("/")[-1]):
                continue
            title = " ".join(link.get_text(" ", strip=True).split())
            if title and "ticket" not in title.lower():
                return title
        return ""

    @staticmethod
    def _date(text: str, *, year: int) -> str:
        match = _DATE_RE.search(text)
        if not match:
            return ""
        month = _MONTHS[match.group(1).lower().rstrip(".")]
        day = int(match.group(2))
        return f"{year:04d}-{month:02d}-{day:02d}"

    @staticmethod
    def _time(text: str) -> str:
        match = _TIME_RE.search(text)
        if not match:
            return ""
        parsed = datetime.strptime(
            match.group(1).upper().replace(".", "").replace(" ", ""),
            "%I:%M%p",
        )
        return parsed.strftime("%-I:%M %p")
