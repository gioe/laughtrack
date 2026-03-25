"""Esther's Follies event extractor for the VBO Tickets date slider HTML."""

import re
from typing import List, Optional

from laughtrack.core.entities.event.esthers_follies import EsthersFolliesEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Matches each "SelectorBox" entry in the date slider HTML, capturing:
#   group 1: EDID (event date instance ID)
#   group 2: month abbreviation (e.g. "Mar")
#   group 3: day of month (e.g. "26")
#   group 4: weekday abbreviation (e.g. "Thu")
#   group 5: time string (e.g. "7:00 PM")
_SHOW_RE = re.compile(
    r'id="edid(\d+)"[^>]*onclick="LoadEvent[^"]+">.*?'
    r'<div class="DateMonth[^>]+>(\w+)<.*?'
    r'<div class="DateDay[^>]+>(\d+)<.*?'
    r'<span class="WeekDay">(\w+)</span>.*?'
    r'<span class="WeekDayTime"> - ([^<]+)</span>',
    re.DOTALL,
)


class EsthersFolliesEventExtractor:
    """Parse VBO Tickets date slider HTML into EsthersFolliesEvent objects.

    The date slider is fetched from:
      GET https://plugin.vbotickets.com/v5.0/controls/events.asp
        ?a=load_eventdate_slider&page=seatmap.asp
        &eid=39242&edid=0&req=1&s=<session>

    Response is a server-rendered HTML fragment containing a ``<ul>`` of
    ``<li>`` elements, each with a ``SelectorBox`` div per upcoming show.
    The first item is a "More Event Dates" calendar button — it has no
    ``LoadEvent`` onclick and is skipped by the regex.
    """

    @staticmethod
    def extract_shows(html: str, logger_context: Optional[dict] = None) -> List[EsthersFolliesEvent]:
        """Parse the date slider HTML fragment into a list of show slots.

        Args:
            html: Raw HTML from the VBO date slider endpoint.
            logger_context: Optional logging context dict.

        Returns:
            List of EsthersFolliesEvent objects (may be empty).
        """
        ctx = logger_context or {}
        if not html or not html.strip():
            Logger.warn("EsthersFolliesEventExtractor: empty HTML received", ctx)
            return []

        matches = _SHOW_RE.findall(html)
        if not matches:
            Logger.warn("EsthersFolliesEventExtractor: no shows found in HTML", ctx)
            return []

        events: List[EsthersFolliesEvent] = []
        seen: set = set()

        for edid, month, day_str, weekday, time_str in matches:
            try:
                day = int(day_str)
            except ValueError:
                Logger.warn(
                    f"EsthersFolliesEventExtractor: invalid day '{day_str}' for EDID {edid}",
                    ctx,
                )
                continue

            key = (edid, month, day, time_str.strip())
            if key in seen:
                continue
            seen.add(key)

            events.append(EsthersFolliesEvent(
                edid=edid,
                month=month,
                day=day,
                weekday=weekday,
                time=time_str.strip(),
            ))

        Logger.info(
            f"EsthersFolliesEventExtractor: extracted {len(events)} show slots",
            ctx,
        )
        return events
