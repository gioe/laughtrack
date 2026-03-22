"""Improv Asylum data extraction utilities."""

from typing import List

from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ImprovAsylumEventExtractor:
    """Utility class for extracting Improv Asylum event data from HTML content."""

    @staticmethod
    def extract_tixr_urls(html_content: str) -> List[str]:
        """
        Extract Tixr event URLs for Improv Asylum from a Tixr group page.

        The Tixr group page (tixr.com/groups/improvasylum) lists upcoming
        events as links matching tixr.com/groups/improvasylum/events/*.

        Args:
            html_content: HTML content of the Tixr group page

        Returns:
            List of unique Tixr event URLs found in the page
        """
        try:
            urls = HtmlScraper.extract_links_by_regex_patterns(
                html=html_content,
                patterns=[
                    r"https?://[^\s\"']*tixr\.com/groups/improvasylum/events/[^\s\"']*",
                ],
            )
            return [u for u in urls if "tixr.com" in u and "/events/" in u]

        except Exception as e:
            Logger.error(f"Error extracting Tixr URLs from Improv Asylum HTML: {e}")
            return []
