"""
Gotham Comedy Club data extraction utilities.

This module provides extraction logic for Gotham Comedy Club's S3 bucket-based
event system that provides JSON API endpoints with monthly event data.
"""

from typing import List, Optional

from laughtrack.core.clients.gotham.models.models import GothamMonthlyResponse
from laughtrack.core.clients.showclix.client import ShowclixAPIClient
from laughtrack.core.entities.event.gotham import GothamEvent
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.utilities.infrastructure.scraper import log_filter_breakdown
from laughtrack.utilities.infrastructure.scraper.config import BatchScrapingConfig
from laughtrack.utilities.infrastructure.scraper.scraper import BatchScraper


from .data import GothamPageData

_SHOWCLIX_BATCH_CONFIG = BatchScrapingConfig(
    max_concurrent=5,
    delay_between_requests=0,
    enable_logging=True,
)


class GothamEventExtractor:
    """
    Extractor for Gotham Comedy Club event data from S3 JSON endpoints.

    Handles:
    - Monthly JSON file fetching from S3 bucket
    - Event data extraction and typing
    - Showclix ticket data enrichment
    """

    def __init__(self, club, http_session_getter, proxy_pool: Optional[ProxyPool] = None):
        """
        Initialize the extractor.

        Args:
            club: Club entity with configuration
            http_session_getter: Async function to get HTTP session
            proxy_pool: Optional ProxyPool forwarded to Showclix client.
        """
        self.club = club
        self.get_session = http_session_getter
        self.showclix_client = ShowclixAPIClient(club, proxy_pool=proxy_pool)
        self.logger_context = club.as_context()
        self.batch_scraper = BatchScraper(self.logger_context, config=_SHOWCLIX_BATCH_CONFIG)

    def get_headers(self) -> dict:
        """Get headers optimized for S3 CORS requests."""
        return BaseHeaders.get_venue_headers(
            venue_type="gotham",
            domain="https://www.gothamcomedyclub.com",
            **{
                "Sec-Fetch-Site": "cross-site",  # Override for S3
                "Accept": "application/json,*/*",  # JSON preference
            },
        )

    async def extract_events(self, monthly_url: str) -> Optional[GothamPageData]:
        """
        Extract events from a monthly S3 JSON endpoint.

        Args:
            monthly_url: URL to monthly JSON file (e.g., .../2025-07.json)

        Returns:
            GothamPageData with extracted events or None if failed
        """
        try:
            session = await self.get_session()

            # Fetch JSON with appropriate headers
            response = await session.get(monthly_url, headers=self.get_headers())
            if response.status_code == 404 or response.status_code == 403:
                # Future months may not have files yet - this is normal
                Logger.info(
                    f"Monthly file {monthly_url} not available (status {response.status_code})", self.logger_context
                )
                return None

            response.raise_for_status()
            json_content = response.json()

            # Convert to typed monthly response
            monthly_response = GothamMonthlyResponse.from_dict(json_content)

            # Get flattened event list
            event_list = monthly_response.flatten_events()

            # Enrich with ticket data
            enriched_events = await self._enrich_events_with_tickets(event_list)

            Logger.info(
                f"GothamEventExtractor [{self.club.name}]: Extracted {len(enriched_events)} events from {monthly_url} ({len(monthly_response.days)} days)",
                self.logger_context,
            )

            return GothamPageData(event_list=enriched_events) if enriched_events else None

        except Exception as e:
            Logger.warn(f"GothamEventExtractor [{self.club.name}]: Error extracting events from {monthly_url}: {e}", self.logger_context)
            return None

    async def _enrich_events_with_tickets(self, events: List[GothamEvent]) -> List[GothamEvent]:
        """
        Enrich GothamEvent objects with ticket data from Showclix API.

        Args:
            events: List of GothamEvent objects

        Returns:
            List of GothamEvent objects enriched with ticket data
        """
        if not events:
            Logger.info(f"GothamEventExtractor [{self.club.name}]: No events to enrich", self.logger_context)
            return events

        try:
            Logger.info(f"GothamEventExtractor [{self.club.name}]: Enriching {len(events)} events with Showclix ticket data", self.logger_context)

            # Log a standardized breakdown of which events have usable slugs for Showclix fetches
            _ = log_filter_breakdown(
                events,
                self.logger_context,
                id_getter=lambda e: getattr(e, "slug", None),
                accept_predicate=lambda e: bool(getattr(e, "slug", None)),
                label="Showclix HTML fetch",
                name_getter=lambda e: getattr(e, "name", "n/a"),
                date_getter=lambda e: getattr(e, "date", "n/a"),
            )

            # Separate events with and without slugs
            events_with_slugs = [e for e in events if e.slug]
            events_without_slugs = [e for e in events if not e.slug]

            for event in events_without_slugs:
                Logger.warn(f"GothamEventExtractor [{self.club.name}]: Event missing slug, skipping: {event}", self.logger_context)

            if not events_with_slugs:
                Logger.info(f"GothamEventExtractor [{self.club.name}]: No events with valid slugs found", self.logger_context)
                return events

            # Build slug→event lookup for the processor
            events_by_slug = {e.slug: e for e in events_with_slugs}
            enriched_events: List[GothamEvent] = []

            async def _enrich_event(slug: str) -> GothamEvent:
                event = events_by_slug[slug]
                try:
                    html_content = await self.showclix_client.get_web_page_for_event(slug)

                    if not html_content or not isinstance(html_content, str):
                        Logger.warn(f"GothamEventExtractor [{self.club.name}]: No HTML content received for event {slug}", self.logger_context)
                        return event

                    Logger.info(
                        f"GothamEventExtractor [{self.club.name}]: Successfully fetched HTML for event {slug} ({len(html_content)} chars)",
                        self.logger_context,
                    )

                    event_id = self._extract_event_id_from_html(html_content)
                    if not event_id:
                        Logger.warn(f"GothamEventExtractor [{self.club.name}]: Could not extract event_id from HTML for event {slug}", self.logger_context)
                        return event

                    Logger.info(f"GothamEventExtractor [{self.club.name}]: Extracted event_id '{event_id}' for event {slug}", self.logger_context)

                    event_data = await self.showclix_client.get_event_data(event_id)
                    if not event_data:
                        Logger.warn(
                            f"GothamEventExtractor [{self.club.name}]: Failed to fetch Showclix event data for event_id {event_id}", self.logger_context
                        )
                        return event

                    Logger.info(
                        f"GothamEventExtractor [{self.club.name}]: Successfully fetched Showclix event data for {slug} - "
                        f"Name: {event_data.event}, Venue: {event_data.venue.venue_name}, "
                        f"Primary Price: ${event_data.get_primary_price()}, "
                        f"Available Tickets: {event_data.get_available_tickets()}",
                        self.logger_context,
                    )

                    return event.enrich_with_showclix_data(event_data)
                except Exception as e:
                    Logger.error(
                        f"GothamEventExtractor [{self.club.name}]: Error enriching event {slug}: {e}", self.logger_context
                    )
                    return event

            slugs = [e.slug for e in events_with_slugs]
            enriched_events = await self.batch_scraper.process_batch(
                slugs, _enrich_event, description="Showclix enrichment"
            )

            # Add events without slugs (unenriched)
            enriched_events.extend(events_without_slugs)

            Logger.info(f"GothamEventExtractor [{self.club.name}]: Successfully processed {len(enriched_events)} events", self.logger_context)
            return enriched_events

        except Exception as e:
            Logger.error(f"GothamEventExtractor [{self.club.name}]: Error enriching events with tickets: {str(e)}", self.logger_context)
            return events

    def _extract_event_id_from_html(self, html_content: str) -> Optional[str]:
        """
        Extract event_id from Showclix HTML content.

        Looks for JavaScript variable assignment like:
        var EVENT = {"event_id":"10081681", ...};

        Args:
            html_content: HTML content from Showclix event page

        Returns:
            event_id string if found, None otherwise
        """
        try:
            event_data = JSONUtils.extract_json_variable(html_content, "EVENT")

            if event_data is None:
                Logger.warn(f"GothamEventExtractor [{self.club.name}]: No EVENT variable found in HTML", self.logger_context)
                return None

            if isinstance(event_data, dict):
                event_id = event_data.get("event_id")
                if event_id:
                    return str(event_id)
                else:
                    Logger.warn(f"GothamEventExtractor [{self.club.name}]: event_id not found in EVENT object", self.logger_context)
            else:
                Logger.warn(f"GothamEventExtractor [{self.club.name}]: Could not parse EVENT variable as valid JSON", self.logger_context)

        except Exception as e:
            Logger.error(f"GothamEventExtractor [{self.club.name}]: Error extracting event_id from HTML: {e}", self.logger_context)

        return None
