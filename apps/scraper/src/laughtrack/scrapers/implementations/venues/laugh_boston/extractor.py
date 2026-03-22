"""Laugh Boston data extraction utilities."""

from typing import List

from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger


class LaughBostonEventExtractor:
    """Utility class for extracting Laugh Boston event data from HTML content."""

    @staticmethod
    def extract_tixr_urls(html_content: str) -> List[str]:
        """
        Extract all Tixr event URLs from the Laugh Boston homepage.

        The Laugh Boston homepage lists upcoming shows as direct Tixr links
        (tixr.com/groups/laughboston/events/*).

        Args:
            html_content: HTML content of the Laugh Boston homepage

        Returns:
            List of unique Tixr event URLs found in the page
        """
        try:
            urls = HtmlScraper.extract_links_by_regex_patterns(
                html=html_content,
                patterns=[
                    r"https?://[^\s\"']*tixr\.com/groups/[^\s\"']*/events/[^\s\"']*",
                ],
            )
            return [u for u in urls if "tixr.com" in u and "/events/" in u]

        except Exception as e:
            Logger.error(f"Error extracting Tixr URLs from Laugh Boston HTML: {e}")
            return []
