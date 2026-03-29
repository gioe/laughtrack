"""
Simplified JSON-LD scraper implementation using standardized project patterns.

This implementation leverages the project's architectural abstractions:
- BaseScraper pipeline for standard workflow
- Built-in fetch methods with error handling and retries
- URL discovery manager for pagination support
- Standardized error handling and logging
- Proper session management and cleanup

Clean single-responsibility architecture:
- JsonLdExtractor: HTML → JSON-LD dictionaries
- JSONLdTransformer: JSON-LD dictionaries → Show objects
- JsonLdScraper: Orchestrates extraction and transformation
"""

from typing import Optional, TYPE_CHECKING

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils
from .transformer import JsonLdTransformer

if TYPE_CHECKING:
    # Only imported for type hints to avoid heavy imports at module import time
    from .data import JsonLdPageData
    from .extractor import EventExtractor  # noqa: F401


class JsonLdScraper(BaseScraper):
    """
    Simplified JSON-LD scraper using standardized project patterns.

    This implementation:
    1. Uses BaseScraper's standard pipeline (discover_urls → extract_data → transform_data)
    2. Leverages built-in fetch methods with error handling and retries
    3. Uses URL discovery manager for pagination support
    4. Follows established error handling and logging patterns
    5. Separates concerns: extraction vs transformation
    """

    key = "json_ld"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(JsonLdTransformer(club))

    async def get_data(self, url: str) -> Optional["JsonLdPageData"]:
        """
        Extract JSON-LD data from a webpage using standardized fetch methods.

        Returns raw JSON-LD dictionaries, not transformed objects.
        """
        try:
            # Local imports to prevent circular imports during module discovery
            from .data import JsonLdPageData
            from .extractor import EventExtractor
            # Use BaseScraper's standardized fetch_html with built-in error handling
            normalized_url = URLUtils.normalize_url(url)
            html_content = await self.fetch_html(normalized_url)

            # Parse HTML and extract JSON-LD (events only)
            event_list = EventExtractor.extract_events(html_content)

            if not event_list:
                if html_content:
                    Logger.warn(
                        f"{self.__class__.__name__} [{self._club.name}]: Page loaded but contained no JSON-LD events: {normalized_url}",
                        self.logger_context,
                    )
                return None

            return JsonLdPageData(event_list)

        except Exception as e:
            Logger.error(f"{self.__class__.__name__} [{self._club.name}]: Error extracting data from {url}: {str(e)}", self.logger_context)
            return None
