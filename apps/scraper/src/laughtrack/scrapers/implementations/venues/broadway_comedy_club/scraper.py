"""
Simplified Broadway Comedy Club scraper implementation using standardized project patterns.

This implementation leverages the project's architectural abstractions:
- BaseScraper pipeline for standard workflow
- Built-in fetch methods with error handling and retries
- URL discovery manager for pagination support
- Standardized error handling and logging
- Proper session management and cleanup

Clean single-responsibility architecture:
- BroadwayEventExtractor: HTML → BroadwayEvent objects
- BroadwayEventTransformer: BroadwayEvent objects → Show objects
- BroadwayComedyClubScraper: Orchestrates extraction and transformation
"""

from typing import List, Optional

from laughtrack.core.clients.tessera.instances.broadway import BroadwayTesseraClient
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.broadway import BroadwayEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.utilities.infrastructure.scraper import log_filter_breakdown
from laughtrack.scrapers.utils.tessera_enrichment import TesseraTicketBatchEnricher

from .data import BroadwayEventData
from .extractor import BroadwayEventExtractor
from .transformer import BroadwayEventTransformer


class BroadwayComedyClubScraper(BaseScraper):
    """
    Simplified Broadway Comedy Club scraper using standardized project patterns.

    This implementation:
    1. Uses BaseScraper's standard pipeline (discover_urls → extract_data → transform_data)
    2. Leverages built-in fetch methods with error handling and retries
    3. Uses URL discovery manager for pagination support
    4. Follows established error handling and logging patterns
    5. Separates concerns: extraction vs transformation
    """

    key = "broadway"

    def __init__(self, club: Club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(BroadwayEventTransformer(club))
        self.tessera_client = BroadwayTesseraClient(club, proxy_pool=self.proxy_pool)
        # Use a factory method for a reusable enrichment pattern across scrapers
        self._tickets = self._make_ticket_enricher()
        # Precompute base domain for absolute URL building
        self._base_url = URLUtils.get_base_domain_with_protocol(
            URLUtils.normalize_url(self.club.scraping_url)
        )

    def _make_ticket_enricher(self):
        """Factory method for ticket enrichment.

        Scrapers can override this to provide the appropriate enricher for their source.
        Returning None disables ticket enrichment.
        """
        return TesseraTicketBatchEnricher(
            self.tessera_client,
            logger_context=self.logger_context,
            base_url=self.club.scraping_url,
        )

    async def get_data(self, url: str) -> Optional[BroadwayEventData]:
        """
        Extract Broadway event data from a webpage using standardized fetch methods.

        Returns BroadwayEvent objects extracted from Broadway's JavaScript arrays,
        enriched with ticket data from Tessera API.
        """
        try:
            # Use BaseScraper's standardized fetch_html with built-in error handling
            normalized_url = URLUtils.normalize_url(url)
            Logger.info(f"Processing URL: {normalized_url}", self.logger_context)
            html_content = await self.fetch_html(normalized_url)

            # Parse HTML and extract Broadway events as BroadwayEvent objects
            event_list = BroadwayEventExtractor.extract_events(html_content)

            if not event_list:
                Logger.info("No events found on page", self.logger_context)
                return None

            Logger.info(f"Extracted {len(event_list)} raw events", self.logger_context)
            # Enrich events with ticket data from Tessera API
            event_list = await self._enrich_events_with_tickets(event_list)
            enriched_count = sum(1 for e in event_list if hasattr(e, "_ticket_data"))
            Logger.info(
                f"Post-enrichment: {len(event_list)} events, {enriched_count} with ticket data",
                self.logger_context,
            )
            return BroadwayEventData(event_list) if event_list else None

        except Exception as e:
            Logger.error(f"Error extracting data from {url}: {str(e)}", self.logger_context)
            return None

    async def _enrich_events_with_tickets(self, events: List[BroadwayEvent]) -> List[BroadwayEvent]:
        """
        Enrich BroadwayEvent objects with ticket data from Tessera API.

        Args:
            events: List of BroadwayEvent objects

        Returns:
            List of BroadwayEvent objects enriched with ticket data, with any Tessera
            events that returned no ticket data excluded entirely.
        """
        try:
            # 1) Select Tessera-backed event IDs
            event_ids = self._select_tessera_event_ids(events)
            if not event_ids:
                Logger.info("No Tessera events found to enrich", self.logger_context)
                return self._filter_unenriched_tessera_events(events)

            # 2) Enrich using the configured ticket enricher
            if self._tickets is None:
                # Enrichment intentionally disabled — pass events through without filtering
                # so subclasses that disable enrichment don't silently lose Tessera events.
                Logger.info("Ticket enrichment disabled for this scraper", self.logger_context)
                return events

            enriched = await self._tickets.enrich(
                events,
                lambda e: bool(getattr(e, "isTesseraProduct", False)),
                lambda e: getattr(e, "id", None),
                lambda e: (getattr(e, "show_page_url", "") or getattr(e, "externalLink", "")),
            )

            Logger.info(
                f"Successfully enriched {len([e for e in enriched if getattr(e, '_ticket_data', None)])} events with ticket data",
                self.logger_context,
            )
            return self._filter_unenriched_tessera_events(enriched)

        except Exception as e:
            Logger.error(f"Error enriching events with tickets: {str(e)}", self.logger_context)
            # Filter even on failure — any Tessera events that didn't receive data would
            # otherwise produce partial shows with fallback tickets on every subsequent run.
            return self._filter_unenriched_tessera_events(events)

    def _filter_unenriched_tessera_events(self, events: List[BroadwayEvent]) -> List[BroadwayEvent]:
        """Exclude Tessera events with no ticket data to prevent partial shows.

        Events that claim to be Tessera products but carry no _ticket_data are stale or
        unreachable — including them would result in a fallback-ticket partial show being
        saved on every subsequent scrape run.
        """
        output: List[BroadwayEvent] = []
        for event in events:
            if getattr(event, "isTesseraProduct", False) and not getattr(event, "_ticket_data", None):
                Logger.warning(
                    f"Skipping Tessera event {event.id!r} — _fetch_ticket_data returned None/empty; "
                    "event may be stale or removed from Broadway's site",
                    self.logger_context,
                )
            else:
                output.append(event)
        return output

    def _select_tessera_event_ids(self, events: List[BroadwayEvent]) -> List[str]:
        """Filter and return deduped Tessera event IDs with diagnostics logging."""
        return log_filter_breakdown(
            events,
            self.logger_context,
            id_getter=lambda e: getattr(e, "id", None),
            accept_predicate=lambda e: bool(getattr(e, "isTesseraProduct", False)),
            label="Tessera enrichment",
            name_getter=lambda e: (e.mainArtist[0] if getattr(e, "mainArtist", []) else "n/a"),
            date_getter=lambda e: getattr(e, "eventDate", "n/a"),
        )

    # Legacy batch-based ticket attachment removed; enrichment now flows through _make_ticket_enricher()

    async def close(self):
        """Clean up resources including Tessera client session."""
        # BaseScraper will call this; super().close() handles the HTTP session via AsyncHttpMixin
        try:
            await super().close()
        except Exception as e:
            Logger.error(f"Error closing HTTP session: {e}", self.logger_context)

        # Always attempt to close the Tessera client as well, independently of the HTTP session result
        try:
            client = getattr(self, "tessera_client", None)
            if client and hasattr(client, "cleanup") and callable(getattr(client, "cleanup")):
                await client.cleanup()
        except Exception as e:
            Logger.error(f"Error closing Tessera client: {e}", self.logger_context)
