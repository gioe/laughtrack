"""
Four Day Weekend Comedy data extraction utilities.

Pure parsing helpers — no HTTP calls.  All network I/O is handled by the scraper.
"""

import re
from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.event.four_day_weekend import FourDayWeekendEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict

# Matches https://ci.ovationtix.com/{clientId}/production/{productionId}
_PRODUCTION_URL_RE = re.compile(
    r"https://ci\.ovationtix\.com/(\d+)/production/(\d+)",
    re.IGNORECASE,
)


class FourDayWeekendExtractor:
    """Pure parsing utilities for Four Day Weekend Comedy responses."""

    @staticmethod
    def extract_production_ids(html: str) -> List[str]:
        """
        Extract OvationTix production IDs from the buy-tickets page HTML.

        Returns a deduplicated list of production ID strings, preserving order.
        """
        seen: set = set()
        ids: List[str] = []
        for _client_id, prod_id in _PRODUCTION_URL_RE.findall(html):
            if prod_id not in seen:
                seen.add(prod_id)
                ids.append(prod_id)
        return ids

    @staticmethod
    def extract_events_from_production(
        production_data: JSONDict,
        production_id: str,
        client_id: str,
    ) -> List[FourDayWeekendEvent]:
        """
        Build FourDayWeekendEvent objects from a Production/performance? API response.

        Args:
            production_data: Parsed JSON from the OvationTix production endpoint.
            production_id: The production ID string (e.g. "1068128").
            client_id: The OvationTix org/client ID (e.g. "36367").

        Returns:
            List of FourDayWeekendEvent, one per upcoming performance.
        """
        production_name = (
            production_data.get("productionName")
            or production_data.get("supertitle")
            or "Four Day Weekend"
        )
        description = production_data.get("description")
        performances = production_data.get("performances") or []

        events: List[FourDayWeekendEvent] = []
        for perf in performances:
            perf_id = perf.get("id")
            start_date = perf.get("startDate")
            if not perf_id or not start_date:
                continue

            tickets_available = bool(perf.get("ticketsAvailable", True))
            available_to_purchase = bool(perf.get("availableToPurchaseOnWeb", True))

            event_url = (
                f"https://ci.ovationtix.com/{client_id}/production/{production_id}"
                f"?performanceId={perf_id}"
            )

            events.append(
                FourDayWeekendEvent(
                    production_id=production_id,
                    performance_id=str(perf_id),
                    production_name=production_name,
                    start_date=start_date,
                    tickets_available=tickets_available and available_to_purchase,
                    event_url=event_url,
                    description=description,
                    sections=[],
                )
            )

        return events

    @staticmethod
    def is_past_event(start_date_str: str, timezone: str) -> bool:
        """Return True if the 'YYYY-MM-DD HH:MM' string is in the past."""
        try:
            tz = pytz.timezone(timezone)
            naive = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M")
            event_dt = tz.localize(naive, is_dst=None)
            return event_dt < datetime.now(tz)
        except Exception:
            return False
