"""Extraction for House of Comedy Phoenix WordPress AJAX show cards."""

import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.house_of_comedy_phoenix import (
    HouseOfComedyPhoenixEvent,
    normalize_showclix_url,
)
from laughtrack.foundation.utilities.datetime import DateTimeUtils

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
    def extract_events(
        html: str,
        *,
        year: int,
        source_url: str,
        month: Optional[int] = None,
    ) -> List[HouseOfComedyPhoenixEvent]:
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        containers = HouseOfComedyPhoenixExtractor._event_containers(soup)
        if not containers:
            containers = [soup]

        events: List[HouseOfComedyPhoenixEvent] = []
        seen: set[tuple[str, str, str, str]] = set()
        for container in containers:
            event = HouseOfComedyPhoenixExtractor._parse_container(
                container,
                year=year,
                month=month,
                source_url=source_url,
            )
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
            ".grid-view-comedy_show_item",
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

        source_host = urlparse(str(soup.base.get("href")) if soup.base else "").netloc
        for link in soup.find_all("a", href=True):
            href = str(link.get("href") or "")
            parsed = urlparse(href)
            if "/events/" not in parsed.path:
                continue
            if source_host and parsed.netloc and parsed.netloc != source_host:
                continue
            card = link.find_parent(["article", "li", "div"])
            if isinstance(card, Tag) and id(card) not in seen_ids:
                seen_ids.add(id(card))
                matches.append(card)
        return matches

    @staticmethod
    def _parse_container(
        container: Tag,
        *,
        year: int,
        source_url: str,
        month: Optional[int],
    ) -> Optional[HouseOfComedyPhoenixEvent]:
        ticket_url = HouseOfComedyPhoenixExtractor._ticket_url(container, source_url=source_url)
        if not ticket_url:
            return None

        text = " ".join(container.get_text(" ", strip=True).split())
        title = HouseOfComedyPhoenixExtractor._title(container, ticket_url=ticket_url)
        date = HouseOfComedyPhoenixExtractor._date(text, year=year, month=month)
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
    def _ticket_url(container: Tag, *, source_url: str) -> str:
        hrefs = [str(a.get("href") or "") for a in container.find_all("a", href=True)]
        haystack = " ".join(hrefs + [str(container)])
        match = _SHOWCLIX_RE.search(haystack)
        if match:
            return normalize_showclix_url(match.group(0).rstrip("/"))

        source_host = urlparse(source_url).netloc
        for href in hrefs:
            if not href or href == "#":
                continue
            absolute = urljoin(source_url, href)
            parsed = urlparse(absolute)
            if parsed.netloc == source_host and "/events/" in parsed.path:
                return absolute
        return ""

    @staticmethod
    def _title(container: Tag, *, ticket_url: str) -> str:
        selectors = (
            ".comedy_show_title",
            ".show_title",
            ".event-title",
            ".grid-view-comedy_show_title",
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
    def _date(text: str, *, year: int, month: Optional[int] = None) -> str:
        match = _DATE_RE.search(text)
        if match:
            month = DateTimeUtils.month_name_to_number(match.group(1))
            if month is None:
                return ""
            day = int(match.group(2))
            return f"{year:04d}-{month:02d}-{day:02d}"

        if month is None:
            return ""
        day_match = re.search(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\b", text, re.I)
        if not day_match:
            return ""
        day = int(day_match.group(1))
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
