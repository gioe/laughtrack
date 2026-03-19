"""
West Side Comedy Club event extractor.

West Side Comedy Club's website is built on the Punchup platform using Next.js App Router
with TanStack Query for data management. Show data is embedded in the page HTML as
React Query hydration state inside self.__next_f.push() streaming calls, NOT as JSON-LD.

This extractor delegates to the shared PunchupExtractor in core/clients/punchup/ and
wraps the resulting PunchupShow objects in the venue-specific WestSideShow subclass so
that DataTransformer dispatch is unambiguous (isinstance checks are distinct per venue).
"""

import dataclasses
from dataclasses import dataclass
from typing import List

from laughtrack.core.clients.punchup.extractor import PunchupExtractor, PunchupShow


@dataclass
class WestSideShow(PunchupShow):
    """A show parsed from West Side Comedy Club's Punchup page."""


class WestSideExtractor:
    """Extracts shows from West Side Comedy Club's Punchup page, returning WestSideShow objects."""

    @staticmethod
    def extract_shows(html_content: str) -> List[WestSideShow]:
        """Extract shows and wrap them as WestSideShow instances."""
        punchup_shows = PunchupExtractor.extract_shows(html_content)
        return [
            WestSideShow(**{f.name: getattr(s, f.name) for f in dataclasses.fields(s)})
            for s in punchup_shows
        ]


__all__ = ["WestSideShow", "WestSideExtractor"]
