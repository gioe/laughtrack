"""Transformer for 1234ticket events (already normalized to ShowConvertible)."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import Ticket1234Event


class Ticket1234Transformer(DataTransformer[Ticket1234Event]):
    """Pass-through transformer; events are normalized in the scraper."""
