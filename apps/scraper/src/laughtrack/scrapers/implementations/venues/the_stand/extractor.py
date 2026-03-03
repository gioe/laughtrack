"""The Stand NYC data extraction utilities."""

import re
from typing import List
from urllib.parse import urljoin

from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

from laughtrack.foundation.infrastructure.logger.logger import Logger



class TheStandEventExtractor:
    """Utility class for extracting The Stand NYC event data from HTML content."""

    @staticmethod
    def extract_tixr_urls(html_content: str) -> List[str]:
        """
        Extract all Tixr URLs from The Stand NYC HTML content.

        Args:
            html_content: HTML content containing Tixr event links

        Returns:
            List of unique Tixr event URLs found in the page
        """
        try:
            urls = HtmlScraper.extract_links_by_regex_patterns(
                html=html_content,
                patterns=[r"https?://[^\s\"]*tixr\.com/[^\s\"]*/events/[^\s\"]*", r"/events/[^\s\"]*"],
            )
            return [u for u in urls if "tixr.com" in u and "/events/" in u]

        except Exception as e:
            Logger.error(f"Error extracting Tixr URLs from HTML: {e}")
            return []

    @staticmethod
    def extract_pagination_url(html_content: str, base_url: str) -> str:
        """
        Extract the next page URL using dual pagination logic.

        Handles The Stand's dual pagination:
        1. "More Shows" horizontal pagination (priority)
        2. Date-based calendar pagination (next month)

        Args:
            html_content: HTML content to parse
            base_url: Base URL for relative URL resolution

        Returns:
            Next page URL if found, empty string otherwise
        """
        try:
            # Priority 1: Look for More Shows button by class selector
            href = HtmlScraper.get_text_content(html_content, "a.btn.btn-outline-light.loading-btn[href]")
            # get_text_content returns text; we need href, so use a dedicated selector helper
            more_shows = HtmlScraper.find_elements_by_selector(html_content, "a.btn.btn-outline-light.loading-btn")
            if more_shows:
                link = more_shows[0]
                href_val = getattr(link, "get", lambda *_: None)("href")
                if isinstance(href_val, str):
                    return urljoin(base_url, href_val)

            # Priority 2: title contains 'month' or right-caret icon nesting
            anchors = HtmlScraper.find_elements(html_content, "a")
            for a in anchors:
                title = getattr(a, "get", lambda *_: None)("title")
                if isinstance(title, str) and "month" in title.lower():
                    href_val = getattr(a, "get", lambda *_: None)("href")
                    if isinstance(href_val, str):
                        return urljoin(base_url, href_val)

            # Fallback: caret icon parent anchor
            carets = HtmlScraper.find_elements(html_content, "i", class_="fas fa-caret-right")
            if carets:
                parent_a = getattr(carets[0], "find_parent", lambda *_: None)("a")
                if parent_a:
                    href_val = getattr(parent_a, "get", lambda *_: None)("href")
                    if isinstance(href_val, str):
                        return urljoin(base_url, href_val)

            return ""

        except Exception as e:
            Logger.error(f"Error extracting pagination URL from HTML: {e}")
            return ""
