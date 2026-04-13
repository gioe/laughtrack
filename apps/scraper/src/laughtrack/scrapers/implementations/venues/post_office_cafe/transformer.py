"""Post Office Cafe & Cabaret event transformer."""

from laughtrack.core.entities.event.post_office_cafe import PostOfficeCafePerformance
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class PostOfficeCafeEventTransformer(DataTransformer[PostOfficeCafePerformance]):
    """Transforms PostOfficeCafePerformance objects into Show objects.

    PostOfficeCafePerformance implements ShowConvertible, so the base
    DataTransformer.transform_to_show() delegates to
    PostOfficeCafePerformance.to_show() automatically.
    """
