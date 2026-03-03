"""
Comedy Cellar data extraction utilities.

This module handles data extraction and mapping from Comedy Cellar API responses.
The extractor takes raw API responses and converts them to domain models.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from laughtrack.core.entities.event.comedy_cellar import ComedyCellarEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.models.api.comedy_cellar.models import ComedyCellarLineupAPIResponse, ComedyCellarShowsAPIResponse, ShowInfoData
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.foundation.utilities.url import URLUtils


class ComedyCellarExtractor:
    """
    Utility class for extracting Comedy Cellar data from API responses.

    This extractor handles data mapping from raw API responses to domain models.
    Network requests and session management are handled by the scraper.
    """

    # Constants for Comedy Cellar room mapping
    ROOM_MAPPING = {1: "MacDougal St.", 2: "Village Underground", 3: "Fat Black Pussycat"}

    # Common selector patterns for HTML parsing
    COMEDIAN_LINK_PATTERN = "/comedians/"

    @staticmethod
    def extract_available_dates(lineup_response_text: str) -> List[str]:
        """
        Extract available dates from lineup API response.

        Args:
            lineup_response_text: Raw text response from lineup API

        Returns:
            List of date strings that can be processed
        """
        try:
            if not lineup_response_text:
                return []

            try:
                data = json.loads(lineup_response_text)
            except json.JSONDecodeError as e:
                Logger.error(f"Failed to parse JSON response: {e}")
                return []

            dates = data.get("dates", {})
            if not isinstance(dates, dict):
                Logger.warning(f"Invalid dates format in API response. Expected dict, got {type(dates)}")
                return []

            return list(dates.keys())

        except Exception as e:
            Logger.error(f"Error extracting available dates: {str(e)}")
            return []

    @staticmethod
    def extract_lineup_data(lineup_response_text: str) -> Optional[ComedyCellarLineupAPIResponse]:
        """
        Extract lineup data from lineup API response.

        This method handles the actual JSON structure returned by the Comedy Cellar lineup API,
        which includes show content, date, and available dates dictionary.

        Args:
            lineup_response_text: Raw text response from lineup API

        Returns:
            Parsed lineup data as dataclass, or None if extraction failed
        """
        try:
            if not lineup_response_text:
                Logger.warning("Empty lineup response text provided")
                return None

            try:
                response_data = json.loads(lineup_response_text)
            except json.JSONDecodeError as e:
                Logger.error(f"Failed to parse lineup JSON response: {e}")
                return None

            # Validate response structure
            if not isinstance(response_data, dict):
                Logger.warning(f"Invalid lineup response format. Expected dict, got {type(response_data)}")
                return None

            if "show" not in response_data:
                Logger.warning("Missing 'show' key in lineup response")
                return None

            # Convert dict to dataclass instance using from_dict()
            return ComedyCellarLineupAPIResponse.from_dict(response_data)

        except Exception as e:
            Logger.error(f"Unexpected error extracting lineup data: {str(e)}")
            return None

    @staticmethod
    def extract_shows_data(shows_response_data: dict) -> Optional[ComedyCellarShowsAPIResponse]:
        """
        Extract shows data from shows API response.

        Args:
            shows_response_data: Parsed JSON response from shows API

        Returns:
            Shows data as dataclass, or None if extraction failed
        """
        if not shows_response_data:
            Logger.warning("Empty shows response data provided")
            return None

        if not isinstance(shows_response_data, dict):
            Logger.warning(f"Invalid shows response format. Expected dict, got {type(shows_response_data)}")
            return None

        # Validate required structure
        if "data" not in shows_response_data:
            Logger.warning("Missing 'data' key in shows response")
            return None

        try:
            # Convert nested dicts to dataclass instances using from_dict()
            return ComedyCellarShowsAPIResponse.from_dict(shows_response_data)

        except Exception as e:
            Logger.error(f"Error converting shows data to dataclass: {str(e)}")
            return None

    @staticmethod
    def extract_events(
        date_key: Optional[str],
        lineup_data: ComedyCellarLineupAPIResponse,
        shows_data: ComedyCellarShowsAPIResponse,
    ) -> List[ComedyCellarEvent]:
        """
        Combine lineup and shows data into a unified list of ComedyCellarEvent objects.

        Args:
            date_key: Optional date string for the data (YYYY-MM-DD). If not provided,
                the value will be derived from the API responses. If provided and it
                differs from the API value, the API value will be preferred.
            lineup_data: Validated lineup data (guaranteed non-null)
            shows_data: Validated shows data (guaranteed non-null)

        Returns:
            List of events. Empty list if combination fails
        """
        # Resolve authoritative date key from APIs
        api_date = None
        try:
            api_date = shows_data.data.showInfo.date or None
        except Exception:
            api_date = None

        if not api_date:
            try:
                api_date = lineup_data.date or None
            except Exception:
                api_date = None

        # Prefer API-provided date; warn if a different external date was passed
        if date_key and api_date and date_key != api_date:
            Logger.warning(
                f"Provided date_key ({date_key}) differs from API date ({api_date}); using API date"
            )

        resolved_date = api_date or date_key
        if not resolved_date:
            Logger.error("Unable to resolve date for combining data")
            return []

        # Create ComedyCellarEvent objects from the API data
        try:
            # Extract and validate HTML content
            html = lineup_data.show.html
            if not html:
                Logger.warning(f"No HTML content found in lineup data for {resolved_date}")
                return []

            # Build an index of lineup info keyed by show_id
            lineup_index = ComedyCellarExtractor._build_lineup_index(html, resolved_date)
            if not lineup_index:
                return []

            # Create ticket lookup dictionary
            ticket_dict = ComedyCellarExtractor._create_ticket_lookup(shows_data, resolved_date)

            # Join on show_id and create events
            events: List[ComedyCellarEvent] = []
            missing_ticket_ids = []
            for show_id, li in lineup_index.items():
                ticket_data = ticket_dict.get(show_id)
                if not ticket_data:
                    missing_ticket_ids.append(show_id)
                    continue

                api_data = ComedyCellarExtractor._extract_api_data(ticket_data, resolved_date)
                if not api_data:
                    continue

                room_name = ComedyCellarExtractor._get_room_name(api_data.get("room_id"))

                events.append(
                    ComedyCellarEvent(
                        show_id=show_id,
                        date_key=resolved_date,
                        api_time=api_data["api_time"],
                        show_name=api_data["show_name"],
                        description=api_data["description"],
                        note=api_data["note"],
                        room_id=api_data["room_id"],
                        room_name=room_name,
                        timestamp=api_data["timestamp"],
                        ticket_link=li["ticket_link"],
                        ticket_data=ticket_data,
                        html_container=li["html_container"],
                        lineup_names=li["lineup_names"],
                    )
                )

            if missing_ticket_ids:
                Logger.debug(
                    f"No ticket data for {len(missing_ticket_ids)} lineup shows on {resolved_date}: {sorted(missing_ticket_ids)}"
                )

            return events

        except Exception as e:
            Logger.error(f"Unexpected error creating events from API data for {resolved_date}: {str(e)}")
            return []

    @staticmethod
    def _build_lineup_index(html: str, date_key: str) -> Dict[int, Dict[str, Any]]:
        """
        Build an index of lineup information keyed by show ID.

        Returns:
            Dict of show_id -> { ticket_link, lineup_names, html_container }
        """
        show_containers = ComedyCellarExtractor._extract_show_containers(html, date_key)
        if not show_containers:
            return {}

        index: Dict[int, Dict[str, Any]] = {}
        for container in show_containers:
            show_id_int, ticket_link = ComedyCellarExtractor._extract_show_id_and_link(container, date_key)
            if not show_id_int or not ticket_link:
                continue
            lineup_names = ComedyCellarExtractor._extract_lineup_names(container)
            index[show_id_int] = {
                "ticket_link": ticket_link,
                "lineup_names": lineup_names,
                "html_container": str(container),
            }

        if not index:
            Logger.warning(f"No valid lineup entries found for {date_key}")
        else:
            Logger.debug(f"Built lineup index with {len(index)} entries for {date_key}")

        return index

    @staticmethod
    def _extract_show_containers(html: str, date_key: str) -> List[Any]:
        """
        Extract show containers from HTML content.

        Args:
            html: HTML content from lineup API
            date_key: Date key for logging context

        Returns:
            List of container elements representing show containers
        """
        try:
            show_containers = HtmlScraper.find_parent_containers_by_child_class(html, "div", "set-header")

            if not show_containers:
                Logger.warning(f"No valid show containers found for {date_key}")

            return show_containers

        except Exception as e:
            Logger.error(f"Error parsing HTML for {date_key}: {str(e)}")
            return []

    @staticmethod
    def _create_ticket_lookup(shows_data: ComedyCellarShowsAPIResponse, date_key: str) -> Dict[int, ShowInfoData]:
        """
        Create a lookup dictionary for ticket data by show ID.

        Args:
            shows_data: Shows API response data
            date_key: Date key for logging context

        Returns:
            Dictionary mapping show identifiers to ticket data. Keys include both the
            numeric show.id and the numeric show.timestamp (when present), since the
            lineup "showid" link parameter can be either depending on the site.
        """
        try:
            show_ticket_list = shows_data.data.showInfo.shows

            if not isinstance(show_ticket_list, list):
                Logger.warning(f"Invalid shows data format for {date_key}. Expected list, got {type(show_ticket_list)}")
                return {}

            if not show_ticket_list:
                Logger.warning(f"Empty shows list for {date_key}")
                return {}

            # Create lookup by show ID and timestamp (fallback key)
            ticket_dict: Dict[int, ShowInfoData] = {}
            added_keys = 0
            for show in show_ticket_list:
                try:
                    # Primary key: API show.id
                    if isinstance(show.id, int) and show.id not in ticket_dict:
                        ticket_dict[show.id] = show
                        added_keys += 1

                    # Fallback key: API show.timestamp (some lineup links use this in showid param)
                    if isinstance(show.timestamp, int) and show.timestamp and show.timestamp not in ticket_dict:
                        ticket_dict[show.timestamp] = show
                        added_keys += 1
                except Exception:
                    continue

            Logger.debug(
                f"Created ticket lookup with {len(show_ticket_list)} shows and {added_keys} keys for {date_key}"
            )
            return ticket_dict

        except Exception as e:
            Logger.error(f"Error creating ticket lookup for {date_key}: {str(e)}")
            return {}

    @staticmethod
    def _extract_show_id_and_link(container: Any, date_key: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Extract show ID and ticket link from container.

        Args:
            container: HTML container element
            date_key: Date key for logging context

        Returns:
            Tuple of (show_id, ticket_link) or (None, None) if extraction failed
        """
        try:
            ticket_link = HtmlScraper.extract_nested_link_href(container, "make-reservation")
            if not ticket_link:
                Logger.debug(f"No ticket link found in show container for {date_key}")
                return None, None

            show_id = URLUtils.extract_query_param(ticket_link, "showid")

            if not show_id:
                Logger.warning(f"Could not extract show ID from link: {ticket_link}")
                return None, None

            try:
                show_id_int = int(show_id)
                return show_id_int, ticket_link
            except ValueError:
                Logger.warning(f"Invalid show ID format: {show_id}")
                return None, None

        except Exception as e:
            Logger.error(f"Error extracting show ID and link for {date_key}: {str(e)}")
            return None, None

    @staticmethod
    def _extract_api_data(ticket_data: ShowInfoData, date_key: str) -> Optional[Dict[str, Any]]:
        """
        Extract and validate API data from ticket information.

        Args:
            ticket_data: Ticket data from shows API
            date_key: Date key for logging context

        Returns:
            Dictionary of extracted API data or None if validation failed
        """
        try:
            api_time = ticket_data.time
            if not api_time:
                Logger.warning(f"No time found in API data for show on {date_key}")
                return None

            return {
                "api_time": api_time,
                "show_name": ticket_data.description or "Comedy Show",
                "description": ticket_data.description,
                "note": ticket_data.note,
                "room_id": ticket_data.roomId,
                "timestamp": ticket_data.timestamp or 0,
            }

        except Exception as e:
            Logger.error(f"Error extracting API data for {date_key}: {str(e)}")
            return None

    @staticmethod
    def _get_room_name(room_id: Optional[int]) -> Optional[str]:
        """
        Get human-readable room name from room ID.

        Args:
            room_id: Numeric room identifier

        Returns:
            Room name string or None if no mapping found
        """
        if room_id is not None and isinstance(room_id, int):
            return ComedyCellarExtractor.ROOM_MAPPING.get(room_id, f"Room {room_id}")
        return None

    @staticmethod
    def _extract_lineup_names(container: Any) -> List[str]:
        """
        Extract comedian names from HTML container.

        Args:
            container: Container element containing show HTML

        Returns:
            List of comedian names found in comedian links
        """
        try:
            # First, get visible link texts for comedian profile links
            names = HtmlScraper.extract_text_from_links_by_href_pattern(
                container, ComedyCellarExtractor.COMEDIAN_LINK_PATTERN
            )

            # Also consider <img alt="Name"> inside those links; sometimes names are only in alt text
            try:
                link_selector = lambda href: bool(href and ComedyCellarExtractor.COMEDIAN_LINK_PATTERN in href)
                if hasattr(container, "find_all"):
                    links = container.find_all("a", href=link_selector)  # type: ignore[attr-defined]
                    for link in links:
                        try:
                            imgs = link.find_all("img") if hasattr(link, "find_all") else []
                        except Exception:
                            imgs = []
                        for img in imgs:
                            try:
                                alt = img.get("alt") if hasattr(img, "get") else None
                                alt_text = str(alt).strip() if alt else ""
                                if alt_text and alt_text not in names:
                                    names.append(alt_text)
                            except Exception:
                                continue
            except Exception:
                # Fallback silently; we'll just return the link texts we found
                pass

            Logger.debug(f"Extracted {len(names)} comedian names from container (including alt text)")
            return names

        except Exception as e:
            Logger.error(f"Error extracting lineup names: {str(e)}")
            return []
