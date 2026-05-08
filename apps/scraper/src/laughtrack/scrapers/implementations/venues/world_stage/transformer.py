"""World Stage event transformer (relies on WorldStageEvent.to_show)."""

from laughtrack.core.entities.event.world_stage import WorldStageEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class WorldStageTransformer(DataTransformer[WorldStageEvent]):
    pass
