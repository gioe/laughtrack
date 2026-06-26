"""Arts-People event transformer.

ArtsPeopleEvent implements ShowConvertible.to_show(), so the transformer is a
thin DataTransformer subtype — the pipeline calls to_show() on each event.
"""

from laughtrack.core.entities.event.arts_people import ArtsPeopleEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class ArtsPeopleEventTransformer(DataTransformer[ArtsPeopleEvent]):
    pass
