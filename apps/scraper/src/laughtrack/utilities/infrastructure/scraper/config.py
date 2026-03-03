"""
Configuration types for batch scraping utilities.

This module isolates configuration dataclasses from the scraper implementation
to avoid circular imports with presets and other utilities.
"""

from typing import Optional


class BatchScrapingConfig:
    """Configuration for batch scraping operations."""

    def __init__(
        self,
        max_concurrent: int = 5,
        delay_between_requests: float = 0.5,
        batch_delay: float = 1.0,
        batch_size: Optional[int] = None,
        enable_logging: bool = True,
    ):
        """
        Initialize batch scraping configuration.

        Args:
            max_concurrent: Maximum number of concurrent requests
            delay_between_requests: Delay in seconds between individual requests
            batch_delay: Delay in seconds between batches (if using batch processing)
            batch_size: Size of each batch (None means process all at once)
            enable_logging: Whether to log progress and results
        """
        self.max_concurrent = max_concurrent
        self.delay_between_requests = delay_between_requests
        self.batch_delay = batch_delay
        self.batch_size = batch_size
        self.enable_logging = enable_logging
