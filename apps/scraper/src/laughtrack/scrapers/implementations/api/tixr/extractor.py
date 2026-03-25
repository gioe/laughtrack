"""Generic Tixr URL extraction utilities."""

import re
from typing import List


class TixrExtractor:
    """Extracts Tixr event URLs (short and long form) from calendar page HTML."""

    # Short form: https://tixr.com/e/{id}
    _SHORT_URL_RE = re.compile(
        r'https?://(?:www\.)?tixr\.com/e/(\d+)',
        re.IGNORECASE,
    )

    # Long form: https://www.tixr.com/groups/{group}/events/{slug}-{id}
    # Captured as the full URL; client handles --{id} (won't-fix) skipping.
    _LONG_URL_RE = re.compile(
        r'https?://(?:www\.)?tixr\.com/groups/[^\s"\'<>]+/events/[^\s"\'<>]+',
        re.IGNORECASE,
    )

    @staticmethod
    def extract_tixr_urls(html_content: str) -> List[str]:
        """
        Extract all unique Tixr event URLs from calendar page HTML.

        Handles both short form (tixr.com/e/{id}) and long form
        (tixr.com/groups/*/events/*-{id}). Results are deduplicated
        while preserving order of first occurrence.

        Args:
            html_content: HTML content of a venue calendar page

        Returns:
            List of unique Tixr event URLs
        """
        seen: set = set()
        urls: List[str] = []

        for match in TixrExtractor._SHORT_URL_RE.finditer(html_content):
            url = f"https://tixr.com/e/{match.group(1)}"
            if url not in seen:
                seen.add(url)
                urls.append(url)

        for match in TixrExtractor._LONG_URL_RE.finditer(html_content):
            url = match.group(0)
            if url not in seen:
                seen.add(url)
                urls.append(url)

        return urls
