"""
Four Day Weekend Comedy event data model.

Represents a single performance extracted from the OvationTix API.
Each FourDayWeekendEvent maps to one performance (date/time slot),
not a production — productions group multiple recurring performances.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class FourDayWeekendEvent:
    """
    A single upcoming performance from the OvationTix API for Four Day Weekend Comedy.

    One production (e.g. "Four Day Weekend Dallas") has many performances — one per
    show date/time.  This model represents a single performance entry from the
    `performances` array in the `Production({id})/performance?` response.

    Ticket pricing data is NOT available from the production listing endpoint.
    The OvationTix `Performance({id})` endpoint would provide `sections` with
    pricing, but fetching it per-performance (18+ API calls per run) is deferred.
    Shows are saved with the ticket purchase URL so users can buy on the OvationTix
    site even without pre-fetched pricing.
    # TODO: fetch per-performance sections for ticket pricing data
    """

    production_id: str
    performance_id: str
    production_name: str
    start_date: str          # "YYYY-MM-DD HH:MM" (local time, no timezone)
    tickets_available: bool
    event_url: str
    description: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        """Transform this performance into a Show object."""
        try:
            start_dt = self._parse_start_date(club.timezone)
            if not start_dt:
                Logger.error(
                    f"Could not parse start_date '{self.start_date}' for event "
                    f"'{self.production_name}' (perf {self.performance_id})"
                )
                return None

            return ShowFactoryUtils.create_enhanced_show_base(
                name=self.production_name,
                club=club,
                date=start_dt,
                show_page_url=self.event_url,
                lineup=[],
                tickets=[],
                description=self.description,
                room="",
                supplied_tags=["event"],
                enhanced=enhanced,
            )
        except Exception as e:
            Logger.error(f"Failed to transform FourDayWeekendEvent: {e}")
            return None

    def _parse_start_date(self, timezone: str) -> Optional[datetime]:
        """Parse 'YYYY-MM-DD HH:MM' local-time string into an aware datetime."""
        try:
            tz = pytz.timezone(timezone)
            naive = datetime.strptime(self.start_date, "%Y-%m-%d %H:%M")
            # is_dst=False picks the post-transition (standard time) interpretation
            # for ambiguous times during DST fall-back, rather than raising AmbiguousTimeError.
            return tz.localize(naive, is_dst=False)
        except Exception as e:
            Logger.error(f"Error parsing start_date '{self.start_date}': {e}")
            return None
