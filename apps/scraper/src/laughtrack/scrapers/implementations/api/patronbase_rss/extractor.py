"""Extraction helpers for PatronBase productions RSS feeds."""

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, List, Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.patronbase_rss import PatronBaseRssEvent

_DATE_RE = re.compile(r"\bDate:\s*([0-9]{1,2}\s+[A-Za-z]{3},\s+[0-9]{4})\b")
_VENUE_RE = re.compile(r"\bVenue:\s*([^<\n\r]+)")
_TIME_RE = re.compile(r"\b([0-9]{1,2}:[0-9]{2}\s*[AP]M)\b", re.IGNORECASE)
_TITLE_DATE_SUFFIX_RE = re.compile(
    r"\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?\s+[0-9]{1,2}/[0-9]{1,2}\s+"
    r"[0-9]{1,2}:[0-9]{2}\s*[AP]M\s*$",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class PatronBaseRssExtractor:
    """Parse PatronBase RSS XML into PatronBaseRssEvent objects."""

    @classmethod
    def extract_events(
        cls,
        xml_text: Any,
        *,
        timezone_name: str = "UTC",
    ) -> List[PatronBaseRssEvent]:
        if not isinstance(xml_text, str) or not xml_text.strip():
            return []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        try:
            tz = ZoneInfo(timezone_name or "UTC")
        except Exception:
            tz = ZoneInfo("UTC")

        now = datetime.now(tz)
        events: List[PatronBaseRssEvent] = []
        for item in root.findall(".//item"):
            event = cls._parse_item(item, tz)
            if event is None or event.start < now:
                continue
            events.append(event)

        return events

    @classmethod
    def _parse_item(cls, item: ET.Element, tz: ZoneInfo) -> Optional[PatronBaseRssEvent]:
        raw_title = cls._child_text(item, "title")
        link = cls._child_text(item, "link")
        raw_description = cls._child_text(item, "description")
        if not raw_title or not link:
            return None

        date_match = _DATE_RE.search(raw_description)
        time_match = _TIME_RE.search(raw_title)
        if not date_match or not time_match:
            return None

        try:
            date_part = datetime.strptime(date_match.group(1), "%d %b, %Y")
            time_part = datetime.strptime(
                time_match.group(1).replace(" ", "").upper(),
                "%I:%M%p",
            )
        except ValueError:
            return None

        start = datetime(
            date_part.year,
            date_part.month,
            date_part.day,
            time_part.hour,
            time_part.minute,
            tzinfo=tz,
        )
        title = cls._clean_title(raw_title)
        description = cls._clean_description(raw_description)
        venue = ""
        venue_match = _VENUE_RE.search(raw_description)
        if venue_match:
            venue = cls._clean_text(venue_match.group(1))

        return PatronBaseRssEvent(
            title=title,
            start=start,
            show_page_url=link,
            description=description,
            venue=venue,
        )

    @staticmethod
    def _child_text(item: ET.Element, tag: str) -> str:
        child = item.find(tag)
        return child.text.strip() if child is not None and child.text else ""

    @staticmethod
    def _clean_title(title: str) -> str:
        cleaned = _TITLE_DATE_SUFFIX_RE.sub("", title).strip()
        return html.unescape(cleaned)

    @classmethod
    def _clean_description(cls, description: str) -> str:
        without_tags = _TAG_RE.sub(" ", description)
        return cls._clean_text(without_tags)

    @staticmethod
    def _clean_text(value: str) -> str:
        return _WHITESPACE_RE.sub(" ", html.unescape(value)).strip()
