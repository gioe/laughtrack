"""Extractor for TK's static Spothopper events page."""

from __future__ import annotations

import re
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.tks_comedy import TksComedyEvent

_COMEDY_RE = re.compile(r"\b(?:stand[- ]?up|comedy|comedian)\b", re.IGNORECASE)
_NON_SHOW_RE = re.compile(r"\bno\s+show\b", re.IGNORECASE)
_DATE_RE = re.compile(
    r"\b(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)?[,]?\s*"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s*\d{4})?",
    re.IGNORECASE,
)
_SHOW_TIME_RE = re.compile(r"\b(?:stand[- ]?up\s+)?comedy\s+show\s+(\d{1,2}(?::\d{2})?\s*[ap]m)\b", re.IGNORECASE)
_GENERIC_TIME_RE = re.compile(r"\b(?:at\s+)?(\d{1,2}(?::\d{2})?\s*[ap]m)\b", re.IGNORECASE)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize_date_label(raw: str) -> str:
    match = _DATE_RE.search(raw)
    if not match:
        return ""
    return f"{match.group(1)} {int(match.group(2))}"


def _extract_time_label(raw: str) -> str:
    match = _SHOW_TIME_RE.search(raw) or _GENERIC_TIME_RE.search(raw)
    return _clean_text(match.group(1)).lower() if match else ""


class TksComedyExtractor:
    """Extract comedy-labeled ticketed events from TK's public events page."""

    @staticmethod
    def extract_events(html: str) -> List[TksComedyEvent]:
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one(".events-custom-page-content") or soup
        events: List[TksComedyEvent] = []

        for heading in container.find_all("h2"):
            event = TksComedyExtractor._extract_from_heading(heading)
            if event is not None:
                events.append(event)

        return events

    @staticmethod
    def _extract_from_heading(heading: Tag) -> Optional[TksComedyEvent]:
        title = _clean_text(heading.get_text(" ", strip=True))
        siblings: List[Tag] = []

        for sibling in heading.find_next_siblings():
            if isinstance(sibling, Tag) and sibling.name == "h2":
                break
            if isinstance(sibling, Tag) and sibling.find("h2") is not None:
                break
            if isinstance(sibling, Tag):
                siblings.append(sibling)

        block_text = _clean_text(" ".join([title] + [s.get_text(" ", strip=True) for s in siblings]))
        image_text = _clean_text(" ".join(str(img.get("alt", "")) for img in siblings for img in img.find_all("img")))
        searchable_text = _clean_text(f"{block_text} {image_text}")

        if not _COMEDY_RE.search(searchable_text) or _NON_SHOW_RE.search(title):
            return None

        ticket_url = TksComedyExtractor._extract_ticket_url(siblings)
        date_label = _normalize_date_label(searchable_text)
        time_label = _extract_time_label(searchable_text)
        if not ticket_url or not date_label or not time_label:
            return None
        description = _NON_SHOW_RE.split(block_text, maxsplit=1)[0].strip()

        return TksComedyEvent(
            title=title,
            date_label=date_label,
            time_label=time_label,
            ticket_url=ticket_url,
            description=description,
        )

    @staticmethod
    def _extract_ticket_url(siblings: List[Tag]) -> str:
        for sibling in siblings:
            link = sibling.find("a", href=True)
            if link is None:
                continue
            href = str(link.get("href") or "").strip()
            link_text = _clean_text(link.get_text(" ", strip=True))
            if "square.link/" in href and re.search(r"\bbuy\s+tickets?\b", link_text, re.IGNORECASE):
                return href
        return ""
