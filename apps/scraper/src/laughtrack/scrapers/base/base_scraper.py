"""
Base scraper class for the new architecture.

This module provides the abstract base class for all scrapers, implementing a standardized
scraping pipeline with support for different data extraction methods, rate limiting,
error handling, and data transformation.

The BaseScraper follows the 5-Component Architecture pattern as defined in the
scraper-architecture-patterns.md documentation.
"""

import asyncio
import concurrent.futures
import contextvars
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Awaitable, Callable, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.http.diagnostics import (
    ScrapeDiagnostics,
    bind_diagnostics,
    current_diagnostics,
    reset_diagnostics,
)
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.shared.types import ScrapingTarget
from laughtrack.ports.scraping import EventListContainer
from laughtrack.ports.http import HttpConvenienceMixin

from laughtrack.shared.errors import ErrorHandler, RetryConfig
from laughtrack.scrapers.utils.rate_limiting import RateLimiter
from laughtrack.scrapers.utils.url_discovery import create_discovery_manager
from laughtrack.scrapers.base.pipeline import create_standard_pipeline
from laughtrack.shared.logging import Logger


class BaseScraper(HttpConvenienceMixin, ABC):
    """
    Abstract base class for all scrapers implementing the standardized scraping pipeline.

    This class provides a complete scraping framework that supports multiple extraction patterns:
    - Direct data extraction (JSON-LD, API responses)
    - Multi-step workflows (link discovery + data extraction)
    - Mixed approaches combining different strategies

    The scraper follows a standardized pipeline:
    1. collect_scraping_targets() - Discover URLs or identifiers to process
    2. process_target() - For each target, extract and transform data
    3. get_data() - Extract raw data from source (abstract method)
    4. transform_data() - Transform raw data to Show objects

    Key Features:
    - Domain-wide rate limiting coordination
    - Async and synchronous operation support
    - Configurable retry logic with exponential backoff
    - Extensible data processing pipeline
    - Standardized HTTP session management
    - Comprehensive error handling and classification
    - Flexible URL discovery strategies

    Target Processing:
    The collect_scraping_targets() method can return two types of items:
    1. Actual URLs (most common) - processed directly by get_data()
    2. Identifiers/keys (e.g., date strings) - used by get_data() to construct requests

    This flexible approach accommodates different scraping patterns:
    - URL-based: Broadway Comedy Club returns actual URLs to scrape
    - Identifier-based: Comedy Cellar returns date strings used to make API calls

    Attributes:
        key (str): Unique identifier that must match the club.scraper field
        club (Club): The club configuration for this scraper
        rate_limiter (RateLimiter): Domain-specific rate limiting
        transformation_pipeline: Data transformation pipeline
        error_handler (ErrorHandler): Retry and error handling logic
        url_discovery: URL discovery management
        logger_context (dict): Logging context for this scraper

    Examples:
        Basic scraper implementation:

        ```python
        class VenueScraper(BaseScraper):
            key = "venue_identifier"

            async def get_data(self, target: ScrapingTarget) -> Optional[EventListContainer]:
                # Extract data from URL or using identifier
                html = await self.fetch_html(target)
                return VenuePageData(event_list=extract_events(html))
        ```

        Custom workflow override:

        ```python
        async def scrape_async(self) -> List[Show]:
            # Custom multi-step workflow
            auth_token = await self.authenticate()
            targets = await self.discover_authenticated_targets(auth_token)
            return await self.process_targets_with_auth(targets, auth_token)
        ```
    """

    # Each scraper must define its unique key that matches the club.scraper field
    key: Optional[str] = None

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None) -> None:
        """
        Initialize the scraper with club configuration and infrastructure components.

        Args:
            club: Club entity containing scraper configuration, rate limits,
                 retry settings, and venue-specific parameters.
            proxy_pool: Optional ProxyPool for rotating proxy support. When provided,
                 subclasses should forward it to any BaseApiClient they construct.

        Raises:
            ValueError: If club configuration is invalid
        """
        super().__init__()
        self._club = club  # Store as private attribute to avoid conflict with AsyncHttpMixin
        self.proxy_pool: Optional[ProxyPool] = proxy_pool

        # Set up logging context for this scraper instance (augment with scraper key)
        self.logger_context = {**club.as_context(), "scraper": self.key or "-"}

        # Always wire in the unified rate limiter; override RPS when the club
        # specifies an explicit rate_limit.
        self.rate_limiter: RateLimiter = RateLimiter()
        if club.rate_limit:
            self.rate_limiter.set_domain_limit(club.scraping_domain, club.rate_limit)

        # Initialize transformation pipeline
        self.transformation_pipeline = create_standard_pipeline(club)

        # Initialize error handler with retry configuration
        retry_config = RetryConfig(max_attempts=club.max_retries + 1, base_delay=1.0, max_delay=30.0)
        self.error_handler = ErrorHandler(retry_config)

        # Initialize URL discovery manager
        self.url_discovery = create_discovery_manager()

    @property
    def club(self) -> Club:
        """Get the club instance for this scraper."""
        return self._club

    @property
    def _log_prefix(self) -> str:
        """Logging prefix shared by all Logger calls in this scraper."""
        return f"{self.__class__.__name__} [{self._club.name}]"

    async def get_session(self, headers=None, proxy_url=None):
        """
        Override AsyncHttpMixin.get_session() to auto-inject a proxy URL from the
        pool when proxy_pool is configured and no explicit proxy_url is supplied.
        """
        if proxy_url is None and self.proxy_pool is not None:
            proxy_url = self.proxy_pool.get_proxy()
        return await super().get_session(headers=headers, proxy_url=proxy_url)

    async def _fetch_html_with_js(self, url: str) -> Optional[str]:
        """Fetch page HTML using the shared PlaywrightBrowser singleton.

        Use this instead of fetch_html() when the target page requires JavaScript
        execution to render event data (i.e. curl_cffi returns only the page shell).
        Uses the shared browser instance managed by _get_js_browser() to avoid
        leaking Chromium processes.

        PlaywrightBrowser uses wait_until='domcontentloaded'. This is sufficient
        for pages where event rows are server-side rendered into the initial HTML
        payload. Only override with networkidle if events load via a post-DOMContent
        XHR.

        Returns:
            The rendered HTML string, or None if Playwright is unavailable or the
            fetch fails.
        """
        try:
            import asyncio
            from laughtrack.foundation.infrastructure.http.client import _get_js_browser
            browser = _get_js_browser()
            if browser is None:
                Logger.warn(
                    f"{self._log_prefix}: Playwright unavailable for {url}",
                    self.logger_context,
                )
                return None
            return await asyncio.wait_for(browser.fetch_html(url), timeout=60)
        except asyncio.TimeoutError:
            Logger.warn(
                f"{self._log_prefix}: Playwright fetch timed out after 60s for {url}",
                self.logger_context,
            )
            return None
        except Exception as e:
            Logger.warn(
                f"{self._log_prefix}: Playwright fetch failed for {url}: {e}",
                self.logger_context,
            )
            return None

    def scrape(self) -> List[Show]:
        """
        Synchronously scrape shows from the venue.

        This is a convenience method that runs the async version in an appropriate event loop.
        It handles the complexity of running async code from sync contexts, including
        cases where an event loop is already running.

        Returns:
            List[Show]: Show objects found at the venue

        Raises:
            Exception: Any scraping errors are propagated after cleanup
        """
        try:
            # Try to get the current event loop
            asyncio.get_running_loop()
            # If we reach here, we're in an async context with a running loop
            # We need to run in a separate thread to avoid "RuntimeError: cannot be called from a running event loop".
            # copy_context() propagates ContextVars (notably the ScrapeDiagnostics
            # binding from scrape_with_result) into the worker thread; a plain
            # executor.submit starts with a fresh context and the side-channel
            # would silently record into the void.
            ctx = contextvars.copy_context()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(ctx.run, asyncio.run, self.scrape_async())
                return future.result()
        except RuntimeError:
            # No event loop is running, we can safely use asyncio.run
            return asyncio.run(self.scrape_async())

    async def scrape_async(self) -> List[Show]:
        """
        Asynchronously scrape shows using a two-phase pipeline for optimal performance.

        This method implements an optimized scraping workflow:
        1. Collect scraping targets (URLs or identifiers)
        2. Phase 1: Concurrently fetch all raw data (async I/O)
        3. Phase 2: Transform all raw data to Show objects (sync CPU work)

        The separation of async I/O and sync transformation prevents blocking
        the event loop and maximizes concurrent data fetching performance.

        The method can be overridden by subclasses for custom workflows
        (e.g., authentication, multi-step APIs, complex data gathering).

        Returns:
            List[Show]: All shows found across all processed targets

        Raises:
            Exception: Scraping errors are logged and re-raised after cleanup
        """
        try:
            # Step 1: Collect URLs or identifiers to scrape
            targets = await self.collect_scraping_targets()
            count = len(targets)
            if count > 1:
                Logger.info(f"{self._log_prefix}: Found {count} targets to process", self.logger_context)
            elif count == 1:
                Logger.info(f"{self._log_prefix}: Found target to process", self.logger_context)
            else:
                Logger.info(f"{self._log_prefix}: Found 0 targets to process", self.logger_context)

            # Step 2: Phase 1 - Concurrent async data fetching
            raw_data_results = await self._fetch_all_raw_data(targets)

            # Step 3: Phase 2 - Sync transformation of all raw data
            all_shows = self._transform_all_raw_data(raw_data_results)

            Logger.info(f"{self._log_prefix}: Scraped {len(all_shows)} total shows", self.logger_context)
            return all_shows

        except Exception as e:
            Logger.error(f"{self._log_prefix}: Scraping failed: {e}", self.logger_context)
            raise
        finally:
            # Clean up resources
            await self._cleanup_resources()

    async def _cleanup_resources(self) -> None:
        """Clean up scraper resources, handling errors gracefully."""
        try:
            # Call close() if it exists in the subclass (HTTP sessions, etc.)
            if hasattr(self, "close") and callable(getattr(self, "close")):
                await getattr(self, "close")()
        except Exception as cleanup_error:
            Logger.error(f"{self._log_prefix}: Error during cleanup: {cleanup_error}", self.logger_context)

    async def _fetch_all_raw_data(
        self, targets: List[ScrapingTarget]
    ) -> List[tuple[Optional[EventListContainer], ScrapingTarget]]:
        """
        Phase 1: Concurrently fetch raw data from all targets using async I/O.

        This method maximizes I/O concurrency by fetching data from all targets
        simultaneously, without blocking on CPU-bound transformation work.

        Args:
            targets: List of URLs or identifiers to fetch data from

        Returns:
            List of tuples containing (raw_data, target) pairs. raw_data will be
            None if fetching failed for that target.
        """

        async def fetch_single_target(target: ScrapingTarget) -> tuple[Optional[EventListContainer], ScrapingTarget]:
            """Fetch data from a single target with error handling and rate limiting."""
            try:
                # Apply domain-appropriate rate limiting before each fetch
                await self.rate_limiter.await_if_needed(target)

                # Extract raw data using retry logic
                async def _fetch_with_retry() -> Optional[EventListContainer]:
                    return await self.get_data(target)

                raw_data = await self.error_handler.execute_with_retry(_fetch_with_retry, f"Fetch Data: {target}")

                Logger.debug(f"{self._log_prefix}: Fetched data from {target}", self.logger_context)
                return raw_data, target

            except Exception as e:
                Logger.error(f"{self._log_prefix}: Failed to fetch data from {target}: {e}", self.logger_context)
                return None, target

        # Fetch all targets concurrently
        count = len(targets)
        if count > 1:
            Logger.info(f"{self._log_prefix}: Starting concurrent fetch of {count} targets", self.logger_context)
        elif count == 1:
            Logger.info(f"{self._log_prefix}: Starting concurrent fetch of target", self.logger_context)
        else:
            Logger.info(f"{self._log_prefix}: Starting concurrent fetch of 0 targets", self.logger_context)
        results = await asyncio.gather(*[fetch_single_target(target) for target in targets])

        successful_fetches = sum(1 for raw_data, _ in results if raw_data is not None)
        Logger.info(f"{self._log_prefix}: Successfully fetched data from {successful_fetches}/{len(targets)} targets", self.logger_context)

        return results

    def _transform_all_raw_data(
        self, raw_data_results: List[tuple[Optional[EventListContainer], ScrapingTarget]]
    ) -> List[Show]:
        """
        Phase 2: Transform all raw data to Show objects using sync CPU processing.

        This method processes all the raw data collected in Phase 1, converting
        it to standardized Show objects. Since transformation is CPU-bound work,
        it's done synchronously to avoid blocking the async event loop.

        Args:
            raw_data_results: List of (raw_data, target) tuples from Phase 1

        Returns:
            List[Show]: All successfully transformed Show objects
        """
        all_shows: List[Show] = []

        diagnostics = current_diagnostics()
        successful_transforms = 0
        for raw_data, target in raw_data_results:
            if raw_data is None:
                continue

            # Record raw event count before dedup/date/validation filters run
            # downstream — lets a 0-show result distinguish "parser returned
            # nothing" from "filter dropped everything".
            if diagnostics is not None and hasattr(raw_data, "event_list"):
                try:
                    diagnostics.add_items_before_filter(len(raw_data.event_list))
                except TypeError:
                    pass

            try:
                shows = self.transform_data(raw_data, target)
                all_shows.extend(shows)
                successful_transforms += 1
                Logger.debug(f"{self._log_prefix}: Transformed {len(shows)} shows from {target}", self.logger_context)
            except Exception as e:
                Logger.error(f"{self._log_prefix}: Failed to transform data from {target}: {e}", self.logger_context)
                continue

        Logger.info(
            f"{self._log_prefix}: Successfully transformed data from {successful_transforms} targets into {len(all_shows)} shows",
            self.logger_context,
        )
        return all_shows

    def scrape_with_result(self):
        """
        Scrape shows and return a comprehensive result with execution metrics.

        This method wraps the standard scrape() method to provide additional
        execution information including timing, error handling, and success metrics.
        Useful for monitoring, debugging, and batch processing scenarios.

        Returns:
            ClubScrapingResult: Comprehensive result containing:
                - club_name: Name of the scraped club
                - shows: List of successfully scraped Show objects
                - execution_time: Time taken in seconds
                - error: Error message if scraping failed, None if successful

        Note:
            This method always returns a result object, never raises exceptions.
            Check the 'error' field to determine if scraping was successful.
        """
        # Late import to avoid circular dependencies during module import
        from laughtrack.core.models.results import ClubScrapingResult

        start_time = datetime.now()
        diagnostics = ScrapeDiagnostics()
        # Ensure all logs in this scrape carry club/scraper context
        with Logger.use_context(self.logger_context):
            token = bind_diagnostics(diagnostics)
            try:
                Logger.info(f"{self._log_prefix}: Starting scrape", self.logger_context)
                shows = self.scrape()
                execution_time = (datetime.now() - start_time).total_seconds()

                Logger.info(
                    f"{self._log_prefix}: Successfully scraped {len(shows)} shows in {execution_time:.2f}s",
                    self.logger_context,
                )

                return ClubScrapingResult(
                    club_name=self.club.name,
                    shows=shows,
                    execution_time=execution_time,
                    club_id=getattr(self.club, 'id', None),
                    http_status=diagnostics.http_status,
                    bot_block_detected=diagnostics.bot_block_detected,
                    bot_block_signature=diagnostics.bot_block_signature,
                    bot_block_provider=diagnostics.bot_block_provider,
                    bot_block_type=diagnostics.bot_block_type,
                    bot_block_source=diagnostics.bot_block_source,
                    bot_block_stage=diagnostics.bot_block_stage,
                    playwright_fallback_used=diagnostics.playwright_fallback_used,
                    items_before_filter=diagnostics.items_before_filter,
                )
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                error_msg = str(e)

                Logger.error(
                    f"{self._log_prefix}: Failed to scrape after {execution_time:.2f}s: {error_msg}", self.logger_context
                )

                return ClubScrapingResult(
                    club_name=self.club.name,
                    shows=[],
                    execution_time=execution_time,
                    error=error_msg,
                    club_id=self.club.id,
                    http_status=diagnostics.http_status,
                    bot_block_detected=diagnostics.bot_block_detected,
                    bot_block_signature=diagnostics.bot_block_signature,
                    bot_block_provider=diagnostics.bot_block_provider,
                    bot_block_type=diagnostics.bot_block_type,
                    bot_block_source=diagnostics.bot_block_source,
                    bot_block_stage=diagnostics.bot_block_stage,
                    playwright_fallback_used=diagnostics.playwright_fallback_used,
                    items_before_filter=diagnostics.items_before_filter,
                )
            finally:
                reset_diagnostics(token)

    async def collect_scraping_targets(self) -> List[ScrapingTarget]:
        """
        Discover URLs or identifiers to scrape from the venue.

        This method determines what should be scraped by discovering URLs or
        identifiers that will be processed by the pipeline. The default implementation
        uses the URL discovery manager with a 'static' strategy, but can be overridden
        for custom discovery logic.

        Discovery Strategies:
        - Static: Use the club's scraping_url directly
        - Dynamic: Parse pages to find event URLs (e.g., Broadway Comedy Club)
        - API-based: Query APIs for endpoint lists
        - Date-based: Generate date ranges for API calls (e.g., Comedy Cellar)

        Returns:
            List[ScrapingTarget]: URLs or identifiers for processing. Items can be:
                - Actual URLs (most common) - passed directly to get_data()
                - Date strings, IDs, or other identifiers used by get_data()
                  to construct API requests or build dynamic URLs

        Raises:
            Exception: If target discovery fails completely

        Examples:
            URL-based discovery (Broadway Comedy Club):
            ```
            ["https://venue.com/show/123", "https://venue.com/show/124"]
            ```

            Identifier-based discovery (Comedy Cellar):
            ```
            ["2024-01-15", "2024-01-16", "2024-01-17"]
            ```
        """
        session = await self.get_session()
        targets = await self.url_discovery.discover_urls(self.club.scraping_url, session)

        Logger.debug(f"{self._log_prefix}: Discovered {len(targets)} scraping targets", self.logger_context)
        return targets

    async def process_target(self, target: ScrapingTarget) -> List[Show]:
        """
        Process a single URL or identifier through the complete data extraction pipeline.

        This method provides backward compatibility and single-target processing
        for cases where the full two-phase pipeline isn't needed. It combines
        both async data fetching and sync transformation for a single target.

        For optimal performance with multiple targets, prefer using scrape_async()
        which uses the two-phase approach.

        Args:
            target: URL to process or identifier to use for data extraction.
                   This could be an actual URL (most common) or an identifier
                   like a date string that get_data() knows how to handle.

        Returns:
            List[Show]: Show objects extracted and transformed from this target

        Raises:
            Exception: Any errors during processing (after retry attempts)
        """
        # Fetch raw data for this single target
        raw_data_results = await self._fetch_all_raw_data([target])

        # Transform the raw data (if any was fetched)
        return self._transform_all_raw_data(raw_data_results)

    @abstractmethod
    async def get_data(self, target: ScrapingTarget) -> Optional[EventListContainer]:
        """
        Extract raw data from a specific URL or using an identifier.

        This is the core data extraction method that must be implemented by each scraper.
        It handles the actual data retrieval from the venue's website or API, whether
        that's scraping HTML, calling REST APIs, or processing other data sources.

        The method should be flexible enough to handle both URL-based scraping
        (where url_or_identifier is an actual URL) and identifier-based scraping
        (where url_or_identifier is a date, ID, or other identifier used to
        construct the request).

        Args:
            url_or_identifier: Either:
                - A URL to extract data from (most common)
                - An identifier (date string, event ID, etc.) that this scraper
                  knows how to use to fetch data (e.g., for API calls)

        Returns:
            Optional[EventListContainer]: Raw data object that implements the
                EventListContainer protocol (has event_list attribute), or None
                if extraction failed or no data was found.

        Raises:
            Exception: Any extraction errors should be allowed to propagate
                for handling by the retry mechanism.

        Implementation Examples:
            HTML scraping:
            ```python
            async def get_data(self, url_or_identifier: ScrapingTarget) -> Optional[EventListContainer]:
                html = await self.fetch_html(url_or_identifier)
                events = extract_json_ld_events(html)
                return VenuePageData(event_list=events) if events else None
            ```

            API with identifier:
            ```python
            async def get_data(self, url_or_identifier: ScrapingTarget) -> Optional[EventListContainer]:
                # url_or_identifier is a date string like "2024-01-15"
                api_url = f"https://api.venue.com/events?date={url_or_identifier}"
                response = await self.fetch_json(api_url)
                events = [VenueEvent(**item) for item in response['events']]
                return VenuePageData(event_list=events) if events else None
            ```
        """
        pass

    def transform_data(self, raw_data: EventListContainer, source_url_or_identifier: ScrapingTarget) -> List[Show]:
        """
        Transform raw extracted data into standardized Show objects.

        This method applies the transformation pipeline to convert venue-specific
        raw data into the standardized Show format used throughout the application.
        The transformation handles data validation, normalization, and formatting.

        This is a synchronous method since transformation is CPU-bound work
        that doesn't benefit from async/await patterns.

        Args:
            raw_data: Raw scraped data implementing EventListContainer protocol.
                     Must have an event_list attribute containing venue-specific event objects.
            source_url_or_identifier: URL or identifier the data was scraped from.
                                    Used for error reporting and data provenance.

        Returns:
            List[Show]: Validated and standardized Show objects. Returns empty list
                       if transformation fails or no valid events are found.

        Implementation Notes:
            - The method checks if raw_data implements EventListContainer protocol
            - Uses the club's transformation pipeline for standardized processing
            - Handles errors gracefully, logging issues and returning empty list
            - Can be overridden for custom transformation logic

        Examples:
            Standard transformation (most common):
            ```python
            # Uses default implementation - no override needed
            shows = self.transform_data(page_data, "https://venue.com/events")
            ```

            Custom transformation override:
            ```python
            def transform_data(self, raw_data: EventListContainer, source: ScrapingTarget) -> List[Show]:
                # Custom preprocessing
                processed_events = self.preprocess_events(raw_data.event_list)
                # Use pipeline for standard transformation
                return self.transformation_pipeline.transform(processed_events)
            ```
        """
        try:
            # Verify the data implements the EventListContainer protocol
            if not hasattr(raw_data, "event_list"):
                Logger.error(
                    f"{self._log_prefix}: Raw data does not implement EventListContainer protocol. "
                    f"Missing 'event_list' attribute. Type: {type(raw_data)}",
                    self.logger_context,
                )
                return []

            # Check if the data is transformable (has events)
            if hasattr(raw_data, "is_transformable") and not raw_data.is_transformable():
                Logger.debug(
                    f"{self._log_prefix}: No transformable events in raw data from {source_url_or_identifier}", self.logger_context
                )
                return []

            # Apply the transformation pipeline
            shows = self.transformation_pipeline.transform(raw_data)
            Logger.debug(f"{self._log_prefix}: Successfully transformed {len(shows)} shows", self.logger_context)
            return shows

        except Exception as e:
            Logger.error(
                f"{self._log_prefix}: Transformation pipeline failed for {source_url_or_identifier}: {str(e)}", self.logger_context
            )
            return []

    # Batch Processing Support

    async def process_targets_in_batches(
        self,
        targets: List[ScrapingTarget],
        process_function: Optional[Callable[[ScrapingTarget], Awaitable[List[Show]]]] = None,
        batch_size: int = 10,
        max_concurrent: int = 5,
    ) -> List[Show]:
        """
        Process multiple targets in batches with concurrency control.

        This method provides optimized batch processing using the two-phase approach:
        Phase 1 fetches data concurrently, Phase 2 transforms synchronously.
        For custom processing functions, it falls back to the original approach.

        Args:
            targets: List of targets (URLs, date strings, IDs, etc.) to process
            process_function: Optional custom function to process each target.
                            If None, uses the optimized two-phase approach.
                            Function signature: async def func(target) -> List[Show]
            batch_size: Number of targets to process concurrently in each batch
            max_concurrent: Maximum number of concurrent operations

        Returns:
            List[Show]: Flattened list of all Show objects from all targets

        Example:
            # Optimized processing using two-phase approach
            shows = await self.process_targets_in_batches(urls)

            # Custom processing function (falls back to original approach)
            async def custom_processor(target):
                # Custom logic here
                return await some_custom_processing(target)

            shows = await self.process_targets_in_batches(
                date_strings,
                process_function=custom_processor,
                batch_size=5
            )
        """
        if not targets:
            Logger.info(f"{self._log_prefix}: No targets to process in batch", self.logger_context)
            return []

        # If no custom function provided, use optimized two-phase approach
        if process_function is None:
            Logger.info(f"{self._log_prefix}: Using optimized two-phase batch processing for {len(targets)} targets", self.logger_context)
            raw_data_results = await self._fetch_all_raw_data(targets)
            return self._transform_all_raw_data(raw_data_results)

        # Fall back to original batch processing for custom functions
        processor = process_function

        Logger.info(
            f"{self._log_prefix}: Starting batch processing of {len(targets)} targets "
            f"(batch_size={batch_size}, max_concurrent={max_concurrent})",
            self.logger_context,
        )

        all_shows: List[Show] = []

        # Process targets in batches
        for i in range(0, len(targets), batch_size):
            batch = targets[i : i + batch_size]
            Logger.debug(f"{self._log_prefix}: Processing batch {i//batch_size + 1}: {len(batch)} targets", self.logger_context)

            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_with_semaphore(target):
                async with semaphore:
                    try:
                        return await processor(target)
                    except Exception as e:
                        Logger.error(f"{self._log_prefix}: Error processing target {target}: {e}", self.logger_context)
                        return []

            # Process batch concurrently
            batch_results = await asyncio.gather(
                *[process_with_semaphore(target) for target in batch], return_exceptions=True
            )

            # Aggregate results from this batch
            for result in batch_results:
                if isinstance(result, Exception):
                    Logger.error(f"{self._log_prefix}: Batch processing exception: {result}", self.logger_context)
                    continue

                if result is not None and isinstance(result, list):
                    all_shows.extend(result)

            Logger.debug(f"{self._log_prefix}: Batch completed. Total shows so far: {len(all_shows)}", self.logger_context)

        Logger.info(
            f"{self._log_prefix}: Batch processing complete. Processed {len(targets)} targets, found {len(all_shows)} total shows",
            self.logger_context,
        )

        return all_shows
