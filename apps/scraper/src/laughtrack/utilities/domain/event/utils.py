"""Event-related utility functions for matching and manipulation."""

from typing import List, Optional, Union

from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.entities.event.event import JsonLdEvent


class EventUtils:
    """Utility functions for working with event data."""

    @staticmethod
    def find_matching_event(events: List[JSONDict], event_id: str) -> Optional[JSONDict]:
        """
        Find the event that matches the given event ID by checking the offers URL.

        Args:
            events: List of event dictionaries to search
            event_id: Event ID to match against

        Returns:
            Matching event dictionary or None if no match found
        """
        for event in events:
            offers = event.get("offers", [])
            if not isinstance(offers, list):
                offers = [offers]

            for offer in offers:
                if isinstance(offer, dict):
                    offer_url = offer.get("url", "")
                    if event_id in offer_url:
                        return event
        return None

    @staticmethod
    def find_matching_event_object(events, event_id: str):
        """
        Find the Event object that matches the given event ID by checking the offers URL.

        Args:
            events: List of Event objects to search
            event_id: Event ID to match against

        Returns:
            Matching Event object or None if no match found
        """

        for event in events:
            if isinstance(event, JsonLdEvent) and event.offers:
                for offer in event.offers:
                    if offer.url and event_id in offer.url:
                        return event
        return None

    @staticmethod
    def convert_events_to_dicts(events) -> List[JSONDict]:
        """
        Convert Event objects to dictionaries with a consistent structure.

        Args:
            events: List of Event objects

        Returns:
            List of event dictionaries
        """

        event_dicts = []
        for event in events:
            if isinstance(event, JsonLdEvent):
                # Extract core fields from Event object
                event_dict = {
                    "name": event.name,
                    "startDate": event.start_date.isoformat() if event.start_date else None,
                    "description": event.description,
                    "url": event.url,
                    "location": (
                        {
                            "name": event.location.name if event.location else None,
                            "address": (
                                {
                                    "streetAddress": (
                                        event.location.address.street_address
                                        if event.location and event.location.address
                                        else None
                                    ),
                                    "addressLocality": (
                                        event.location.address.address_locality
                                        if event.location and event.location.address
                                        else None
                                    ),
                                    "addressRegion": (
                                        event.location.address.address_region
                                        if event.location and event.location.address
                                        else None
                                    ),
                                }
                                if event.location and event.location.address
                                else {}
                            ),
                        }
                        if event.location
                        else {}
                    ),
                    "offers": [],
                    "performer": [],
                }

                # Add offers
                if event.offers:
                    for offer in event.offers:
                        offer_dict = {
                            "price": offer.price,
                            "url": offer.url,
                            "availability": offer.availability,
                            "priceCurrency": offer.price_currency,
                        }
                        event_dict["offers"].append(offer_dict)

                # Add performers
                if event.performers:
                    for performer in event.performers:
                        performer_dict = {"name": performer.name}
                        event_dict["performer"].append(performer_dict)

                event_dicts.append(event_dict)
            else:
                # Already a dict, pass through
                event_dicts.append(event)

        return event_dicts
