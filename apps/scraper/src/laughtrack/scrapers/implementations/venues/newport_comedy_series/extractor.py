"""
Newport Comedy Series event extractor.

Newport Comedy Series (formerly Southcoast Comedy Series) uses the Punchup platform
with Next.js App Router and TanStack Query. Show data is embedded in the page HTML
as React Query hydration state inside self.__next_f.push() streaming calls.

This extractor delegates to the shared PunchupExtractor in core/clients/punchup/ and
wraps the resulting PunchupShow objects in the venue-specific NewportComedySeriesShow
subclass so that DataTransformer dispatch is unambiguous.
"""

import dataclasses
from dataclasses import dataclass
from typing import List

from laughtrack.core.clients.punchup.extractor import PunchupExtractor, PunchupShow


@dataclass
class NewportComedySeriesShow(PunchupShow):
    """A show parsed from Newport Comedy Series' Punchup page."""


class NewportComedySeriesExtractor:
    """Extracts shows from Newport Comedy Series' Punchup page, returning NewportComedySeriesShow objects."""

    @staticmethod
    def extract_shows(html_content: str) -> List[NewportComedySeriesShow]:
        """Extract shows and wrap them as NewportComedySeriesShow instances."""
        punchup_shows = PunchupExtractor.extract_shows(html_content)
        return [
            NewportComedySeriesShow(**{f.name: getattr(s, f.name) for f in dataclasses.fields(s)})
            for s in punchup_shows
        ]


__all__ = ["NewportComedySeriesShow", "NewportComedySeriesExtractor"]
