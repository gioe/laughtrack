"""
API Paginator for handling API-based pagination patterns.

This module provides pagination support for APIs that use offset/limit,
page number, or cursor-based pagination systems.
"""

from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import aiohttp

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.infrastructure.logger.logger import Logger


class ApiPaginator:
    """
    Handles API-based pagination for various patterns:
    - Offset/Limit (e.g., offset=0&limit=50)
    - Page-based (e.g., page=1&per_page=50)
    """

    def __init__(self, session: aiohttp.ClientSession, logger_context: Optional[JSONDict] = None):
        """
        Initialize the API paginator.

        Args:
            session: aiohttp session to use for requests
            logger_context: Context for logging (e.g., {'club': 'venue_name'})
        """
        self.session = session
        self.logger_context = logger_context or {}

    async def paginate_offset_limit(
        self,
        base_url: str,
        headers: Dict[str, str],
        initial_params: JSONDict,
        limit: int = 50,
        max_pages: int = 10,
        data_key: str = "events",
        extract_items: Optional[Callable[[JSONDict], List[Any]]] = None,
    ) -> AsyncIterator[List[Any]]:
        """
        Paginate through an API using offset/limit pagination.

        Args:
            base_url: Base API URL
            headers: HTTP headers to include in requests
            initial_params: Initial query parameters
            limit: Number of items per page
            max_pages: Maximum number of pages to fetch
            data_key: Key in response JSON that contains the data array
            extract_items: Optional function to extract items from response

        Yields:
            List of items from each page
        """
        offset = 0
        page_count = 0

        while page_count < max_pages:
            # Prepare parameters for this page
            params = initial_params.copy()
            params.update({"offset": offset, "limit": limit})

            try:
                async with self.session.get(base_url, headers=headers, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()

                    # Extract items using custom function or default key
                    if extract_items:
                        items = extract_items(data)
                    else:
                        items = data.get(data_key, [])

                    if not items:
                        # End of data reached
                        break

                    yield items

                    # If we got fewer items than limit, we've reached the end
                    if len(items) < limit:
                        break

                    offset += limit
                    page_count += 1

            except Exception as e:
                Logger.error(f"Error during offset/limit pagination at offset {offset}: {e}", self.logger_context)
                break

    async def paginate_page_based(
        self,
        base_url: str,
        headers: Dict[str, str],
        initial_params: JSONDict,
        per_page: int = 50,
        max_pages: int = 10,
        data_key: str = "events",
        extract_items: Optional[Callable[[JSONDict], List[Any]]] = None,
    ) -> AsyncIterator[List[Any]]:
        """
        Paginate through an API using page-based pagination.

        Args:
            base_url: Base API URL
            headers: HTTP headers to include in requests
            initial_params: Initial query parameters
            per_page: Number of items per page
            max_pages: Maximum number of pages to fetch
            data_key: Key in response JSON that contains the data array
            extract_items: Optional function to extract items from response

        Yields:
            List of items from each page
        """
        page = 1

        while page <= max_pages:
            # Prepare parameters for this page
            params = initial_params.copy()
            params.update({"page": page, "per_page": per_page})

            try:
                async with self.session.get(base_url, headers=headers, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()

                    # Extract items using custom function or default key
                    if extract_items:
                        items = extract_items(data)
                    else:
                        items = data.get(data_key, [])

                    if not items:
                        # End of data reached
                        break

                    yield items

                    # If we got fewer items than per_page, we've reached the end
                    if len(items) < per_page:
                        break

                    page += 1

            except Exception as e:
                Logger.error(f"Error during page-based pagination on page {page}: {e}", self.logger_context)
                break

    async def collect_all_pages(self, pagination_method: str, **kwargs) -> List[Any]:
        """
        Collect all items from all pages into a single list.

        Args:
            pagination_method: Either 'offset_limit' or 'page_based'
            **kwargs: Arguments to pass to the pagination method

        Returns:
            List of all items from all pages
        """
        all_items = []

        if pagination_method == "offset_limit":
            async for page_items in self.paginate_offset_limit(**kwargs):
                all_items.extend(page_items)
        elif pagination_method == "page_based":
            async for page_items in self.paginate_page_based(**kwargs):
                all_items.extend(page_items)
        else:
            raise ValueError(f"Unknown pagination method: {pagination_method}")

        return all_items
