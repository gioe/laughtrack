"""Transformer for classic SeatEngine HTML show dicts → Show objects."""

import re
from typing import Optional

import pytz
from dateutil import parser as dateutil_parser

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.utilities.datetime.utils import DateTimeUtils
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.logger.logger import Logger


def _parse_seatengine_classic_date(date_str: str, timezone: str) -> Optional[str]:
    """
    Parse classic SeatEngine date strings and return a UTC ISO string.

    Handles formats like:
      "Sun, Mar 22, 2026 3:00 PM"
      "Wed Mar 25 2026,  7:30 PM"
      "Fri, Apr  3, 2026 9:30 PM"   (extra spaces around day)
    """
    # Collapse multiple spaces and strip stray commas before time component
    cleaned = re.sub(r"\s+", " ", date_str).strip()
    # "Wed Mar 25 2026,  7:30 PM" → "Wed Mar 25 2026 7:30 PM"
    cleaned = re.sub(r",\s*(\d+:\d+)", r" \1", cleaned)
    try:
        dt = dateutil_parser.parse(cleaned, fuzzy=True)
    except Exception as e:
        Logger.warn(f"SeatEngineClassic: failed to parse date '{date_str}': {e}")
        return None
    if dt.tzinfo is None:
        tz = pytz.timezone(timezone)
        dt = tz.localize(dt)
    return DateTimeUtils.format_utc_iso_date(dt)


class SeatEngineClassicTransformer(DataTransformer[JSONDict]):

    def can_transform(self, raw_data: JSONDict) -> bool:  # type: ignore[override]
        return isinstance(raw_data, dict) and "name" in raw_data and "date_str" in raw_data

    def transform_to_show(
        self,
        raw_data: JSONDict,
        source_url: Optional[str] = None,
    ) -> Optional[Show]:  # type: ignore[override]
        try:
            date_str = raw_data.get("date_str") or ""
            parsed_date = None
            if date_str:
                parsed_date = _parse_seatengine_classic_date(date_str, self.club.timezone)

            show_url = raw_data.get("show_url")
            sold_out = bool(raw_data.get("sold_out", False))

            # Skip soldout shows with no URL — no link to surface to users
            if sold_out and not show_url:
                return None

            tickets = []
            if show_url and not sold_out:
                # sold_out is False in this branch by the condition above — not a hardcoded omission
                tickets.append(
                    Ticket(
                        price=0.0,
                        purchase_url=show_url,
                        sold_out=False,
                        type="General Admission",
                    )
                )
            elif sold_out:
                tickets.append(
                    Ticket(
                        price=0.0,
                        purchase_url=show_url or "",
                        sold_out=True,
                        type="General Admission",
                    )
                )

            # Treat event name as the headliner's name
            name = raw_data.get("name") or ""
            lineup = [Comedian(name)] if name else []

            return Show.create(
                name=name,
                date=parsed_date,
                show_page_url=show_url,
                description=None,
                tickets=tickets,
                lineup=lineup,
                timezone=self.club.timezone,
                club_id=self.club.id,
                room=None,
            )
        except Exception as e:
            Logger.error(f"SeatEngineClassic transformer failed: {e}")
            return None
