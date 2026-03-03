"""
Paginator for handling pagination across different comedy venue websites.

This module provides a flexible pagination system that can handle different
types of pagination patterns found on comedy venue websites.
"""

from dataclasses import dataclass
from typing import Callable, Iterator, Optional, Set
import time

import requests

from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class PaginatorConfig:
    """Configuration for Paginator behavior.

    Clients should specify how to find the next page and any other behaviors
    rather than relying on paginator assumptions.
    """

    # Called with (html_content, base_url) -> next_url or None
    find_next_url: Optional[Callable[[str, str], Optional[str]]] = None

    # Optional: stop pagination early if condition is met; called with (html, url)
    stop_condition: Optional[Callable[[str, str], bool]] = None

    # Networking
    request_timeout: Optional[float] = 10.0
    headers: Optional[dict] = None
    session: Optional[requests.Session] = None

    # Flow control
    track_visited: bool = True
    delay_seconds: float = 0.0

    # Logging
    debug_mode: bool = False


class Paginator:
    """
    A flexible paginator for comedy venue websites.

    Supports multiple venue types and custom pagination logic.
    Includes infinite loop prevention through visited URL tracking.
    """

    def __init__(self, config: Optional[PaginatorConfig] = None):
        """
        Initialize the paginator with provided configuration.

        Args:
            config: PaginatorConfig controlling behavior. If omitted, a default
                    config is created and no next-page discovery is performed
                    unless a custom finder is later provided.
        """
        self.config = config or PaginatorConfig()
        self.session = self.config.session or requests.Session()
        if self.config.headers:
            try:
                self.session.headers.update(self.config.headers)
            except Exception as e:
                if self.config.debug_mode:
                    Logger.warning(f"Failed to apply headers to session: {e}")
        self._visited_urls: Set[str] = set()
        self.debug_mode = self.config.debug_mode

    def get_next_page_url(self, html_content: str, base_url: str) -> Optional[str]:
        """
        Get the next page URL from HTML content.

        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative URLs

        Returns:
            Next page URL if found, None otherwise
        """
        finder = self.config.find_next_url
        if not finder:
            # No finder configured; caller controls pagination decisions
            return None
        try:
            return finder(html_content, base_url)
        except Exception as e:
            if self.debug_mode:
                Logger.error(f"Error finding next page URL: {e}")
            return None

    def get_url_by_anchor_id(self, html_content: str, base_url: str, anchor_id: str) -> Optional[str]:
        """
        Find a URL by looking for an <a> tag with the given id and returning its href as an absolute URL.

        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative URLs
            anchor_id: The id attribute of the target <a> element containing the URL

        Returns:
            Absolute URL string if found; None otherwise.
        """
        try:
            return HtmlScraper.get_link_url_by_id(html_content, anchor_id=anchor_id, base_url=base_url)
        except Exception as e:
            if self.debug_mode:
                Logger.error(f"Error finding URL by anchor id '{anchor_id}': {e}")
            return None

    def pages(self, start_url: str, max_pages: int = 50) -> Iterator[str]:
        """
        Iterate through pages starting from start_url.

        Args:
            start_url: Starting URL to paginate from
            max_pages: Maximum number of pages to fetch (safety limit)

        Yields:
            HTML content of each page
        """
        current_url = start_url
        page_count = 0
        self._visited_urls.clear()  # Reset for new pagination sequence

        while current_url and page_count < max_pages:
            # Prevent infinite loops by tracking visited URLs
            if self.config.track_visited and current_url in self._visited_urls:
                if self.debug_mode:
                    Logger.warning(f"Already visited URL {current_url}, stopping pagination")
                break

            if self.config.track_visited:
                self._visited_urls.add(current_url)

            try:
                response = self.session.get(current_url, timeout=self.config.request_timeout)
                response.raise_for_status()
                html_content = response.text

                yield html_content

                # Optional stop condition provided by caller
                if self.config.stop_condition:
                    try:
                        if self.config.stop_condition(html_content, current_url):
                            if self.debug_mode:
                                Logger.info("Stop condition met; ending pagination")
                            break
                    except Exception as e:
                        if self.debug_mode:
                            Logger.warning(f"Stop condition raised an error: {e}")

                # Find next page URL
                next_url = self.get_next_page_url(html_content, current_url)
                current_url = next_url
                page_count += 1

                if self.debug_mode:
                    Logger.info(f"Paginated to page {page_count}, next URL: {next_url}")

                # Optional delay between requests
                if self.config.delay_seconds and self.config.delay_seconds > 0:
                    time.sleep(self.config.delay_seconds)

            except Exception as e:
                if self.debug_mode:
                    Logger.error(f"Error fetching page {current_url}: {e}")
                break

    def set_custom_next_finder(self, finder_func: Callable[[str, str], Optional[str]]):
        """
        Set a custom function for finding next page URLs.

        Args:
            finder_func: Function that takes (html_content, base_url) and returns next URL or None
        """
        self.config.find_next_url = finder_func

    def reset_visited_urls(self):
        """Reset the visited URLs tracking."""
        self._visited_urls.clear()

    def close(self):
        """Close the session."""
        self.session.close()
