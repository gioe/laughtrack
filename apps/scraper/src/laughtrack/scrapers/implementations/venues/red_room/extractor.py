"""RED ROOM Comedy Club event extraction from Wix paginated-events API."""

from typing import List, Optional

from laughtrack.core.entities.event.red_room import RedRoomEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.venues.bushwick.models.wix_response import WixEvent, WixEventsResponse


class RedRoomEventExtractor:
    """Converts Wix paginated-events API response into RedRoomEvent objects."""

    @staticmethod
    def extract_events(api_response: WixEventsResponse) -> List[RedRoomEvent]:
        """Extract RedRoomEvent objects from the Wix paginated-events API response.

        Args:
            api_response: Typed WixEventsResponse from the paginated-events endpoint.

        Returns:
            List of RedRoomEvent objects.
        """
        try:
            events = []
            for event_data in api_response.events:
                try:
                    event = RedRoomEventExtractor._convert_wix_event(event_data)
                    if event:
                        events.append(event)
                except Exception as e:
                    Logger.warn(f"RedRoomEventExtractor: skipping event due to error: {e}")
            return events
        except Exception as e:
            Logger.error(f"RedRoomEventExtractor: error extracting events: {e}")
            return []

    @staticmethod
    def _convert_wix_event(event_data: WixEvent) -> Optional[RedRoomEvent]:
        """Convert a WixEvent dataclass to a RedRoomEvent."""
        try:
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

            location_dict = {
                "name": event_data.location.name,
                "coordinates": {
                    "lat": event_data.location.coordinates.lat,
                    "lng": event_data.location.coordinates.lng,
                },
                "address": event_data.location.address,
                "type": event_data.location.type,
                "tbd": event_data.location.tbd,
            }

            registration_dict = {
                "type": event_data.registration.type,
                "status": event_data.registration.status,
                "ticketing": {
                    "lowestPrice": event_data.registration.ticketing.lowestPrice,
                    "highestPrice": event_data.registration.ticketing.highestPrice,
                    "currency": event_data.registration.ticketing.currency,
                    "soldOut": event_data.registration.ticketing.soldOut,
                },
                "eventSlug": event_data.slug,
            }

            return RedRoomEvent(
                id=event_data.id,
                title=event_data.title,
                description=event_data.description,
                scheduling=scheduling_dict,
                location=location_dict,
                registration_form=registration_dict,
                created_date=event_data.created,
                updated_date=event_data.modified,
                status=str(event_data.status),
                _raw_data=None,
            )
        except Exception as e:
            Logger.warn(f"RedRoomEventExtractor: failed to convert event: {e}")
            return None
