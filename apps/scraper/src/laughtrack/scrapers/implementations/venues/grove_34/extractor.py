"""Grove34 data extraction utilities."""

import json
from typing import List, Optional

from laughtrack.core.entities.event.grove34 import Grove34Event
from laughtrack.foundation.models.types import JSONDict
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger


class Grove34EventExtractor:
    """Utility class for extracting Grove34 event data from Wix warmup data."""

    @staticmethod
    def extract_events(html_content: str) -> List[Grove34Event]:
        """
        Extract Grove34 events from Wix warmup data script tag.

        Args:
            html_content: HTML content containing the warmup data

        Returns:
            List of Grove34Event objects extracted from Wix warmup data
        """
        try:
            # Extract warmup events from HTML
            warmup_events = Grove34EventExtractor._extract_warmup_events(html_content)

            # Convert raw events to Grove34Event objects
            grove34_events = []
            for event_data in warmup_events:
                event = Grove34EventExtractor._convert_to_grove34_event(event_data)
                if event:
                    grove34_events.append(event)

            return grove34_events

        except Exception as e:
            Logger.error(f"Error extracting Grove34 events: {e}")
            return []

    @staticmethod
    def _extract_warmup_events(html_content: str) -> List[JSONDict]:
        """
        Extract events from Wix warmup data script tag.

        Args:
            html_content: HTML content containing the warmup data

        Returns:
            List of raw event dictionaries from warmup data
        """
        try:
            # Find the warmup data script tag
            script_elements = HtmlScraper.find_elements(
                html_content, "script", type="application/json", id="wix-warmup-data"
            )
            if not script_elements:
                Logger.warning("Warmup data script tag not found")
                return []

            warmup_script = script_elements[0]

            # Get script content
            script_content = warmup_script.get_text()

            if not script_content:
                Logger.error("Warmup script tag is empty or missing string content")
                return []

            # Parse JSON content
            try:
                warmup_data = json.loads(script_content)
            except json.JSONDecodeError as e:
                Logger.error(f"Failed to parse warmup data JSON: {e}")
                return []

            # Navigate to events data in nested structure
            apps_data = warmup_data.get("appsWarmupData", {})

            # Find the events widget - the key appears to be a UUID
            events_data = []
            for app_key, app_data in apps_data.items():
                if isinstance(app_data, dict):
                    for widget_key, widget_data in app_data.items():
                        if isinstance(widget_data, dict) and "events" in widget_data:
                            events = widget_data["events"].get("events", [])
                            if events:
                                events_data.extend(events)

            Logger.info(f"Found {len(events_data)} events in warmup data")
            return events_data

        except Exception as e:
            Logger.error(f"Error extracting warmup events: {e}")
            return []

    @staticmethod
    def _convert_to_grove34_event(event_data: JSONDict) -> Optional[Grove34Event]:
        """
        Convert raw warmup event data to Grove34Event object.

        Args:
            event_data: Raw event dictionary from warmup data

        Returns:
            Grove34Event object or None if conversion fails
        """
        try:
            # Extract required fields
            event_id = event_data.get("id")
            title = event_data.get("title", "").strip()
            slug = event_data.get("slug", "")
            description = event_data.get("description", "")

            if not title or not event_id:
                Logger.warning(f"Event missing required fields: id={event_id}, title='{title}'")
                return None

            # Extract scheduling information
            scheduling = event_data.get("scheduling", {})
            config = scheduling.get("config", {})

            start_date = config.get("startDate")
            timezone_id = config.get("timeZoneId", "America/New_York")

            if not start_date:
                Logger.warning(f"Event {event_id} missing start date")
                return None

            # Extract location information
            location = event_data.get("location", {})
            location_name = location.get("name", "")

            # Extract ticketing information
            registration = event_data.get("registration", {})
            ticketing = registration.get("ticketing", {})

            sold_out = ticketing.get("soldOut", False)
            lowest_price = None
            highest_price = None

            # Parse price information
            lowest_price_data = ticketing.get("lowestTicketPrice", {})
            if lowest_price_data and "value" in lowest_price_data:
                try:
                    lowest_price = float(lowest_price_data["value"])
                except (ValueError, TypeError):
                    pass

            highest_price_data = ticketing.get("highestTicketPrice", {})
            if highest_price_data and "value" in highest_price_data:
                try:
                    highest_price = float(highest_price_data["value"])
                except (ValueError, TypeError):
                    pass

            # Create Grove34Event object
            return Grove34Event(
                id=event_id,
                title=title,
                slug=slug,
                description=description if description else None,
                start_date=start_date,
                timezone_id=timezone_id,
                location_name=location_name if location_name else None,
                ticketing_data=ticketing if ticketing else None,
                sold_out=sold_out,
                lowest_price=lowest_price,
                highest_price=highest_price,
                raw_event_data=event_data,  # Store raw data for debugging
            )

        except Exception as e:
            Logger.error(f"Error converting event to Grove34Event: {e}")
            return None
