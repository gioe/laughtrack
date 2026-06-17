"""NeonCRM event transformer.

NeonCRMEvent implements ShowConvertible.to_show(), so the transformer is a thin
DataTransformer subtype — the pipeline calls to_show() on each event.
"""

from laughtrack.core.entities.event.neoncrm import NeonCRMEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class NeonCRMEventTransformer(DataTransformer[NeonCRMEvent]):
    pass
