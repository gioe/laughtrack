"""
Async paginator for handling pagination with curl_cffi sessions.

This module provides an async-enabled paginator that works with curl_cffi AsyncSession
while leveraging the pagination logic from the base Paginator class.
"""

from typing import AsyncIterator, Dict, Optional

import asyncio

from curl_cffi.requests import AsyncSession

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.paginator.paginator import (
    Paginator,
    PaginatorConfig,
)


class AsyncPaginator(Paginator):
    """
    Async-enabled paginator that extends the base Paginator class.

    This class provides async pagination capabilities while reusing the
    URL discovery logic from the base Paginator class. It works with
    curl_cffi AsyncSession instead of the synchronous requests library.
    """

    def __init__(
        self,
        async_session: AsyncSession,
        parent_scraper,
        config: Optional[PaginatorConfig] = None,
    ):
        """
        Initialize the async paginator.

        Args:
            async_session: The curl_cffi AsyncSession to use for requests
            parent_scraper: Parent scraper instance for logging context
            config: Configuration for paginator behavior
        """
        super().__init__(config=config)
        self.async_session = async_session
        self.parent_scraper = parent_scraper

    async def async_pages(self, start_url: str, max_pages: int = 10) -> AsyncIterator[Dict[str, str]]:
        """
        Async version of pages() method that yields URL and content.

        This method handles pagination asynchronously, yielding each page's
        URL and HTML content. It includes infinite loop prevention and
        proper error handling.

        Args:
            start_url: Starting URL for pagination
            max_pages: Maximum number of pages to fetch

        Yields:
            Dict containing 'url' and 'html_content' for each page
        """
        self._visited_urls.clear()
        current_url = start_url
        page_count = 0

        while current_url and page_count < max_pages:
            # Prevent infinite loops by checking visited URLs
            if self.config.track_visited and current_url in self._visited_urls:
                break

            if self.config.track_visited:
                self._visited_urls.add(current_url)

            try:
                response = await self.async_session.get(current_url)
                if response.status_code != 200:
                    break

                html_content = response.text

                yield {"url": current_url, "html_content": html_content}

                # Optional stop condition
                if self.config.stop_condition:
                    try:
                        if self.config.stop_condition(html_content, current_url):
                            break
                    except Exception as e:
                        # Log and continue pagination by default
                        Logger.error(
                            f"Stop condition raised an error: {str(e)}",
                            self.parent_scraper.logger_context,
                        )

                # Find next page URL using parent class logic
                next_url = self.get_next_page_url(html_content, current_url)

                # Stop if no next page found or if next page is already visited
                if not next_url:
                    break
                elif self.config.track_visited and next_url in self._visited_urls:
                    break

                current_url = next_url
                page_count += 1

                # Optional delay between requests
                if self.config.delay_seconds and self.config.delay_seconds > 0:
                    await asyncio.sleep(self.config.delay_seconds)

            except Exception as e:
                Logger.error(
                    f"Error during pagination at {current_url}: {str(e)}",
                    self.parent_scraper.logger_context,
                )
                break
