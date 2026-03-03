"""Bushwick Comedy Club data extraction utilities."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.bushwick import BushwickEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.bushwick.models.factory import WixResponseFactory
from laughtrack.scrapers.implementations.venues.bushwick.models.wix_response import WixEvent, WixEventsResponse
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


class BushwickEventExtractor:
    """Utility class for extracting Wix event data from API responses."""

    @staticmethod
    def extract_events(api_response: WixEventsResponse) -> List[BushwickEvent]:
        """
        Extract Bushwick Comedy Club events from Wix API response.

        Args:
            api_response: JSON response from Wix events API

        Returns:
            List of BushwickEvent objects extracted from the API response
        """
        try:
            bushwick_events = []

            for event_data in api_response.events:
                try:
                    event = BushwickEventExtractor._convert_wix_to_bushwick_event(event_data)
                    if event:
                        bushwick_events.append(event)
                except Exception as e:
                    Logger.warn(f"Failed to create BushwickEvent from data: {e}")
                    continue

            return bushwick_events

        except Exception as e:
            Logger.error(f"Error extracting Wix events: {e}")
            return []

    @staticmethod
    def _convert_wix_to_bushwick_event(event_data: WixEvent) -> Optional[BushwickEvent]:
        """
        Convert Wix event data to BushwickEvent object.

        Args:
            event_data: WixEvent dataclass object from Wix API

        Returns:
            BushwickEvent object or None if conversion fails
        """
        try:
            # Convert the structured dataclasses back to dictionaries for BushwickEvent
            # This maintains compatibility with the existing BushwickEvent structure
            # while allowing us to use the new typed WixEvent dataclasses

            # Convert scheduling dataclass to dictionary
            scheduling_dict = {
                "config": {
                    "scheduleTbd": event_data.scheduling.config.scheduleTbd,
                    "startDate": event_data.scheduling.config.startDate,
                    "endDate": event_data.scheduling.config.endDate,
                    "timeZoneId": event_data.scheduling.config.timeZoneId,
                    "endDateHidden": event_data.scheduling.config.endDateHidden,
                    "showTimeZone": event_data.scheduling.config.showTimeZone,
                    "recurrences": {
                        "occurrences": event_data.scheduling.config.recurrences.occurrences,
                        "categoryId": event_data.scheduling.config.recurrences.categoryId,
                        "status": event_data.scheduling.config.recurrences.status,
                    },
                },
                "formatted": event_data.scheduling.formatted,
                "startDateFormatted": event_data.scheduling.startDateFormatted,
                "startTimeFormatted": event_data.scheduling.startTimeFormatted,
                "endDateFormatted": event_data.scheduling.endDateFormatted,
                "endTimeFormatted": event_data.scheduling.endTimeFormatted,
            }

            # Convert location dataclass to dictionary
            location_dict = {
                "name": event_data.location.name,
                "coordinates": {"lat": event_data.location.coordinates.lat, "lng": event_data.location.coordinates.lng},
                "address": event_data.location.address,
                "type": event_data.location.type,
                "tbd": event_data.location.tbd,
            }

            # Convert registration dataclass to dictionary for registration_form field
            registration_dict = {
                "type": event_data.registration.type,
                "status": event_data.registration.status,
                "ticketing": {
                    "lowestPrice": event_data.registration.ticketing.lowestPrice,
                    "highestPrice": event_data.registration.ticketing.highestPrice,
                    "currency": event_data.registration.ticketing.currency,
                    "soldOut": event_data.registration.ticketing.soldOut,
                },
            }

            return BushwickEvent(
                id=event_data.id,
                title=event_data.title,
                description=event_data.description,
                scheduling=scheduling_dict,
                location=location_dict,
                registration_form=registration_dict,
                created_date=event_data.created,
                updated_date=event_data.modified,
                status=str(event_data.status),
                _raw_data=None,  # Could store the original WixEvent here if needed
            )

        except Exception as e:
            Logger.warn(f"Failed to convert Wix data to BushwickEvent: {e}")
            return None

    @staticmethod
    def extract_single_event(event_data: Dict[str, Any]) -> Optional[BushwickEvent]:
        """
        Extract a single Wix event from event data.

        Args:
            event_data: Single event data dictionary

        Returns:
            BushwickEvent object or None if extraction fails
        """
        try:
            # Convert dictionary to WixEvent dataclass first
            wix_event = WixResponseFactory.create_wix_event(event_data)
            return BushwickEventExtractor._convert_wix_to_bushwick_event(wix_event)
        except Exception as e:
            Logger.warn(f"Failed to extract single event: {e}")
            return None
