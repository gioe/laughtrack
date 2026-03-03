"""
Data model for scraped page data from The Stand NYC.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class TheStandPageData:
    """
    Data model representing raw extracted data from The Stand NYC pages.

    Contains the Tixr URLs extracted from The Stand's HTML pages,
    following the standard PageData pattern.
    """

    tixr_urls: List[str]

    def has_json_ld_data(self) -> bool:
        """Check if the scraped page contains any event data."""
        return bool(self.tixr_urls)

    def get_event_count(self) -> int:
        """Get the number of Tixr URLs found on the page."""
        return len(self.tixr_urls)
