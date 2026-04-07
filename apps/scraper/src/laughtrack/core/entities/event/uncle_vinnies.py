"""
Uncle Vinnie's Comedy Club event data model.

Extends OvationTixEvent with support for ISO 8601 date formats that
Uncle Vinnie's OvationTix API sometimes returns (e.g. "2025-06-28T20:00:00-04:00").
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz

from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.entities.event.ovationtix import OvationTixEvent
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class UncleVinniesEvent(OvationTixEvent):
    """
    OvationTix event for Uncle Vinnie's Comedy Club.

    Overrides date parsing to handle ISO 8601 formats with timezone offsets
    that the OvationTix API sometimes returns for this venue.
    """

    ticket_types: Optional[List[Dict[str, Any]]] = None
    _raw_performance_data: Optional[JSONDict] = None

    @property
    def name(self) -> str:
        """Alias for production_name, preserving the legacy field name."""
        return self.production_name

    def __post_init__(self):
        if self.ticket_types is None:
            self.ticket_types = []

    def has_ticket_data(self) -> bool:
        """Check if this event has ticket information available."""
        return bool(self.sections or self.ticket_types)

    def get_ticket_count(self) -> int:
        """Get the total number of ticket types available."""
        total = 0
        if self.sections:
            for section in self.sections:
                ticket_type_views = section.get("ticketTypeViews", [])
                total += len(ticket_type_views)
        return total

    def _parse_start_date(self, timezone: str) -> Optional[datetime]:
        """
        Parse the event start date, handling multiple OvationTix date formats:
        - "YYYY-MM-DD HH:MM" (no timezone)
        - "YYYY-MM-DDTHH:MM:SS" (no timezone)
        - "YYYY-MM-DDTHH:MM:SS-04:00" or "...Z" (ISO 8601 with timezone)
        """
        try:
            if "T" in self.start_date and (
                "+" in self.start_date or self.start_date.endswith("Z") or self.start_date[-6] in "+-"
            ):
                return ShowFactoryUtils.parse_datetime_with_timezone_fallback(self.start_date, timezone)

            elif "T" in self.start_date:
                local_tz = pytz.timezone(timezone)
                naive_datetime = datetime.strptime(self.start_date, "%Y-%m-%dT%H:%M:%S")
                return local_tz.localize(naive_datetime, is_dst=None)

            else:
                # Delegate to parent for standard "YYYY-MM-DD HH:MM" format
                return super()._parse_start_date(timezone)

        except Exception as e:
            Logger.error(f"Error parsing start date {self.start_date}: {e}")
            return None
