"""Goofs Comedy Club event extractor.

Goofs uses a custom Next.js app (goofscomedy.com). Show data is embedded in the
page HTML as a Next.js RSC (React Server Components) flight payload — specifically
inside `self.__next_f.push([1, "..."])` script calls, as a JSON-encoded string
containing an `initialShows` array.

No third-party ticketing platform is used; ticket purchase happens on-site.
"""

import json
import re
from typing import List

from laughtrack.core.entities.event.goofs import GoofsEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


_PUSH_PATTERN = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]')


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
        for raw_str in _PUSH_PATTERN.findall(html):
            try:
                # Decode the JSON-encoded string to get the RSC payload text
                decoded: str = json.loads('"' + raw_str + '"')
            except (json.JSONDecodeError, ValueError):
                continue

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

        Uses bracket counting to reliably extract the array, independent of the
        surrounding RSC tree structure.

        Returns:
            Parsed list of show dicts, or None on failure.
        """
        key = '"initialShows":'
        key_idx = text.find(key)
        if key_idx < 0:
            return None

        arr_start = text.find("[", key_idx + len(key))
        if arr_start < 0:
            return None

        depth = 0
        arr_end = -1
        for i, ch in enumerate(text[arr_start:]):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    arr_end = arr_start + i + 1
                    break

        if arr_end < 0:
            Logger.warn("GoofsEventExtractor: unmatched bracket in initialShows array")
            return None

        try:
            return json.loads(text[arr_start:arr_end])
        except (json.JSONDecodeError, ValueError) as e:
            Logger.warn(f"GoofsEventExtractor: failed to parse initialShows array: {e}")
            return None
