"""
Ticket Utilities

Domain-specific utilities for working with Ticket entities.
Provides operations for ticket data processing, validation, and deduplication.
"""

from typing import List

from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.logger.logger import Logger


class TicketUtils:
    """Utility class for ticket-specific operations and data processing."""

    @staticmethod
    def deduplicate_tickets(tickets: List[Ticket]) -> List[Ticket]:
        """
        Deduplicate tickets based on unique constraint (show_id, type).

        Args:
            tickets: List of tickets to deduplicate

        Returns:
            List of deduplicated tickets
        """
        if not tickets:
            return []

        # Use dictionary to deduplicate based on (show_id, type) tuple
        unique_tickets = {}

        for ticket in tickets:
            # Create key based on unique constraint
            key = (ticket.show_id, ticket.type)

            # Keep the first ticket for each unique key (or implement your own logic)
            if key not in unique_tickets:
                unique_tickets[key] = ticket
            else:
                # Optionally log duplicates
                Logger.debug(f"Duplicate ticket found for show_id={ticket.show_id}, type={ticket.type}")

        deduplicated = list(unique_tickets.values())

        if len(deduplicated) < len(tickets):
            removed_count = len(tickets) - len(deduplicated)
            Logger.info(f"Deduplicated {removed_count} duplicate tickets (kept {len(deduplicated)})")

        return deduplicated

    @staticmethod
    def validate_ticket_data(ticket: Ticket) -> List[str]:
        """
        Validate ticket data and return list of validation errors.

        Args:
            ticket: Ticket object to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate required fields
        if not hasattr(ticket, "price") or ticket.price is None:
            errors.append("Ticket price is required")
        elif not isinstance(ticket.price, (int, float)) or ticket.price < 0:
            errors.append("Ticket price must be a non-negative number")

        if not hasattr(ticket, "purchase_url") or not ticket.purchase_url:
            errors.append("Ticket purchase URL is required")
        elif not isinstance(ticket.purchase_url, str) or not ticket.purchase_url.strip():
            errors.append("Ticket purchase URL must be a non-empty string")

        # Validate optional fields
        if hasattr(ticket, "type") and ticket.type:
            if not isinstance(ticket.type, str):
                errors.append("Ticket type must be a string")

        if hasattr(ticket, "sold_out") and ticket.sold_out is not None:
            if not isinstance(ticket.sold_out, bool):
                errors.append("Ticket sold_out status must be a boolean")

        return errors

    @staticmethod
    def get_ticket_summary(tickets: List[Ticket]) -> dict:
        """
        Generate summary statistics for a list of tickets.

        Args:
            tickets: List of tickets to analyze

        Returns:
            Dictionary containing ticket summary statistics
        """
        if not tickets:
            return {
                "total_tickets": 0,
                "unique_shows": 0,
                "price_range": None,
                "average_price": 0.0,
                "sold_out_count": 0,
                "ticket_types": [],
            }

        # Calculate statistics
        prices = [ticket.price for ticket in tickets if hasattr(ticket, "price") and ticket.price is not None]
        show_ids = set(ticket.show_id for ticket in tickets if hasattr(ticket, "show_id") and ticket.show_id)
        sold_out_count = sum(1 for ticket in tickets if hasattr(ticket, "sold_out") and ticket.sold_out)
        ticket_types = list(set(ticket.type for ticket in tickets if hasattr(ticket, "type") and ticket.type))

        return {
            "total_tickets": len(tickets),
            "unique_shows": len(show_ids),
            "price_range": (min(prices), max(prices)) if prices else None,
            "average_price": sum(prices) / len(prices) if prices else 0.0,
            "sold_out_count": sold_out_count,
            "ticket_types": sorted(ticket_types),
        }

    @staticmethod
    def filter_tickets_by_show(tickets: List[Ticket], show_id: int) -> List[Ticket]:
        """
        Filter tickets by show ID.

        Args:
            tickets: List of tickets to filter
            show_id: Show ID to filter by

        Returns:
            List of tickets for the specified show
        """
        return [ticket for ticket in tickets if hasattr(ticket, "show_id") and ticket.show_id == show_id]

    @staticmethod
    def group_tickets_by_show(tickets: List[Ticket]) -> dict:
        """
        Group tickets by show ID.

        Args:
            tickets: List of tickets to group

        Returns:
            Dictionary mapping show_id to list of tickets
        """
        grouped = {}

        for ticket in tickets:
            if hasattr(ticket, "show_id") and ticket.show_id:
                show_id = ticket.show_id
                if show_id not in grouped:
                    grouped[show_id] = []
                grouped[show_id].append(ticket)

        return grouped

    @staticmethod
    def normalize_ticket_type(ticket_type: str) -> str:
        """
        Normalize ticket type string for consistency.

        Args:
            ticket_type: Raw ticket type string

        Returns:
            Normalized ticket type
        """
        if not ticket_type:
            return "General Admission"

        # Clean and normalize
        normalized = ticket_type.strip().title()

        # Common normalizations
        type_mappings = {
            "Ga": "General Admission",
            "General": "General Admission",
            "Vip": "VIP",
            "V.I.P.": "VIP",
            "Premium": "Premium",
            "Standard": "General Admission",
        }

        return type_mappings.get(normalized, normalized)
