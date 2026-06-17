"""EventON event transformer.

EventONEvent implements ShowConvertible.to_show(), so the transformer is a thin
DataTransformer subtype — the pipeline calls to_show() on each event.
"""

from laughtrack.core.entities.event.eventon import EventONEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class EventONEventTransformer(DataTransformer[EventONEvent]):
    pass
