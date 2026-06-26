"""StandUp Media event transformer for the Funny Bone / Levity platform scraper."""

from laughtrack.core.entities.event.standup_media import StandUpMediaEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class StandUpMediaEventTransformer(DataTransformer[StandUpMediaEvent]):
    """Transforms StandUpMediaEvent objects into Show objects via event.to_show()."""

    pass
