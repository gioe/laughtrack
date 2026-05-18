"""Transformer for the generic SellingTicket scraper."""

from laughtrack.core.entities.event.sellingticket import SellingTicketEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class SellingTicketTransformer(DataTransformer[SellingTicketEvent]):
    """Transforms SellingTicketEvent objects into Show objects."""
