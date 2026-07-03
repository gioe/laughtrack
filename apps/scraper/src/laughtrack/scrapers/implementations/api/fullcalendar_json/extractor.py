"""Extraction for simple FullCalendar JSON feeds."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Pattern, Sequence
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.fullcalendar_json import FullCalendarJsonEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.html.utils import HtmlUtils


def _title_allowed(
    title: str,
    include_title_res: Optional[Sequence[Pattern[str]]],
    exclude_title_res: Optional[Sequence[Pattern[str]]],
) -> bool:
    if include_title_res and not any(p.search(title) for p in include_title_res):
        return False
    if exclude_title_res and any(p.search(title) for p in exclude_title_res):
        return False
    return True


class FullCalendarJsonExtractor:
    """Convert FullCalendar event dictionaries into domain events."""

    @staticmethod
    def extract_events(
        api_response: List[Dict[str, Any]],
        base_domain: str,
        timezone_name: str = "UTC",
        include_title_res: Optional[Sequence[Pattern[str]]] = None,
        exclude_title_res: Optional[Sequence[Pattern[str]]] = None,
    ) -> List[FullCalendarJsonEvent]:
        """Extract future, unsold FullCalendar events from a JSON list."""
        if not isinstance(api_response, list):
            return []

        try:
            default_tz = ZoneInfo(timezone_name or "UTC")
        except Exception:
            default_tz = timezone.utc
        now = datetime.now(timezone.utc)
        events: List[FullCalendarJsonEvent] = []
        for raw in api_response:
            try:
                event = FullCalendarJsonExtractor._parse_event(raw, base_domain, default_tz)
            except Exception as e:
                Logger.warn(f"FullCalendarJsonExtractor: skipping event due to error: {e}")
                continue
            if event is None:
                continue
            if event.start.astimezone(timezone.utc) < now:
                continue
            if not _title_allowed(event.title, include_title_res, exclude_title_res):
                continue
            events.append(event)
        return events

    @staticmethod
    def _parse_event(raw: Dict[str, Any], base_domain: str, default_tz) -> Optional[FullCalendarJsonEvent]:
        if not isinstance(raw, dict):
            return None

        title = (raw.get("title") or "").strip()
        start = FullCalendarJsonExtractor._parse_start(raw.get("start"), default_tz)
        if not title or start is None:
            return None

        props = raw.get("extendedProps") if isinstance(raw.get("extendedProps"), dict) else {}
        if props.get("soldOut") is True:
            return None

        event_url = (raw.get("url") or "").strip()
        show_page_url = urljoin(base_domain.rstrip("/") + "/", event_url) if event_url else base_domain
        description = HtmlUtils.strip_tags(props.get("desc") or raw.get("description") or "")
        location = (props.get("location") or raw.get("location") or "").strip()

        return FullCalendarJsonEvent(
            title=title,
            start=start,
            show_page_url=show_page_url,
            description=description,
            location=location,
        )

    @staticmethod
    def _parse_start(value: Any, default_tz) -> Optional[datetime]:
        if not isinstance(value, str) or not value.strip():
            return None
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=default_tz)
        return parsed
