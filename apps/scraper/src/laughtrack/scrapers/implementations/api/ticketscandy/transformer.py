"""Transformer for TicketsCandy events.

TicketsCandy pages emit standard schema.org Event JSON-LD, so the shared
JsonLdEvent -> Show transform is reused unchanged.
"""

from laughtrack.scrapers.implementations.json_ld.transformer import JsonLdTransformer


class TicketsCandyTransformer(JsonLdTransformer):
    """Alias of JsonLdTransformer (JsonLdEvent.to_show)."""

    pass
