"""HAHA Comedy Club data extraction utilities."""

import re
from typing import List


class HaHaComedyClubExtractor:
    """Utility class for extracting HAHA Comedy Club event data from HTML content."""

    # Matches short Tixr event URLs: https://tixr.com/e/{id}
    _TIXR_SHORT_URL_RE = re.compile(r'https?://(?:www\.)?tixr\.com/e/(\d+)', re.IGNORECASE)

    @staticmethod
    def extract_tixr_urls(html_content: str) -> List[str]:
        """
        Extract all Tixr short-form event URLs from the HAHA Comedy Club calendar HTML.

        HAHA's calendar embeds ticket links in the form https://tixr.com/e/{id}.

        Args:
            html_content: HTML content of the calendar page

        Returns:
            List of unique Tixr event URLs found in the page
        """
        seen = set()
        urls = []
        for match in HaHaComedyClubExtractor._TIXR_SHORT_URL_RE.finditer(html_content):
            url = f"https://tixr.com/e/{match.group(1)}"
            if url not in seen:
                seen.add(url)
                urls.append(url)
        return urls
