"""
Paginator base class — URL-discovery logic shared with AsyncPaginator.

Historically this module also performed sync HTTP fetches via `requests`. That
path has been removed: AsyncPaginator (curl_cffi AsyncSession + Playwright
fallback via HttpClient) is the only paginator used by scrapers, and this base
class now contributes only the config container and next-URL finder logic that
AsyncPaginator inherits. No new scrapers should instantiate `Paginator`
directly — use `AsyncPaginator` for paginated HTTP, or call `HtmlScraper`
utilities directly for one-off HTML parsing.
"""

from dataclasses import dataclass
from typing import Callable, Optional, Set

from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class PaginatorConfig:
    """Configuration shared between the Paginator base class and AsyncPaginator.

    Only `find_next_url` and `debug_mode` are read by the base `Paginator` class.
    The remaining fields (`stop_condition`, `track_visited`, `delay_seconds`) are
    consumed exclusively by `AsyncPaginator.async_pages()` — they exist on the
    base config so AsyncPaginator can share a single dataclass.
    """

    # Called with (html_content, base_url) -> next_url or None. Consumed by Paginator + AsyncPaginator.
    find_next_url: Optional[Callable[[str, str], Optional[str]]] = None

    # Optional: stop pagination early if condition is met; called with (html, url). AsyncPaginator only.
    stop_condition: Optional[Callable[[str, str], bool]] = None

    # Flow control. AsyncPaginator only.
    track_visited: bool = True
    delay_seconds: float = 0.0

    # Logging. Consumed by Paginator + AsyncPaginator.
    debug_mode: bool = False


class Paginator:
    """URL-discovery base class for AsyncPaginator.

    Holds the PaginatorConfig and the visited-URL set, and resolves the next
    page URL via the config's `find_next_url` callback. All HTTP I/O lives in
    AsyncPaginator.
    """

    def __init__(self, config: Optional[PaginatorConfig] = None):
        self.config = config or PaginatorConfig()
        self._visited_urls: Set[str] = set()
        self.debug_mode = self.config.debug_mode

    def get_next_page_url(self, html_content: str, base_url: str) -> Optional[str]:
        """Resolve the next page URL from HTML content using the configured finder."""
        finder = self.config.find_next_url
        if not finder:
            return None
        try:
            return finder(html_content, base_url)
        except Exception as e:
            if self.debug_mode:
                Logger.error(f"Error finding next page URL: {e}")
            return None
