"""Extraction for Kenosha Comedy Club's Happenings Magazine WordPress posts."""

import html
import re
from datetime import date, datetime
from typing import Any, Iterable, List, Optional

from laughtrack.core.entities.event.kenosha_comedy_club import KenoshaComedyClubEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

_TITLE_RE = re.compile(
    r"^\s*(?P<name>.+?)\s*:\s*"
    r"(?P<month>[A-Za-z]+)\s+"
    r"(?P<days>\d{1,2}(?:\s*(?:&|and|,)\s*\d{1,2})*)"
    r"\s+at\s+"
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<meridiem>[AP]M)",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("rendered", "")
    text = html.unescape(str(value or ""))
    text = _TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_title_dates(title: str, today: date) -> List[tuple[str, str]]:
    match = _TITLE_RE.search(title)
    if not match:
        return []

    show_name = match.group("name").strip()
    month = match.group("month")
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or "0")
    meridiem = match.group("meridiem").upper()
    if meridiem == "PM" and hour != 12:
        hour += 12
    elif meridiem == "AM" and hour == 12:
        hour = 0

    starts = []
    for day_text in re.findall(r"\d{1,2}", match.group("days")):
        stamp = f"{month} {int(day_text)} {today.year} {hour:02d}:{minute:02d}"
        parsed = None
        for fmt in ("%B %d %Y %H:%M", "%b %d %Y %H:%M"):
            try:
                parsed = datetime.strptime(stamp, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            continue
        if parsed.date() < today:
            parsed = parsed.replace(year=today.year + 1)
        starts.append((show_name, parsed.strftime("%Y-%m-%d %H:%M:00")))

    return starts


class KenoshaComedyClubExtractor:
    """Parse KenoshaComedyClubEvent objects from WordPress REST posts."""

    @staticmethod
    def extract_events(
        api_response: Any,
        logger_context=None,
        today: Optional[date] = None,
    ) -> List[KenoshaComedyClubEvent]:
        today = today or date.today()
        raw_posts = api_response.get("posts", api_response) if isinstance(api_response, dict) else api_response
        if not isinstance(raw_posts, Iterable) or isinstance(raw_posts, (str, bytes, dict)):
            return []

        events: List[KenoshaComedyClubEvent] = []
        seen = set()
        for raw in raw_posts:
            if not isinstance(raw, dict):
                continue
            title = _clean_text(raw.get("title"))
            link = str(raw.get("link") or "").strip()
            description = _clean_text(raw.get("excerpt"))
            parsed_starts = _parse_title_dates(title, today)
            if not parsed_starts:
                Logger.warn(
                    f"KenoshaComedyClubExtractor: skipping post with unparseable show date: {title}",
                    logger_context,
                )
                continue

            for name, start_date in parsed_starts:
                key = (name.lower(), start_date, link)
                if key in seen:
                    continue
                seen.add(key)
                events.append(
                    KenoshaComedyClubEvent(
                        name=name,
                        start_date=start_date,
                        url=link,
                        description=description,
                    )
                )

        return events
