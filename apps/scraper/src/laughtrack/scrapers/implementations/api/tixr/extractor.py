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

    # Extracts the trailing numeric event ID from a long-form URL slug.
    # Matches the final -\d+ sequence (single-dash format with a digit ID).
    _LONG_URL_ID_RE = re.compile(r'-(\d+)$')

    @staticmethod
    def extract_tixr_urls(html_content: str) -> List[str]:
        """
        Extract all unique Tixr event URLs from calendar page HTML.

        Handles both short form (tixr.com/e/{id}) and long form
        (tixr.com/groups/*/events/*-{id}). Results are deduplicated
        by event ID across both forms — if the same event appears as
        both a short and long URL, only the short form is returned.
        Short-form URLs are returned first (in document order), followed
        by long-form URLs not already represented by a short-form link.

        Args:
            html_content: HTML content of a venue calendar page

        Returns:
            List of unique Tixr event URLs
        """
        seen_ids: set = set()
        seen_urls: set = set()
        urls: List[str] = []

        for match in TixrExtractor._SHORT_URL_RE.finditer(html_content):
            event_id = match.group(1)
            url = f"https://tixr.com/e/{event_id}"
            if event_id not in seen_ids:
                seen_ids.add(event_id)
                seen_urls.add(url)
                urls.append(url)

        for match in TixrExtractor._LONG_URL_RE.finditer(html_content):
            url = match.group(0)
            if url in seen_urls:
                continue
            id_match = TixrExtractor._LONG_URL_ID_RE.search(url)
            event_id = id_match.group(1) if id_match else None
            if event_id is None or event_id not in seen_ids:
                if event_id:
                    seen_ids.add(event_id)
                seen_urls.add(url)
                urls.append(url)

        return urls
