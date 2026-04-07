"""Funny Bone Comedy Club event transformer."""

from laughtrack.core.entities.event.funny_bone import FunnyBoneEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class FunnyBoneEventTransformer(DataTransformer[FunnyBoneEvent]):
    """Transforms FunnyBoneEvent objects into Show objects via event.to_show()."""

    pass
