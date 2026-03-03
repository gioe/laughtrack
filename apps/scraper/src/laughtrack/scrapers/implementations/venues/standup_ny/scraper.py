"""
StandUp NY specialized scraper.

This scraper implements the 5-component architecture for StandUp NY's complex workflow:
1. GraphQL API discovery and querying (ShowTix4U/VenuePilot)
2. VenuePilot ticket enhancement for applicable events
3. Data transformation to standardized Show objects

Expected club.scraping_url formats:
- GraphQL endpoint: https://api.showtix4u.com/graphql
- Calendar page: https://standupny.com/upcoming-shows/#/calendar (GraphQL endpoint will be discovered)
"""

from typing import List, Optional
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show

from laughtrack.foundation.models.types import JSONDict
from laughtrack.infrastructure.config.presets import BatchConfigPresets
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.scrapers.implementations.venues.standup_ny.extractor import StandupNYEventExtractor
from laughtrack.scrapers.implementations.venues.standup_ny.transformer import StandupNYEventTransformer
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper
from laughtrack.utilities.infrastructure.scraper import log_filter_breakdown


class StandupNYScraper(BaseScraper):
    """
    Specialized scraper for StandUp NY following the 5-component architecture.

    Uses a flexible multi-step workflow:
    1. Analyze club.scraping_url - if it's GraphQL, use directly; otherwise discover from calendar
    2. Query GraphQL endpoint to get event data including ticket URLs
    3. For VenuePilot ticket URLs, fetch detailed ticket information in parallel
    4. Transform combined data into standardized Show objects
    """

    key = "standup_ny"

    def __init__(self, club: Club):
        super().__init__(club)
        self.transformer = StandupNYEventTransformer(club)
        self.extractor = StandupNYEventExtractor(self.logger_context)

        # Initialize batch scraper for VenuePilot URL processing
        self.batch_scraper = BatchScraper(
            config=BatchConfigPresets.get_api_endpoint_config(),
            logger_context={"club": club.name, "scraper": "standupny"},
        )

    async def discover_urls(self) -> List[str]:
        """
        Discover events by querying GraphQL API and identifying VenuePilot URLs.

        Returns:
            List of VenuePilot ticket URLs that need enhancement
        """
        session = await self.get_session()

        try:
            # Extract events using the dedicated extractor
            self.page_data = await self.extractor.extract_events(session, self.club.scraping_url)

            if not self.page_data:
                Logger.warn("No events found during GraphQL discovery", self.logger_context)
                return []

            # Get VenuePilot URLs that need enhancement
            venuepilot_urls = self.page_data.get_venue_pilot_urls()

            Logger.info(
                f"Discovered {self.page_data.get_event_count()} events, "
                f"{len(venuepilot_urls)} need VenuePilot enhancement",
                self.logger_context,
            )

            return venuepilot_urls

        except Exception as e:
            Logger.error(f"Error in discover_urls: {e}", self.logger_context)
            self.page_data = None
            return []

    async def get_data(self, url: str) -> Optional[JSONDict]:
        """
        Extract VenuePilot enhancement data for a single URL.

        Args:
            url: VenuePilot ticket URL to enhance

        Returns:
            Enhanced event data or None if enhancement failed
        """
        if not hasattr(self, "page_data") or not self.page_data:
            Logger.error("No page data available for VenuePilot enhancement", self.logger_context)
            return None

        # Find the event for this URL
        event = self.page_data.find_event_by_ticket_url(url)
        if not event:
            Logger.warn(f"No event found for ticket URL: {url}", self.logger_context)
            return None

        session = await self.get_session()

        # Use extractor to enhance the event with VenuePilot data
        success = await self.extractor.enhance_event_with_venue_pilot(session, event)

        if success:
            Logger.debug(f"Successfully enhanced event {event.id} with VenuePilot data", self.logger_context)
            return {"enhanced_event": event, "url": url}
        else:
            Logger.warn(f"Failed to enhance event {event.id} with VenuePilot data", self.logger_context)
            return None

    async def transform_data(self, raw_data: JSONDict, source_url: str) -> List[Show]:
        """
        Transform enhanced event data to Show objects.

        Args:
            raw_data: Enhanced event data from extract_data
            source_url: VenuePilot URL for the enhancement

        Returns:
            List of Show objects (should contain one Show per event)
        """
        # Individual events are transformed during process_data phase
        # This method is not used in our custom workflow
        return []

    async def scrape_async(self) -> List[Show]:
        """
        Custom scraping workflow for StandUp NY following the 5-component architecture.

        Overrides the default BaseScraper workflow to implement:
        1. GraphQL discovery via discover_urls()
        2. VenuePilot enhancement via extract_data() in parallel
        3. Data transformation via transformer
        """
        try:
            # Step 1: Discover URLs and extract base event data
            venuepilot_urls = await self.discover_urls()

            if not hasattr(self, "page_data") or not self.page_data:
                Logger.warn("No base event data available", self.logger_context)
                return []

            # Step 2: Enhance VenuePilot events in parallel if any URLs found
            if venuepilot_urls:
                Logger.info(f"Enhancing {len(venuepilot_urls)} VenuePilot events", self.logger_context)

                # Diagnostics: log breakdown of VenuePilot slugs prior to enhancement
                def _extract_slug(u: str) -> Optional[str]:
                    try:
                        # Expected format: https://tickets.venuepilot.com/e/<slug>
                        parts = u.split("/e/")
                        return parts[1].split("/")[0] if len(parts) > 1 else None
                    except Exception:
                        return None

                log_filter_breakdown(
                    venuepilot_urls,
                    self.logger_context,
                    id_getter=_extract_slug,
                    accept_predicate=lambda u: bool(_extract_slug(u)),
                    label="VenuePilot enhancement",
                    name_getter=lambda u: u,
                    date_getter=None,
                )

                # Process VenuePilot URLs using batch processing
                async def process_single_url(url: str) -> Optional[JSONDict]:
                    """Process a single VenuePilot URL with error handling."""
                    try:
                        return await self.get_data(url)
                    except Exception:
                        return None

                # Process URLs in parallel
                results = await self.batch_scraper.process_batch(
                    venuepilot_urls, process_single_url, "VenuePilot enhancement"
                )

                # Log enhancement results
                enhanced_count = sum(1 for result in results if result is not None)
                Logger.info(
                    f"Successfully enhanced {enhanced_count}/{len(venuepilot_urls)} VenuePilot events",
                    self.logger_context,
                )

            # Step 3: Transform all events (enhanced + non-enhanced) to Show objects
            if not self.transformer.can_transform(self.page_data):
                Logger.error("Transformer cannot handle page data", self.logger_context)
                return []

            shows = self.transformer.transform_to_shows(self.page_data, self.club.scraping_url)

            Logger.info(f"StandUp NY scraping completed. Found {len(shows)} shows", self.logger_context)

            return shows

        except Exception as e:
            Logger.error(f"Scraping failed: {e}", self.logger_context)
            raise
        finally:
            # Ensure proper session cleanup in all code paths
            await self.close()

    async def cleanup(self):
        """Cleanup method for proper resource management."""
        try:
            # Clean up session via AsyncHttpMixin
            await self.close()

            # Clear any stored page data
            if hasattr(self, "page_data"):
                self.page_data = None

        except Exception as e:
            Logger.warn(f"Error during cleanup: {e}", self.logger_context)
