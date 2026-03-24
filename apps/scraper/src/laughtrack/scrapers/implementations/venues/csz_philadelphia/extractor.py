"""
CSz Philadelphia (ComedySportz) data extraction utilities.

Parses HTML from two VBO Tickets plugin endpoints:
  1. showevents  — lists all events for the venue; we extract comedy shows.
  2. load_eventdate_slider — lists individual upcoming instances for one event.
"""

import re
from typing import List, Tuple

from laughtrack.foundation.infrastructure.logger.logger import Logger

from .page_data import CszPhillyShowInstance


# Regex: match the outer div for each event in the showevents HTML.
# The div carries EID and EDID as CSS classes and data- attributes.
#
# Example (condensed):
#   <div id="EDID664181" class="EventListWrapper ... EID32872 EDID664181 ..."
#        data-event-name="Collegiate Comedy Challenge"
#        data-event-category="Performing Arts"
#        data-event-subcategory="Comedy" ...>
_EVENT_WRAPPER_RE = re.compile(
    r'id="EDID(\d+)"[^>]*?EID(\d+)[^>]*?'
    r'data-event-name="([^"]+)"[^>]*?'
    r'data-event-subcategory="Comedy"',
    re.DOTALL,
)

# Regex: one date-box inside the load_eventdate_slider response.
#
# Example (condensed):
#   <div ... id="edid655663" ...>
#     <div class="DateMonth __edid655663">Mar<div></div></div>
#     <div class="DateDay __edid655663">28<div></div></div>
#     <div class="DateTime __edid655663">
#       <span class="WeekDay">Sat</span>
#       <span class="WeekDayTime"> - 7:00 PM</span>
#     </div>
#   </div>
_DATE_BOX_RE = re.compile(
    r'id="edid(\d+)".*?'
    r'DateMonth[^>]*>([A-Za-z]+)<.*?'
    r'DateDay[^>]*>(\d+)<.*?'
    r'WeekDay">([^<]+)</span>'
    r'.*?WeekDayTime"> - ([^<]+)</span>',
    re.DOTALL,
)


class CszPhillyEventExtractor:
    """Utility class for extracting CSz Philadelphia show data from VBO Tickets HTML."""

    @staticmethod
    def parse_comedy_events(html: str) -> List[Tuple[int, int, str]]:
        """
        Extract comedy-show events from the VBO showevents HTML listing.

        Filters to events whose ``data-event-subcategory`` is ``"Comedy"``.

        Args:
            html: Raw HTML from the VBO ``showevents`` endpoint.

        Returns:
            List of ``(eid, edid, title)`` tuples for comedy shows, in page order.
        """
        try:
            results = []
            for match in _EVENT_WRAPPER_RE.finditer(html):
                edid = int(match.group(1))
                eid = int(match.group(2))
                title = match.group(3)
                results.append((eid, edid, title))
            return results
        except Exception as e:
            Logger.error(f"CszPhillyEventExtractor.parse_comedy_events failed: {e}")
            return []

    @staticmethod
    def parse_show_dates(html: str, event_id: int, event_name: str) -> List[CszPhillyShowInstance]:
        """
        Extract individual show instances from the VBO date-slider HTML.

        Each ``<div class="SelectorBox">`` inside the slider represents one
        scheduled performance with a month, day, weekday, and time.

        Args:
            html: Raw HTML from the VBO ``load_eventdate_slider`` endpoint.
            event_id: The VBO event ID (eid) for all returned instances.
            event_name: The show title to attach to all returned instances.

        Returns:
            List of ``CszPhillyShowInstance`` objects, one per date box found.
        """
        try:
            instances = []
            for match in _DATE_BOX_RE.finditer(html):
                edid = int(match.group(1))
                month = match.group(2).strip()
                day = int(match.group(3))
                weekday = match.group(4).strip()
                time_str = match.group(5).strip()
                instances.append(
                    CszPhillyShowInstance(
                        event_id=event_id,
                        event_date_id=edid,
                        event_name=event_name,
                        month=month,
                        day=day,
                        weekday=weekday,
                        time=time_str,
                    )
                )
            return instances
        except Exception as e:
            Logger.error(f"CszPhillyEventExtractor.parse_show_dates failed for eid={event_id}: {e}")
            return []
