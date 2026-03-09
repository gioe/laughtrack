"""
StandUp NY event extractor for GraphQL API discovery and VenuePilot enhancement.

Handles the complex multi-step workflow:
1. Analyze club.scraping_url to determine if it's GraphQL endpoint or calendar page
2. Discovery GraphQL endpoint from calendar page if needed
3. Query GraphQL endpoint for event data
4. Extract VenuePilot enhancement data for qualifying URLs
"""

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

from laughtrack.core.entities.event.standup_ny import StandupNYEvent
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.foundation.models.types import JSONDict
from laughtrack.scrapers.implementations.venues.standup_ny.data import StandupNYPageData
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.url import URLUtils


class StandupNYEventExtractor:
    """
    Handles GraphQL discovery and event data extraction for StandUp NY.

    This extractor manages the complex workflow of:
    - GraphQL endpoint discovery from calendar pages
    - Direct GraphQL endpoint usage
    - Event data extraction from GraphQL responses
    - VenuePilot URL identification and enhancement
    """

    def __init__(self, logger_context: Dict[str, Any]):
        self.logger_context = logger_context

        # GraphQL headers for API requests
        self.graphql_headers = BaseHeaders.get_headers(
            base_type="graphql", domain="https://standupny.com", referer="https://standupny.com/"
        )
        # Add additional headers
        self.graphql_headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                "Sec-Fetch-Site": "cross-site",
                "accept": "*/*",
            }
        )

    async def extract_events(self, session, club_url: str) -> Optional[StandupNYPageData]:
        """
        Extract events from StandUp NY using GraphQL discovery workflow.

        Args:
            session: HTTP session for requests
            club_url: The club.scraping_url to analyze

        Returns:
            StandupNYPageData with extracted events or None if extraction failed
        """
        try:
            # Step 1: Determine target GraphQL endpoint
            graphql_endpoint = await self._discover_graphql_endpoint(session, club_url)
            if not graphql_endpoint:
                return None

            # Step 2: Query GraphQL endpoint
            events_data = await self._query_graphql_endpoint(session, graphql_endpoint)
            if not events_data:
                return None

            # Step 3: Convert to StandupNYEvent objects
            events = self._convert_graphql_to_events(events_data, graphql_endpoint)

            # Step 4: Create page data with metadata
            page_data = StandupNYPageData(
                event_list=events
            )

            Logger.info(f"Extracted {len(events)} events from GraphQL endpoint {graphql_endpoint}", self.logger_context)

            return page_data

        except Exception as e:
            Logger.error(f"Error extracting events: {e}", self.logger_context)
            return None

    async def enhance_event_with_venue_pilot(self, session, event: StandupNYEvent) -> bool:
        """
        Enhance an event with VenuePilot ticket data.

        Args:
            session: HTTP session for requests
            event: Event to enhance with VenuePilot data

        Returns:
            True if enhancement was successful, False otherwise
        """
        if not event.ticket_url or "venuepilot" not in event.ticket_url.lower():
            return False

        try:
            html_content = await HttpClient.fetch_html(
                session, event.ticket_url, logger_context=self.logger_context
            )
            if not html_content:
                return False

            venue_pilot_data = self._extract_venue_pilot_data(html_content, event.ticket_url)

            if venue_pilot_data:
                event.add_venue_pilot_data(venue_pilot_data)
                return True

            return False

        except Exception as e:
            Logger.error(f"Error enhancing event {event.id} with VenuePilot data: {e}", self.logger_context)
            return False

    async def _discover_graphql_endpoint(self, session, club_url: str) -> Optional[str]:
        """
        Discover the GraphQL endpoint from club.scraping_url.

        Args:
            session: HTTP session
            club_url: The club.scraping_url to analyze

        Returns:
            GraphQL endpoint URL or None if discovery failed
        """
        try:
            # Check if URL is already a GraphQL endpoint
            if "graphql" in club_url.lower():
                Logger.info(f"Direct GraphQL endpoint detected: {club_url}", self.logger_context)
                return URLUtils.normalize_url(club_url)

            # Calendar page - discover GraphQL endpoint
            Logger.info(f"Discovering GraphQL endpoint from calendar page: {club_url}", self.logger_context)

            html_content = await HttpClient.fetch_html(
                session, club_url, logger_context=self.logger_context
            )
            if not html_content:
                Logger.error("Failed to access calendar page", self.logger_context)
                return None

            return self._extract_graphql_endpoint_from_html(html_content, club_url)

        except Exception as e:
            Logger.error(f"Error discovering GraphQL endpoint: {e}", self.logger_context)
            return None

    def _extract_graphql_endpoint_from_html(self, html_content: str, club_url: str) -> Optional[str]:
        """
        Extract GraphQL endpoint from HTML page source.

        Args:
            html_content: HTML content to search
            club_url: Original club URL for fallback logic

        Returns:
            GraphQL endpoint URL or None
        """
        soup_scripts = HtmlScraper.find_script_elements(html_content)

        # Look for GraphQL endpoint in script tags
        for script in soup_scripts:
            script_content = script.get_text() if script else None
            if script_content and "graphql" in script_content.lower():
                # Extract actual endpoint URL from JavaScript/config
                graphql_pattern = r'https?://[^"\s]+/graphql'
                matches = re.findall(graphql_pattern, script_content)
                if matches:
                    endpoint = matches[0]
                    Logger.info(f"Discovered GraphQL endpoint: {endpoint}", self.logger_context)
                    return endpoint

        # Fallback logic based on club domain
        if "standupny.com" in club_url.lower():
            fallback_endpoint = "https://api.showtix4u.com/graphql"
            Logger.warn(
                f"Could not discover GraphQL endpoint from calendar page, using ShowTix4U fallback: {fallback_endpoint}",
                self.logger_context,
            )
            return fallback_endpoint

        Logger.error(
            f"Could not discover GraphQL endpoint from {club_url} and no suitable fallback available",
            self.logger_context,
        )
        return None

    async def _query_graphql_endpoint(self, session, endpoint_url: str) -> Optional[List[Dict[str, Any]]]:
        """
        Query the GraphQL endpoint for event data.

        Args:
            session: HTTP session
            endpoint_url: GraphQL endpoint to query

        Returns:
            List of event data or None if query failed
        """
        try:
            payload = self._build_graphql_payload(endpoint_url)

            response = await session.post(endpoint_url, headers=self.graphql_headers, json=payload)
            if response.status_code != 200:
                Logger.error(
                    f"GraphQL POST request to {endpoint_url} failed with status {response.status_code}",
                    self.logger_context,
                )
                # Log response for debugging
                try:
                    Logger.error(
                        f"Response body: {response.text[:500]}...",  # First 500 chars
                        self.logger_context,
                    )
                except:
                    pass
                return None

            data = response.json()
            return data.get("data", {}).get("publicEvents", [])

        except Exception as e:
            Logger.error(f"Error querying GraphQL endpoint: {e}", self.logger_context)
            return None

    def _build_graphql_payload(self, endpoint_url: str) -> JSONDict:
        """
        Build GraphQL payload for the specific endpoint.

        Args:
            endpoint_url: GraphQL endpoint URL

        Returns:
            GraphQL payload dictionary
        """
        today = datetime.now()
        end_date = today + timedelta(days=180)

        if "showtix4u.com" in endpoint_url.lower() or "venuepilot.co" in endpoint_url.lower():
            # Both ShowTix4U and VenuePilot use the same GraphQL schema
            return {
                "operationName": None,
                "variables": {
                    "accountIds": [2535],  # StandUp NY's account ID
                    "startDate": today.strftime("%Y-%m-%d"),
                    "endDate": end_date.strftime("%Y-%m-%d"),
                    "search": "",
                    "searchScope": "",
                },
                "query": """query ($accountIds: [Int!]!, $startDate: String!, $endDate: String, $search: String, $searchScope: String, $limit: Int) {
                  publicEvents(accountIds: $accountIds, startDate: $startDate, endDate: $endDate, search: $search, searchScope: $searchScope, limit: $limit) {
                    id
                    name
                    date
                    doorTime
                    startTime
                    endTime
                    minimumAge
                    promoter
                    support
                    description
                    websiteUrl
                    twitterUrl
                    instagramUrl
                    images
                    status
                    venue {
                      name
                      __typename
                    }
                    footerContent
                    highlightedImage
                    ticketsUrl
                    __typename
                  }
                }""",
            }
        else:
            # Default to ShowTix4U/VenuePilot format for unknown endpoints
            Logger.warn(
                f"Unknown GraphQL endpoint format: {endpoint_url}, using ShowTix4U/VenuePilot format as fallback",
                self.logger_context,
            )
            return self._build_graphql_payload("https://api.showtix4u.com/graphql")

    def _convert_graphql_to_events(self, events_data: List[Dict[str, Any]], endpoint_url: str) -> List[StandupNYEvent]:
        """
        Convert GraphQL response data to StandupNYEvent objects.

        Args:
            events_data: List of event dictionaries from GraphQL
            endpoint_url: Source endpoint URL for tracking

        Returns:
            List of StandupNYEvent objects
        """
        events = []
        source = self._determine_graphql_source(endpoint_url)

        for event_data in events_data:
            # Ensure we have required fields
            if not event_data.get("name") or not event_data.get("ticketsUrl"):
                continue

            try:
                event = StandupNYEvent.from_graphql_event(event_data, source)
                events.append(event)
            except Exception as e:
                Logger.warn(f"Failed to create event from GraphQL data: {e}", self.logger_context)
                continue

        return events

    def _determine_graphql_source(self, endpoint_url: str) -> str:
        """Determine the GraphQL source type from endpoint URL."""
        if "showtix4u.com" in endpoint_url.lower():
            return "showtix4u"
        elif "venuepilot" in endpoint_url.lower():
            return "venuepilot"
        else:
            return "unknown"

    def _extract_venue_pilot_data(self, html_content: str, ticket_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract VenuePilot data from HTML page.

        Args:
            html_content: HTML content from VenuePilot page
            ticket_url: Original ticket URL

        Returns:
            Dictionary with combined data or None
        """
        try:
            # Extract JSON data from script tags with multiple fallback strategies
            json_scripts = HtmlScraper.find_script_elements(html_content, "application/json")
            pinia_data = {}

            if json_scripts:
                for script in json_scripts:
                    script_content = script.get_text() if script else None
                    if script_content:
                        try:
                            json_data = json.loads(script_content)
                            pinia_data = json_data.get("_piniaInitialState", {}).get("checkout", {})
                            if pinia_data:
                                break
                        except (json.JSONDecodeError, AttributeError):
                            continue

            # If no Pinia data found, try alternative extraction methods
            if not pinia_data:
                all_scripts = HtmlScraper.find_script_elements(html_content)
                for script in all_scripts:
                    script_content = script.get_text() if script else None
                    if script_content and "event" in script_content.lower():
                        try:
                            # Try to extract event data from inline JavaScript
                            event_data_pattern = r"(?:event|selectedEvent)\s*[:=]\s*({[^}]+})"
                            matches = re.findall(event_data_pattern, script_content, re.IGNORECASE)
                            if matches:
                                event_json = json.loads(matches[0])
                                pinia_data = {"selectedEvent": event_json}
                                break
                        except (json.JSONDecodeError, IndexError):
                            continue

            if pinia_data:
                return {"venue_pilot_data": pinia_data, "ticket_url": ticket_url}

            return None

        except Exception as e:
            Logger.error(f"Error extracting VenuePilot data: {e}", self.logger_context)
            return None
