"""Delirious Comedy Club event transformer."""

from laughtrack.core.entities.event.friendlysky import FriendlySkyEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class DeliriousEventTransformer(DataTransformer[FriendlySkyEvent]):
    """Transforms FriendlySkyEvent objects into Show objects.

    FriendlySkyEvent implements ShowConvertible, so the base
    DataTransformer.transform_to_show() delegates to
    FriendlySkyEvent.to_show() automatically.
    """
