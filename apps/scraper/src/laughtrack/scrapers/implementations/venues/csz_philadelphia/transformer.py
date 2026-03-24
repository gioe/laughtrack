"""
CSz Philadelphia event transformer.

Converts CszPhillyShowInstance objects into Show objects, inferring the
calendar year from the current date and the abbreviated month name.
"""

from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .page_data import CszPhillyShowInstance


# Map 3-letter month abbreviations to month numbers (1-based)
_MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _ticket_url(event_id: int, session_key: str) -> str:
    return (
        f"https://plugin.vbotickets.com/v5.0/event.asp"
        f"?eid={event_id}&s={session_key}"
    )


class CszPhillyEventTransformer(DataTransformer[CszPhillyShowInstance]):
    """Transforms CszPhillyShowInstance objects into Show objects."""

    def __init__(self, club: Club, session_key: str = ""):
        super().__init__(club)
        self._session_key = session_key

    def can_transform(self, raw_data: CszPhillyShowInstance) -> bool:
        return (
            isinstance(raw_data, CszPhillyShowInstance)
            and bool(raw_data.event_name)
            and bool(raw_data.month)
            and bool(raw_data.time)
            and raw_data.day > 0
        )

    def transform_to_show(
        self,
        raw_data: CszPhillyShowInstance,
        source_url: str = "",
    ) -> Optional[Show]:
        try:
            year = self._infer_year(raw_data.month)
            if year is None:
                Logger.warn(f"CszPhilly: unknown month abbreviation '{raw_data.month}' for {raw_data.event_name}")
                return None

            # Build datetime string: "2026-04-05 7:00 PM"
            month_num = _MONTH_MAP[raw_data.month]
            datetime_str = f"{year}-{month_num:02d}-{raw_data.day:02d} {raw_data.time}"

            start_date = ShowFactoryUtils.safe_parse_datetime_string(
                datetime_str,
                "%Y-%m-%d %I:%M %p",
                self.club.timezone or "America/New_York",
            )
            if not start_date:
                Logger.warn(f"CszPhilly: failed to parse datetime '{datetime_str}' for {raw_data.event_name}")
                return None

            ticket_url = _ticket_url(raw_data.event_id, self._session_key)
            tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

            return ShowFactoryUtils.create_enhanced_show_base(
                name=raw_data.event_name,
                club=self.club,
                date=start_date,
                show_page_url=ticket_url,
                lineup=[],
                tickets=tickets,
                enhanced=True,
            )

        except Exception as e:
            Logger.error(f"CszPhilly: transform failed for {raw_data.event_name}: {e}")
            return None

    def _infer_year(self, month_abbr: str) -> Optional[int]:
        """
        Infer the calendar year for a month abbreviation.

        Events returned by the VBO ``showevents`` endpoint are always upcoming,
        so month numbers earlier than the current month belong to the next year.
        """
        month_num = _MONTH_MAP.get(month_abbr)
        if month_num is None:
            return None
        now = datetime.now()
        if month_num >= now.month:
            return now.year
        return now.year + 1
