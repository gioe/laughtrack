"""
Gotham Comedy Club data extraction utilities.

This module provides extraction logic for Gotham Comedy Club's S3 bucket-based
event system that provides JSON API endpoints with monthly event data.
"""

import asyncio
from typing import List, Optional

from laughtrack.core.clients.gotham.models.models import GothamMonthlyResponse
from laughtrack.core.clients.showclix.client import ShowclixAPIClient
from laughtrack.core.entities.event.gotham import GothamEvent
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.utilities.infrastructure.scraper import log_filter_breakdown


from .data import GothamPageData


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
                f"Extracted {len(enriched_events)} events from {monthly_url} " f"({len(monthly_response.days)} days)",
                self.logger_context,
            )

            return GothamPageData(event_list=enriched_events) if enriched_events else None

        except Exception as e:
            Logger.warn(f"Error extracting events from {monthly_url}: {e}", self.logger_context)
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
            Logger.info("No events to enrich", self.logger_context)
            return events

        try:
            Logger.info(f"Enriching {len(events)} events with Showclix ticket data", self.logger_context)

            # Log a standardized breakdown of which events have usable slugs for Showclix fetches
            # We keep behavior unchanged; this is purely diagnostic.
            _ = log_filter_breakdown(
                events,
                self.logger_context,
                id_getter=lambda e: getattr(e, "slug", None),
                accept_predicate=lambda e: bool(getattr(e, "slug", None)),
                label="Showclix HTML fetch",
                name_getter=lambda e: getattr(e, "name", "n/a"),
                date_getter=lambda e: getattr(e, "date", "n/a"),
            )

            # Create parallel fetch tasks for events with valid slugs
            fetch_tasks = []
            for event in events:
                if event.slug:
                    task = self.showclix_client.get_web_page_for_event(event.slug)
                    fetch_tasks.append((event, task))
                else:
                    Logger.warn(f"Event missing slug, skipping: {event}", self.logger_context)

            if not fetch_tasks:
                Logger.info("No events with valid slugs found", self.logger_context)
                return events

            # Execute fetch operations in parallel
            Logger.info(f"Fetching HTML for {len(fetch_tasks)} events in parallel", self.logger_context)

            tasks = [task for _, task in fetch_tasks]
            html_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and enrich events
            enriched_events: List[GothamEvent] = []
            for i, (event, _) in enumerate(fetch_tasks):
                html_content = html_results[i]

                if isinstance(html_content, Exception):
                    Logger.warn(f"Failed to fetch HTML for event {event.slug}: {html_content}", self.logger_context)
                    enriched_events.append(event)
                elif html_content and isinstance(html_content, str):
                    Logger.info(
                        f"Successfully fetched HTML for event {event.slug} ({len(html_content)} chars)",
                        self.logger_context,
                    )

                    # Extract event_id and enrich
                    event_id = self._extract_event_id_from_html(html_content)
                    if event_id:
                        Logger.info(f"Extracted event_id '{event_id}' for event {event.slug}", self.logger_context)

                        try:
                            event_data = await self.showclix_client.get_event_data(event_id)
                            if event_data:
                                Logger.info(
                                    f"Successfully fetched Showclix event data for {event.slug} - "
                                    f"Name: {event_data.event}, Venue: {event_data.venue.venue_name}, "
                                    f"Primary Price: ${event_data.get_primary_price()}, "
                                    f"Available Tickets: {event_data.get_available_tickets()}",
                                    self.logger_context,
                                )

                                enriched_event = event.enrich_with_showclix_data(event_data)
                                enriched_events.append(enriched_event)
                            else:
                                Logger.warn(
                                    f"Failed to fetch Showclix event data for event_id {event_id}", self.logger_context
                                )
                                enriched_events.append(event)
                        except Exception as api_error:
                            Logger.error(
                                f"Error fetching Showclix event data for {event_id}: {api_error}", self.logger_context
                            )
                            enriched_events.append(event)
                    else:
                        Logger.warn(f"Could not extract event_id from HTML for event {event.slug}", self.logger_context)
                        enriched_events.append(event)
                else:
                    Logger.warn(f"No HTML content received for event {event.slug}", self.logger_context)
                    enriched_events.append(event)

            # Add any events that were skipped due to missing slugs
            for event in events:
                if not event.slug:
                    enriched_events.append(event)

            Logger.info(f"Successfully processed {len(enriched_events)} events", self.logger_context)
            return enriched_events

        except Exception as e:
            Logger.error(f"Error enriching events with tickets: {str(e)}", self.logger_context)
            return events

    def _extract_event_id_from_html(self, html_content: str) -> Optional[str]:
        """
        Extract event_id from Showclix HTML content.

        Looks for JavaScript variable assignment like:
        var EVENT = {"event_id":"10081681", ...};

        Uses json.JSONDecoder.raw_decode() to extract the full JSON object
        starting at the opening brace, so semicolons and curly braces inside
        string values (e.g. HTML entities, formatted text) do not truncate
        the match.

        Args:
            html_content: HTML content from Showclix event page

        Returns:
            event_id string if found, None otherwise
        """
        import json as _json

        try:
            # Find the EVENT variable assignment — locate the opening brace
            marker = "var EVENT = {"
            idx = html_content.find(marker)
            if idx == -1:
                Logger.warn("No EVENT variable found in HTML", self.logger_context)
                return None

            start = idx + len(marker) - 1  # position of the opening '{'

            # raw_decode parses from 'start' and returns (obj, end_index),
            # correctly handling any JSON-legal content inside string values.
            decoder = _json.JSONDecoder()
            event_data, _ = decoder.raw_decode(html_content, start)

            if isinstance(event_data, dict):
                event_id = event_data.get("event_id")
                if event_id:
                    return str(event_id)
                else:
                    Logger.warn("event_id not found in EVENT object", self.logger_context)
            else:
                Logger.warn("Could not parse EVENT variable as valid JSON", self.logger_context)

        except Exception as e:
            Logger.error(f"Error extracting event_id from HTML: {e}", self.logger_context)

        return None
