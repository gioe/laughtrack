"""
Standardized batch scraping utilities for venue scrapers.

Provides consistent patterns for parallel processing of URLs with:
- Configurable concurrency limits
- Rate limiting and delays
- Error handling and exception isolation
- Logging and progress tracking
- Resource cleanup
"""

import asyncio
from typing import Awaitable, Callable, List, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.types import JSONDict, T
from .config import BatchScrapingConfig


class BatchScraper:
    """
    Standardized batch processing utility for venue scrapers.

    Provides consistent patterns for parallel URL processing with proper
    error handling, rate limiting, and resource management.
    """

    def __init__(self, logger_context: JSONDict, config: Optional[BatchScrapingConfig] = None):
        """
        Initialize the batch scraper.

        Args:
            config: Batch scraping configuration
            logger_context: Context for logging (e.g., {'club': 'venue_name'})
        """
        if config is None:
            # Lazy import to avoid circular dependency at import time
            from laughtrack.infrastructure.config.presets import BatchConfigPresets

            config = BatchConfigPresets.get_conservative_config()
        self.config = config
        self.logger_context = logger_context

    async def process_batch(
        self, items: List[str], processor: Callable[[str], Awaitable[T]], description: str = "batch processing"
    ) -> List[T]:
        """
        Process a list of URLs/items in parallel with semaphore control.

        Args:
            items: List of URLs or items to process
            processor: Async function to process each item
            description: Description for logging

        Returns:
            List of successfully processed results
        """
        if not items:
            if self.config.enable_logging:
                Logger.info(f"No items to process for {description}", self.logger_context)
            return []

        if self.config.enable_logging:
            Logger.info(
                f"Starting {description} for {len(items)} items (max_concurrent={self.config.max_concurrent})",
                self.logger_context,
            )

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def process_with_semaphore_and_delay(item: str) -> Optional[T]:
            """Process a single item with semaphore and delay."""
            async with semaphore:
                try:
                    # Add delay between requests to be respectful
                    if self.config.delay_between_requests > 0:
                        await asyncio.sleep(self.config.delay_between_requests)

                    result = await processor(item)
                    return result

                except Exception as e:
                    if self.config.enable_logging:
                        Logger.error(f"Failed to process {item} in {description}: {e}", self.logger_context)
                    return None

        # Create tasks for all items
        tasks = [process_with_semaphore_and_delay(item) for item in items]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results and count failures
        successful_results = []
        successful_count = 0
        failed_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                if self.config.enable_logging:
                    Logger.error(f"Exception in {description} for {items[i]}: {result}", self.logger_context)
            elif result is not None:
                successful_results.append(result)
                successful_count += 1
            else:
                failed_count += 1

        if self.config.enable_logging:
            summary = f"Completed {description}: {successful_count} successful, {failed_count} failed"
            if failed_count == 0:
                Logger.info(summary, self.logger_context)
            else:
                Logger.error(summary, self.logger_context)

        return successful_results

    async def process_in_batches(
        self, items: List[str], processor: Callable[[str], Awaitable[T]], description: str = "batch processing"
    ) -> List[T]:
        """
        Process items in smaller batches with delays between batches.

        This is useful for very large lists of items where you want to
        limit the total load on the target server.

        Args:
            items: List of URLs or items to process
            processor: Async function to process each item
            description: Description for logging

        Returns:
            List of successfully processed results
        """
        if not items:
            return []

        if self.config.batch_size is None:
            # Process all at once
            return await self.process_batch(items, processor, description)

        all_results = []
        total_batches = (len(items) + self.config.batch_size - 1) // self.config.batch_size

        if self.config.enable_logging:
            Logger.info(
                f"Processing {len(items)} items in {total_batches} batches of size {self.config.batch_size}",
                self.logger_context,
            )

        for i in range(0, len(items), self.config.batch_size):
            batch_num = (i // self.config.batch_size) + 1
            batch = items[i : i + self.config.batch_size]

            batch_description = f"{description} (batch {batch_num}/{total_batches})"
            batch_results = await self.process_batch(batch, processor, batch_description)
            all_results.extend(batch_results)

            # Add delay between batches (except after the last batch)
            if i + self.config.batch_size < len(items) and self.config.batch_delay > 0:
                if self.config.enable_logging:
                    Logger.info(f"Waiting {self.config.batch_delay}s before next batch", self.logger_context)
                await asyncio.sleep(self.config.batch_delay)

        return all_results
