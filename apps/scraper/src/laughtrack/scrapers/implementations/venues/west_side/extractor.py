"""
West Side Comedy Club event extractor.

West Side Comedy Club's website is built on the Punchup platform using Next.js App Router
with TanStack Query for data management. Show data is embedded in the page HTML as
React Query hydration state inside self.__next_f.push() streaming calls, NOT as JSON-LD.

This extractor delegates to the shared PunchupExtractor in core/clients/punchup/ and
re-exports PunchupShow/PunchupExtractor under the legacy WestSide* names for backward
compatibility.
"""

from laughtrack.core.clients.punchup.extractor import PunchupExtractor, PunchupShow

# Re-export under West Side names for backward compatibility
WestSideShow = PunchupShow
WestSideExtractor = PunchupExtractor

__all__ = ["WestSideShow", "WestSideExtractor"]
