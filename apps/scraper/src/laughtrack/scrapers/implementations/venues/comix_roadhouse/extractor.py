"""Extraction for Comix Roadhouse Webflow pages."""

import re
from datetime import datetime
from typing import List
from urllib.parse import urljoin

from laughtrack.core.entities.event.comix_roadhouse import ComixRoadhouseEvent
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

BASE_URL = "https://www.comixroadhouse.com"

_NON_COMEDY_TITLE_RE = re.compile(
    r"\b(line dancing|karaoke|jukebox|radio|band|bands|music|after school special)\b",
    re.IGNORECASE,
)


class ComixRoadhouseExtractor:
    """Parse ComixRoadhouseEvent objects from listing/detail HTML."""

    @staticmethod
    def extract_listing_urls(html_content: str, base_url: str = "https://www.comixroadhouse.com") -> List[str]:
        soup = HtmlScraper._parse_html(html_content)
        urls: List[str] = []
        seen = set()

        for link in soup.select('a.schedule-event[href^="/comics/"]'):
            href = str(link.get("href") or "").strip()
            if not href:
                continue

            name_el = link.select_one(".schedule-speaker-name")
            title = name_el.get_text(" ", strip=True) if name_el else link.get_text(" ", strip=True)
            if _NON_COMEDY_TITLE_RE.search(title):
                continue

            absolute_url = urljoin(base_url, href)
            if absolute_url in seen:
                continue
            seen.add(absolute_url)
            urls.append(absolute_url)

        return urls

    @staticmethod
    def extract_next_page_url(html_content: str, current_url: str) -> str:
        soup = HtmlScraper._parse_html(html_content)
        link = soup.select_one("a.w-pagination-next[href], a[aria-label='Next Page'][href]")
        if not link:
            return ""

        href = str(link.get("href") or "").strip()
        if not href:
            return ""

        return urljoin(current_url, href)

    @staticmethod
    def extract_events_from_detail(
        html_content: str,
        detail_url: str,
        timezone_name: str = "America/New_York",
    ) -> List[ComixRoadhouseEvent]:
        soup = HtmlScraper._parse_html(html_content)
        description_el = soup.select_one(".text-grey.w-richtext")
        description = description_el.get_text(" ", strip=True) if description_el else ""

        events: List[ComixRoadhouseEvent] = []
        seen = set()
        for link in soup.select("a.schedule-event.com[href]"):
            if "w-condition-invisible" in (link.get("class") or []):
                continue

            name_el = link.select_one(".schedule-speaker-name")
            date_el = link.select_one(".schedule-event-time")
            time_el = link.select_one("h6.nm")
            if not name_el or not date_el or not time_el:
                continue

            name = name_el.get_text(" ", strip=True)
            date_text = date_el.get_text(" ", strip=True)
            time_text = time_el.get_text(" ", strip=True)
            start_date = ComixRoadhouseExtractor._parse_start_date(date_text, time_text)
            if not start_date:
                continue

            ticket_url = str(link.get("href") or "").strip()
            key = (name.lower(), start_date, ticket_url)
            if key in seen:
                continue
            seen.add(key)
            events.append(
                ComixRoadhouseEvent(
                    name=name,
                    start_date=start_date,
                    show_page_url=detail_url,
                    ticket_url=ticket_url,
                    description=description,
                )
            )

        return events

    @staticmethod
    def _parse_start_date(date_text: str, time_text: str) -> str:
        normalized_time = " ".join(time_text.upper().split())
        normalized_time = normalized_time.replace("A M", "AM").replace("P M", "PM")
        for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%y %I:%M %p"):
            try:
                parsed = datetime.strptime(f"{date_text.strip()} {normalized_time}", fmt)
                return parsed.strftime("%Y-%m-%d %H:%M:00")
            except ValueError:
                continue
        return ""
