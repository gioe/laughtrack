"""
RSC payload extraction for Comedy Club Haug (comedyclubhaug.com).

The site is a Next.js app backed by Craft CMS. The /shows page embeds all
upcoming events in the RSC streaming payload as a `shows` prop containing
a JSON array of event objects.

Each event object has fields:
  - eventTitle: str
  - eventSubtitle: str (often contains performer names in sentence form)
  - eventProgramStart: ISO 8601 datetime with offset
  - eventProgramEnd: ISO 8601 datetime with offset
  - eventStatus: "active" | "sold_out" | etc.
  - eventTicketLink: Stager ticket URL
  - url: comedyclubhaug.com show page URL
  - artists: list of artist objects with title (name) field
  - eventCategories: list of category objects with title field
"""

import json
import re

from typing import Dict, List, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger


class ComedyClubHaugExtractor:
    """Extracts show data from Comedy Club Haug's Next.js RSC payload."""

    # Regex to capture RSC push content
    _RSC_PUSH_RE = re.compile(
        r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)',
        re.DOTALL,
    )

    @staticmethod
    def extract_shows(html: str) -> List[Dict]:
        """
        Extract show event objects from the RSC payload of /shows page.

        The shows data lives in a large RSC chunk containing a React component
        tree with a `shows` prop holding the full event array.

        Args:
            html: Raw HTML from https://comedyclubhaug.com/shows

        Returns:
            List of event dicts with keys like eventTitle, eventProgramStart, etc.
        """
        if not html:
            return []

        # Strategy: find individual event objects by their unique signature
        # (they start with {"id":"...", and contain eventTitle)
        events = ComedyClubHaugExtractor._extract_from_rsc_chunks(html)
        if events:
            return events

        # Fallback: try regex extraction directly from HTML
        return ComedyClubHaugExtractor._extract_from_raw_html(html)

    @staticmethod
    def _extract_from_rsc_chunks(html: str) -> List[Dict]:
        """Extract events from decoded RSC push chunks."""
        events: List[Dict] = []

        for push_match in ComedyClubHaugExtractor._RSC_PUSH_RE.finditer(html):
            raw = push_match.group(1)

            try:
                decoded: str = json.loads('"' + raw + '"')
            except Exception:
                continue

            # Look for the shows array in this chunk
            shows_idx = decoded.find('"shows":[{')
            if shows_idx == -1:
                continue

            # Extract individual event objects from the shows array
            # Each event starts with {"id":" and has "url":"https://comedyclubhaug.com/shows/
            pattern = re.compile(
                r'\{"id":"\d+","title":"[^"]+","url":"https://comedyclubhaug\.com/shows/[^"]+","slug":"[^"]+'
            )
            for match in pattern.finditer(decoded):
                event = ComedyClubHaugExtractor._extract_single_event(
                    decoded, match.start()
                )
                if event:
                    events.append(event)

            if events:
                break  # Found the data chunk

        return events

    @staticmethod
    def _extract_single_event(text: str, start: int) -> Optional[Dict]:
        """
        Extract a single balanced JSON event object starting at the given position.

        Walks through the text counting braces to find the matching close brace.
        """
        bracket_count = 0
        end = start
        for i, c in enumerate(text[start:start + 15000]):
            if c == "{":
                bracket_count += 1
            elif c == "}":
                bracket_count -= 1
                if bracket_count == 0:
                    end = start + i + 1
                    break
        else:
            return None

        event_str = text[start:end]
        # Replace RSC references ($XX) with null for valid JSON
        event_str = re.sub(r'"\$[0-9a-f]+"', "null", event_str)

        try:
            return json.loads(event_str)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _extract_from_raw_html(html: str) -> List[Dict]:
        """Fallback: extract event data from raw HTML patterns."""
        events: List[Dict] = []

        # Decode unicode escapes in the full HTML
        try:
            decoded = html.encode().decode("unicode_escape", errors="ignore")
        except Exception:
            decoded = html

        pattern = re.compile(
            r'\{"id":"\d+","title":"[^"]+","url":"https://comedyclubhaug\.com/shows/[^"]+","slug":"[^"]+'
        )
        for match in pattern.finditer(decoded):
            event = ComedyClubHaugExtractor._extract_single_event(
                decoded, match.start()
            )
            if event:
                events.append(event)

        return events
