"""Extraction for custom Wix/Velo _functions/shows JSON endpoints."""

from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.event.wix_functions_shows import WixFunctionsShowEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class WixFunctionsShowsExtractor:
    """Convert a response with a top-level ``shows`` array into domain events."""

    @staticmethod
    def extract_events(api_response: Dict[str, Any], timezone_name: str = "UTC") -> List[WixFunctionsShowEvent]:
        if not isinstance(api_response, dict):
            return []

        raw_shows = api_response.get("shows")
        if not isinstance(raw_shows, list):
            return []

        try:
            default_tz = ZoneInfo(timezone_name or "UTC")
        except Exception:
            default_tz = timezone.utc

        now = datetime.now(timezone.utc)
        events: List[WixFunctionsShowEvent] = []
        for raw in raw_shows:
            try:
                event = WixFunctionsShowsExtractor._parse_show(raw, default_tz)
            except Exception as e:
                Logger.warn(f"WixFunctionsShowsExtractor: skipping show due to error: {e}")
                continue
            if event is None:
                continue
            if event.start.astimezone(timezone.utc) < now:
                continue
            events.append(event)
        return events

    @staticmethod
    def _parse_show(raw: Dict[str, Any], default_tz) -> Optional[WixFunctionsShowEvent]:
        if not isinstance(raw, dict):
            return None

        title = str(raw.get("title") or "").strip()
        ticket_url = str(raw.get("ticket_url") or "").strip()
        start = WixFunctionsShowsExtractor._parse_start(raw.get("start_local") or raw.get("start_utc"), default_tz)
        if not title or start is None or not ticket_url:
            return None

        return WixFunctionsShowEvent(
            title=unescape(title),
            start=start,
            ticket_url=ticket_url,
            price_from=WixFunctionsShowsExtractor._parse_price(raw.get("price_from")),
            lineup_text=unescape(str(raw.get("lineup_text") or "")).strip() or None,
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

    @staticmethod
    def _parse_price(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
