"""Levity Live JSON-LD extraction utilities.

Handles the two-pass extraction pattern:
1. Calendar page: extract event list from @graph, collect sameAs detail URLs
2. Comic detail pages: extract per-showtime JSON-LD Event blocks
"""

from typing import List, Set

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper


class LevityLiveExtractor:
    """Extract events and detail URLs from Levity Live HTML pages."""

    @staticmethod
    def extract_detail_urls(html_content: str) -> Set[str]:
        """Extract unique sameAs URLs from the calendar page JSON-LD events.

        These are comic detail page URLs (e.g. levitylive.com/huntsville/comic/...)
        that contain per-showtime JSON-LD with individual ticket URLs.

        Note: JSONUtils.parse_json_ld_contents flattens @graph arrays, so each
        Event object appears as a top-level dict (not nested under @graph).
        """
        script_contents = HtmlScraper.get_json_ld_script_contents(html_content)
        if not script_contents:
            return set()

        json_objects = JSONUtils.parse_json_ld_contents(script_contents)
        if not json_objects:
            return set()

        urls: Set[str] = set()
        for obj in json_objects:
            if not isinstance(obj, dict):
                continue
            obj_type = (obj.get("@type") or "").lower()
            if obj_type not in ("event", "comedyevent"):
                continue
            same_as = obj.get("sameAs")
            if isinstance(same_as, str) and same_as:
                urls.add(same_as)
            elif isinstance(same_as, list):
                for u in same_as:
                    if isinstance(u, str) and u:
                        urls.add(u)
        return urls

    @staticmethod
    def extract_events_from_detail_page(
        html_content: str, detail_url: str
    ) -> List[JsonLdEvent]:
        """Extract per-showtime JsonLdEvent objects from a comic detail page.

        Comic detail pages have individual <script type="application/ld+json"> blocks
        per showtime (not wrapped in @graph), each with a unique TicketWeb URL.

        Sets same_as to the detail_url (levitylive.com) so that show_page_url
        points to the club's site rather than the third-party ticket URL.
        """
        script_contents = HtmlScraper.get_json_ld_script_contents(html_content)
        if not script_contents:
            return []

        json_objects = JSONUtils.parse_json_ld_contents(script_contents)
        if not json_objects:
            return []

        events: List[JsonLdEvent] = []
        for obj in json_objects:
            if not isinstance(obj, dict):
                continue
            obj_type = (obj.get("@type") or "").lower()
            if obj_type not in ("event", "comedyevent"):
                continue
            try:
                event = JsonLdEvent.from_json_ld(obj)
                # Set same_as to the detail page URL so show_page_url
                # points to levitylive.com instead of ticketweb.com
                if not event.same_as:
                    event.same_as = detail_url
                events.append(event)
            except (KeyError, ValueError):
                continue
        return events
