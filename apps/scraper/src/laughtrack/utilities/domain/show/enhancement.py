"""
Show Enhancement Utilities

Domain-specific utilities for enhancing Show objects with advanced data processing.
Provides reusable logic for ticket processing, tag extraction, and data validation.
"""

from typing import List, Optional, Tuple

from laughtrack.core.entities.event.event import Offer, JsonLdEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.utilities.domain.show.utils import ShowUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger
from gioe_libs.string_utils import StringUtils


class ShowEnhancement:
    """Utilities for enhancing Show objects with advanced data processing."""

    @staticmethod
    def enhance_tickets_from_event(event: JsonLdEvent) -> List[Ticket]:
        """
        Create enhanced tickets from Event offers with advanced processing.

        Args:
            event: The Event instance containing offer data

        Returns:
            List of enhanced Ticket objects with proper types and pricing
        """
        if not event.offers:
            return []

        enhanced_tickets = []
        for offer in event.offers:
            ticket = ShowEnhancement._create_enhanced_ticket_from_offer(offer)
            if ticket:
                enhanced_tickets.append(ticket)

        return enhanced_tickets

    @staticmethod
    def _create_enhanced_ticket_from_offer(offer: Offer) -> Optional[Ticket]:
        """Create an enhanced ticket from an offer with advanced processing."""
        try:
            # Extract and validate price
            price = ShowEnhancement._extract_price_from_offer(offer)
            if price is None:
                Logger.warning(f"Could not extract valid price from offer: {offer.price}")
                return None

            # Determine ticket type from offer data
            ticket_type = ShowEnhancement._determine_ticket_type(offer)

            # Determine sold out status
            sold_out = ShowEnhancement._is_sold_out(offer)

            return Ticket(price=price, purchase_url=offer.url or "", type=ticket_type, sold_out=sold_out)

        except Exception as e:
            Logger.error(f"Error creating enhanced ticket from offer: {e}")
            return None

    @staticmethod
    def _extract_price_from_offer(offer: Offer) -> Optional[float]:
        """Extract price using primitive FormattingUtils with fallback logic."""
        if not offer.price:
            return None

        try:
            # Try direct float conversion first
            return float(offer.price)
        except (ValueError, TypeError):
            pass

        # Use primitive utility for price extraction
        price_str = StringUtils.extract_price(str(offer.price))
        if price_str and price_str != "0":
            try:
                return float(price_str)
            except ValueError:
                pass

        return None

    @staticmethod
    def _determine_ticket_type(offer: Offer) -> str:
        """Determine ticket type from offer data with intelligent defaults."""
        # Use availability as type if it looks like a ticket type
        if offer.availability and offer.availability.lower() not in ["instock", "soldout", "limitedavailability"]:
            return offer.availability

        # Use price currency as fallback if it's not a standard currency
        if offer.price_currency and offer.price_currency not in ["USD", "EUR", "GBP", "CAD"]:
            return offer.price_currency

        # Default to general admission
        return "General Admission"

    @staticmethod
    def _is_sold_out(offer: Offer) -> bool:
        """Determine sold out status from offer availability."""
        if not offer.availability:
            return False

        availability_lower = offer.availability.lower()
        return availability_lower in ["soldout", "sold out", "unavailable"]

    @staticmethod
    def extract_advanced_tags_from_event(event: JsonLdEvent) -> List[str]:
        """
        Extract advanced tags from Event with intelligent processing.

        Args:
            event: The Event instance to extract tags from

        Returns:
            List of relevant tags
        """
        tags = []

        # Add event type as a tag
        if event.event_type and event.event_type.lower() != "event":
            tags.append(event.event_type)

        # Add event status if meaningful
        if event.event_status and event.event_status.lower() not in ["published", "scheduled"]:
            tags.append(event.event_status)

        # Extract tags from description
        if event.description:
            description_tags = ShowEnhancement._extract_tags_from_description(event.description)
            tags.extend(description_tags)

        # Extract tags from event name
        if event.name:
            name_tags = ShowEnhancement._extract_tags_from_name(event.name)
            tags.extend(name_tags)

        # Remove duplicates and filter
        return list(set(tag.strip() for tag in tags if tag and tag.strip()))

    @staticmethod
    def _extract_tags_from_description(description: str) -> List[str]:
        """Extract relevant tags from event description."""
        tags = []
        description_lower = description.lower()

        # Comedy-specific keywords
        comedy_keywords = [
            "open mic",
            "open-mic",
            "comedy show",
            "stand-up",
            "standup",
            "improv",
            "sketch",
            "roast",
            "showcase",
            "comedy night",
        ]

        for keyword in comedy_keywords:
            if keyword in description_lower:
                tags.append(keyword.title())

        return tags

    @staticmethod
    def _extract_tags_from_name(name: str) -> List[str]:
        """Extract relevant tags from event name."""
        tags = []
        name_lower = name.lower()

        # Show type indicators
        show_types = ["open mic", "showcase", "workshop", "class", "special event"]

        for show_type in show_types:
            if show_type in name_lower:
                tags.append(show_type.title())

        return tags

    @staticmethod
    def enhance_show_url(show: Show, source_url: str) -> Show:
        """
        Enhance show URL with fallback logic using common utilities.

        Args:
            show: The Show instance to enhance
            source_url: The source URL from scraping

        Returns:
            Show with enhanced URL
        """
        if show.show_page_url and StringUtils.is_valid_url(show.show_page_url):
            show.show_page_url = show.show_page_url.strip()

        if source_url and StringUtils.is_valid_url(source_url):
            show.show_page_url = source_url.strip()

        return show

    @staticmethod
    def validate_and_fix_show_data(show: Show) -> Tuple[Show, List[str]]:
        """
        Validate and fix Show data with intelligent corrections.

        Args:
            show: The Show instance to validate and fix

        Returns:
            Tuple of (fixed_show, list_of_warnings)
        """
        warnings = []

        # Fix missing or invalid name using common utilities
        show.name = ShowUtils.clean_show_name(show.name)
        if show.name == "Untitled Show":
            warnings.append("Show name was empty, set to 'Untitled Show'")

        # Fix missing room using common utilities
        if show.room is None:
            show.room = ""

        # Validate and fix tickets
        if show.tickets:
            valid_tickets = []
            for ticket in show.tickets:
                if ticket.price >= 0:
                    valid_tickets.append(ticket)
                else:
                    warnings.append(f"Removed ticket with invalid price: {ticket.price}")
            show.tickets = valid_tickets

        return show, warnings
