"""
GraphQL request utilities for scrapers.

This module provides standardized GraphQL request handling with proper
error handling, response parsing, and integration with existing infrastructure.
"""

import json
from typing import Any, Dict, Optional

import aiohttp

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.infrastructure.http.base_headers import BaseHeaders
from laughtrack.foundation.infrastructure.logger.logger import Logger


class GraphQLClient:
    """
    Standardized GraphQL client for scrapers.

    Features:
    - Automatic request/response handling
    - Error parsing and logging
    - Header management
    - Variable substitution
    - Response validation
    """

    def __init__(self, endpoint_url: str, default_headers: Optional[Dict[str, str]] = None):
        """
        Initialize GraphQL client.

        Args:
            endpoint_url: GraphQL endpoint URL
            default_headers: Optional default headers to use
        """
        self.endpoint_url = endpoint_url
        self.default_headers = default_headers or BaseHeaders.get_headers(base_type="graphql")

    async def execute_query(
        self,
        session: aiohttp.ClientSession,
        query: str,
        variables: Optional[JSONDict] = None,
        operation_name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> JSONDict:
        """
        Execute a GraphQL query.

        Args:
            session: aiohttp session to use
            query: GraphQL query string
            variables: Optional query variables
            operation_name: Optional operation name
            headers: Optional custom headers

        Returns:
            GraphQL response data

        Raises:
            Exception: If request fails or GraphQL errors occur
        """
        payload = {
            "query": query,
            "variables": variables or {},
        }

        if operation_name:
            payload["operationName"] = operation_name

        request_headers = self._build_headers(headers)

        try:
            async with session.post(self.endpoint_url, json=payload, headers=request_headers) as response:
                response.raise_for_status()
                result = await response.json()

                # Check for GraphQL errors
                if "errors" in result:
                    errors = result["errors"]
                    error_msg = f"GraphQL errors: {errors}"
                    Logger.error(error_msg)
                    raise Exception(error_msg)

                return result.get("data", {})

        except aiohttp.ClientError as e:
            Logger.error(f"GraphQL request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            Logger.error(f"Failed to parse GraphQL response: {e}")
            raise

    def _build_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build request headers."""
        headers = self.default_headers.copy()
        if custom_headers:
            headers.update(custom_headers)
        return headers


class GraphQLQueryBuilder:
    """
    Builder for common GraphQL query patterns in comedy venue scrapers.
    """

    @staticmethod
    def build_events_query(
        account_id: str, date_from: Optional[str] = None, date_to: Optional[str] = None, limit: Optional[int] = None
    ) -> tuple[str, JSONDict]:
        """
        Build a common events query pattern.

        Args:
            account_id: Account ID for the venue
            date_from: Optional start date filter
            date_to: Optional end date filter
            limit: Optional result limit

        Returns:
            Tuple of (query_string, variables)
        """
        query = """
        query GetPublicEvents($accountId: String!, $fromDate: String, $toDate: String, $limit: Int) {
            publicEvents(accountId: $accountId, fromDate: $fromDate, toDate: $toDate, limit: $limit) {
                id
                name
                description
                startDate
                endDate
                ticketUrl
                imageUrl
                location {
                    name
                    address
                }
                tickets {
                    id
                    name
                    price
                    currency
                    soldOut
                    url
                }
                performers {
                    id
                    name
                    role
                }
            }
        }
        """

        variables = {"accountId": account_id, "fromDate": date_from, "toDate": date_to, "limit": limit}

        # Remove None values
        variables = {k: v for k, v in variables.items() if v is not None}

        return query, variables

    @staticmethod
    def build_event_details_query(event_id: str) -> tuple[str, JSONDict]:
        """
        Build a query for detailed event information.

        Args:
            event_id: Event ID to fetch details for

        Returns:
            Tuple of (query_string, variables)
        """
        query = """
        query GetEventDetails($eventId: String!) {
            event(id: $eventId) {
                id
                name
                description
                startDate
                endDate
                duration
                ticketUrl
                imageUrl
                status
                location {
                    name
                    address
                    city
                    state
                    zipCode
                }
                tickets {
                    id
                    name
                    description
                    price
                    currency
                    soldOut
                    url
                    available
                    total
                }
                performers {
                    id
                    name
                    role
                    bio
                    imageUrl
                }
                tags
                categories
            }
        }
        """

        variables = {"eventId": event_id}

        return query, variables
