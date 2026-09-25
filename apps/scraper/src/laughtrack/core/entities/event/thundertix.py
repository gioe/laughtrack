"""
Data model for a single performance from any ThunderTix venue.

Show data is fetched from the ThunderTix calendar API:

  GET https://{venue-slug}.thundertix.com/reports/calendar?week=0&start={ts}&end={ts+7d}

Each item in the JSON array represents a single performance with title, start
datetime (with UTC offset), event/performance IDs, and ticket/show page URLs.

This entity replaces the per-venue ``AnnoyancePerformance`` and
``PostOfficeCafePerformance`` classes — the API response shape is identical
across ThunderTix venues, so a single generic entity drives the
``GenericThunderTixScraper``.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pytz
from dateutil import parser as dateutil_parser

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class ThunderTixPerformance(ShowConvertible):
    """Single performance returned by the ThunderTix calendar API."""

    event_id: int
    performance_id: int
    title: str
    start_dt: str  # raw datetime string, e.g. "2026-03-24 20:00:00 -0500"
    ticket_url: str  # full URL: base_url + order_products_url
    show_page_url: str  # full URL: base_url + truncated_url
    is_sold_out: bool = False
    price: Optional[float] = None  # detail-page JSON-LD AggregateOffer lowPrice
    time_with_timezone: Optional[str] = None  # merchant-displayed local performance time

    @classmethod
    def from_api_response(cls, data: dict, base_url: str) -> "ThunderTixPerformance":
        """Create a ThunderTixPerformance from a raw ThunderTix API dict."""
        order_products_url = data.get("order_products_url") or ""
        truncated_url = data.get("truncated_url") or ""
        return cls(
            event_id=int(data.get("event_id", 0)),
            performance_id=int(data.get("performance_id", 0)),
            title=data.get("title") or "",
            start_dt=data.get("start") or "",
            ticket_url=f"{base_url}{order_products_url}",
            show_page_url=f"{base_url}{truncated_url}",
            is_sold_out=bool(data.get("is_sold_out", False)),
            time_with_timezone=data.get("time_with_timezone"),
        )

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_dt:
            return None

        start_date = self.resolve_start_datetime(club)
        if start_date is None:
            return None

        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, price=self.price, sold_out=self.is_sold_out)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_date,
            show_page_url=self.show_page_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )

    def resolve_start_datetime(self, club: Club) -> Optional[datetime]:
        """Use verified venue-local display time when supplied by ThunderTix.

        Visani's calendar numeric offset is Central while its ticket page and
        time_with_timezone correctly advertise Eastern. Match the displayed
        abbreviation against the venue's IANA zone on this exact date instead
        of trusting that numeric offset. Keep aware-local entities (convention
        323). Callers must surface ValueError as a calendar data failure before
        reconciliation; malformed display data must never silently drop shows.
        """
        if self.time_with_timezone is not None:
            value = self.time_with_timezone
            match = re.fullmatch(
                r"([A-Za-z]{3})\s*-\s*([A-Za-z]{3}\s+\d{1,2},\s*\d{4})\s*-\s*(\d{1,2}:\d{2}\s*[AaPp][Mm])\s+([A-Za-z]{2,5})",
                value.strip() if isinstance(value, str) else "",
            )
            if not match or not club.timezone:
                raise ValueError(
                    f"Invalid ThunderTix displayed showtime for performance {self.performance_id}: {value!r}"
                )
            weekday, day, clock, abbreviation = match.groups()
            try:
                clock = re.sub(r"\s+", "", clock)
                wall_clock = datetime.strptime(f"{day} {clock}", "%b %d, %Y %I:%M%p")
                local = pytz.timezone(club.timezone).localize(wall_clock, is_dst=None)
            except (ValueError, pytz.UnknownTimeZoneError, pytz.InvalidTimeError) as exc:
                raise ValueError(
                    f"Invalid ThunderTix venue-local showtime for performance {self.performance_id}: {value!r}"
                ) from exc
            if local.strftime("%a").lower() != weekday.lower() or local.tzname() != abbreviation.upper():
                raise ValueError(
                    f"ThunderTix displayed weekday/timezone disagrees with venue for performance {self.performance_id}: {value!r} in {club.timezone}"
                )
            return local

        try:
            start_date = datetime.strptime(self.start_dt, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            # ThunderTix's calendar API serializes `start` differently depending
            # on request headers: the default is space-separated
            # ('2026-03-24 20:00:00 -0500'), but an Accept: application/json
            # request can return ISO-8601 ('2026-06-10T21:30:00.000-05:00').
            # strptime only handles the former — if ThunderTix ever flips the
            # default, every performance would silently drop (TASK-2837). Fall
            # back to dateutil (as the SimpleTix extractor does) and warn so the
            # serialization flip is visible in nightly logs.
            try:
                start_date = dateutil_parser.parse(self.start_dt)
            except (ValueError, TypeError, OverflowError):
                return None
            Logger.warn(
                f"ThunderTixPerformance: start '{self.start_dt}' did not match "
                "the primary '%Y-%m-%d %H:%M:%S %z' format; parsed via dateutil "
                "fallback (possible ThunderTix datetime serialization flip)"
            )

        return start_date
