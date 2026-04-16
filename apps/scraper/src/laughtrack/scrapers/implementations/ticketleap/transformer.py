"""TicketLeap event → Show transformer.

TicketLeap event detail pages emit standard JSON-LD Event blocks, which map
cleanly to JsonLdEvent. The default DataTransformer behavior is sufficient.
"""

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TicketleapTransformer(DataTransformer[JsonLdEvent]):
    pass
