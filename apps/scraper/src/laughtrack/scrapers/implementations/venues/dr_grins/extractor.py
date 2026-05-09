"""HTML extraction for Dr. Grins Comedy Club public pages."""

import re
from typing import List, Optional
from urllib.parse import urljoin

from laughtrack.core.entities.event.dr_grins import DrGrinsEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.html.utils import HtmlUtils

_BASE_URL = "https://www.thebob.com"
_DETAIL_PATH_RE = re.compile(
    r'href="(?P<href>https://www\.thebob\.com/drgrins/comedian/index\.html\?id=\d+)"',
    re.IGNORECASE,
)
_TITLE_RE = re.compile(
    r'<div class="feature-title">\s*(?P<title>.*?)\s*</div>',
    re.DOTALL | re.IGNORECASE,
)
_TICKET_RE = re.compile(
    r'<a class="feature-button" href="(?P<href>[^"]+)"',
    re.IGNORECASE,
)
_SHOW_DATE_RE = re.compile(
    r'<div class="show-date">\s*<span class="bold">(?P<date>.*?)</span>'
    r'(?P<body>.*?)</div>',
    re.DOTALL | re.IGNORECASE,
)
_TIME_RE = re.compile(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))", re.IGNORECASE)


class DrGrinsExtractor:
    """Parse the public Dr. Grins listing and comedian detail pages."""

    @staticmethod
    def extract_detail_urls(html: str) -> List[str]:
        """Return unique comedian detail URLs from the public listing page."""
        if not html:
            return []
        seen: set[str] = set()
        urls: List[str] = []
        for match in _DETAIL_PATH_RE.finditer(html):
            url = urljoin(_BASE_URL, match.group("href"))
            if url not in seen:
                seen.add(url)
                urls.append(url)
        return urls

    @staticmethod
    def extract_events(html: str, *, detail_url: str) -> List[DrGrinsEvent]:
        """Extract all dated performances from one comedian detail page."""
        if not html:
            return []

        title_match = _TITLE_RE.search(html)
        if title_match is None:
            Logger.debug("DrGrinsExtractor: skipping page with no feature title")
            return []
        title = HtmlUtils.strip_tags(title_match.group("title"), normalize_whitespace=True)
        if not title:
            return []

        ticket_match = _TICKET_RE.search(html)
        ticket_url = (
            urljoin(_BASE_URL, ticket_match.group("href"))
            if ticket_match is not None
            else detail_url
        )

        events: List[DrGrinsEvent] = []
        for match in _SHOW_DATE_RE.finditer(html):
            date_str = HtmlUtils.strip_tags(match.group("date"), normalize_whitespace=True)
            body = HtmlUtils.strip_tags(match.group("body"), normalize_whitespace=True)
            if not date_str or not body:
                continue
            times = _TIME_RE.findall(body)
            for time_str in times:
                events.append(
                    DrGrinsEvent(
                        title=title,
                        date_str=date_str,
                        time_str=time_str,
                        detail_url=detail_url,
                        ticket_url=ticket_url,
                    )
                )

        return events
