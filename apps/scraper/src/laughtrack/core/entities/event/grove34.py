from dataclasses import dataclass
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class Grove34Event:
    """
    Data model representing a single event from Grove34's Webflow CMS site.
    Populated from JSON-LD found on individual show detail pages.
    """
    title: str
    start_date: str   # ISO UTC string from JSON-LD e.g. "2026-03-18T00:00:00.000Z"
    show_page_url: str
    timezone_id: str = "America/New_York"
    description: Optional[str] = None

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        try:
            # Strip milliseconds and ensure Z suffix (same pattern as old Wix code)
            # rstrip("Z") handles dates that already end with "Z" (no milliseconds),
            # preventing double-Z like "2026-03-18T00:00:00ZZ".
            # parse_wix_iso_date parses any ISO 8601 UTC string — works for Webflow/JSON-LD dates too
            clean_date_str = self.start_date.split(".")[0].rstrip("Z") + "Z"
            event_datetime = ShowFactoryUtils.parse_wix_iso_date(clean_date_str, self.timezone_id)
            if not event_datetime:
                return None

            return ShowFactoryUtils.create_enhanced_show_base(
                name=self.title,
                club=club,
                date=event_datetime,
                show_page_url=self.show_page_url,
                lineup=[],
                tickets=[],
                description=self.description,
                room="",
                supplied_tags=["event"],
                enhanced=enhanced,
            )
        except Exception as e:
            Logger.error(f"Error converting Grove34Event to show: {e}")
            return None
