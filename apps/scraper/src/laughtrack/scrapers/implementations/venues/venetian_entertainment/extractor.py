"""Extraction for Venetian AEM entertainment GraphQL responses."""

from datetime import datetime
from typing import Any, List

from laughtrack.core.entities.event.venetian_entertainment import VenetianEntertainmentEvent

BASE_URL = "https://www.venetianlasvegas.com"
_COMEDY_CATEGORY = "venetianlasvegas-com:events/type/comedy"


class VenetianEntertainmentExtractor:
    """Parse comedy events from Venetian's persisted AEM GraphQL response."""

    @classmethod
    def extract_events(cls, payload: dict[str, Any], *, venue_category: str) -> List[VenetianEntertainmentEvent]:
        items = cls._items(payload)
        events: List[VenetianEntertainmentEvent] = []
        for item in items:
            if not cls._is_matching_comedy_item(item, venue_category=venue_category):
                continue

            name = cls._string(item.get("title"))
            ticket_url = cls._string(item.get("primaryLinkUrl"))
            show_page_url = cls._show_page_url(item)
            time_text = cls._string(item.get("times"))
            description = cls._string(item.get("shortDescription"))
            if not name or not ticket_url or not show_page_url:
                continue

            for start_date in cls._expand_dates(item.get("dates"), time_text):
                events.append(
                    VenetianEntertainmentEvent(
                        name=name,
                        start_date=start_date,
                        show_page_url=show_page_url,
                        ticket_url=ticket_url,
                        description=description,
                    )
                )

        return events

    @staticmethod
    def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data")
        if not isinstance(data, dict):
            return []
        root = data.get("entertainmentList")
        if not isinstance(root, dict):
            return []
        items = root.get("items")
        return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []

    @classmethod
    def _is_matching_comedy_item(cls, item: dict[str, Any], *, venue_category: str) -> bool:
        categories = item.get("categories")
        if not isinstance(categories, list):
            return False
        normalized = {cls._category_slug(category) for category in categories if isinstance(category, str)}
        return "comedy" in normalized and venue_category in normalized

    @staticmethod
    def _category_slug(category: str) -> str:
        return category.rstrip("/").rsplit("/", 1)[-1].strip().lower()

    @classmethod
    def _show_page_url(cls, item: dict[str, Any]) -> str:
        for key in ("secondaryLink", "moreDetailsLink", "primaryLink"):
            value = item.get(key)
            if isinstance(value, dict):
                url = cls._url_from_aem_path(cls._string(value.get("_path")))
                if url:
                    return url

        return cls._url_from_aem_path(cls._string(item.get("_path")))

    @staticmethod
    def _url_from_aem_path(path: str) -> str:
        if not path:
            return ""
        normalized = path.strip()
        if normalized.startswith("/content/venetian/us/en/"):
            normalized = normalized.replace("/content/venetian/us/en/", "/", 1)
        elif normalized.startswith("/content/dam/vlv/content-fragments/events/entertainment/"):
            slug = normalized.rstrip("/").rsplit("/", 1)[-1]
            normalized = f"/entertainment/{slug}"
        else:
            return ""
        if not normalized.endswith(".html"):
            normalized = normalized.rstrip("/") + ".html"
        return f"{BASE_URL}{normalized}"

    @classmethod
    def _expand_dates(cls, dates: Any, time_text: str) -> List[str]:
        if not isinstance(dates, list):
            return []

        parsed_time = cls._parse_time(time_text)
        if parsed_time is None:
            return []

        start_dates: List[str] = []
        for raw_date in dates:
            date_text = cls._string(raw_date)
            if not date_text:
                continue
            try:
                parsed_date = datetime.strptime(date_text, "%Y-%m-%d").date()
            except ValueError:
                continue
            start = datetime.combine(parsed_date, parsed_time)
            start_dates.append(start.strftime("%Y-%m-%d %H:%M:00"))

        return start_dates

    @staticmethod
    def _parse_time(time_text: str):
        normalized = " ".join(time_text.replace("\xa0", " ").split())
        if not normalized or "varies" in normalized.lower() or "various" in normalized.lower():
            return None
        if "&" in normalized or " and " in normalized.lower():
            return None
        try:
            return datetime.strptime(normalized.upper(), "%I:%M %p").time()
        except ValueError:
            return None

    @staticmethod
    def _string(value: Any) -> str:
        return str(value).strip() if value is not None else ""
