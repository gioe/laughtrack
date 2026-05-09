"""Goofs Comedy Club event extractor.

Goofs uses a custom Next.js app (goofscomedy.com). Show data is embedded in the
page HTML as a Next.js RSC (React Server Components) flight payload — specifically
inside `self.__next_f.push([1, "..."])` script calls, as a JSON-encoded string
containing an `initialShows` array.

No third-party ticketing platform is used; ticket purchase happens on-site.
"""

from typing import List

from laughtrack.core.clients.rsc.extractor import extract_push_payloads, find_json_array
from laughtrack.core.entities.event.goofs import GoofsEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class GoofsEventExtractor:
    """Extracts GoofsEvent objects from the /p/shows HTML page."""

    @staticmethod
    def extract_shows(html: str) -> List[GoofsEvent]:
        """
        Parse upcoming shows from the Goofs /p/shows HTML page.

        The page embeds show data in Next.js RSC flight payloads as escaped JSON
        strings.  We locate the `initialShows` array within those payloads and
        parse each entry into a GoofsEvent.

        Args:
            html: Raw HTML content from https://goofscomedy.com/p/shows

        Returns:
            List of GoofsEvent objects (may be empty on parse failure).
        """
        for decoded in extract_push_payloads(html):
            if '"initialShows"' not in decoded:
                continue

            shows_data = GoofsEventExtractor._extract_initial_shows_array(decoded)
            if shows_data is None:
                continue

            events = []
            for item in shows_data:
                if not isinstance(item, dict):
                    continue
                try:
                    event = GoofsEvent.from_dict(item)
                    if event.display_title and event.date and event.time:
                        events.append(event)
                except Exception as e:
                    Logger.warn(f"GoofsEventExtractor: skipping show {item.get('id')}: {e}")
            if events:
                return events

        Logger.warn("GoofsEventExtractor: no initialShows array found in page HTML")
        return []

    @staticmethod
    def _extract_initial_shows_array(text: str):
        """
        Find the `initialShows` JSON array within a decoded RSC payload string.

        Delegates to the shared RSC helper so the venue only owns field mapping.

        Returns:
            Parsed list of show dicts, or None on failure.
        """
        shows = find_json_array(text, "initialShows")
        if shows is None and '"initialShows":' in text:
            Logger.warn("GoofsEventExtractor: unmatched bracket in initialShows array")
        return shows
