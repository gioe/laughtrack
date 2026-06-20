"""Pabst Theater Group venue-page event transformer.

PabstAXSEvent implements ShowConvertible.to_show(), so the transformer is a thin
DataTransformer subtype — the pipeline calls to_show() on each event.
"""

from laughtrack.core.entities.event.pabst_axs import PabstAXSEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class PabstAXSEventTransformer(DataTransformer[PabstAXSEvent]):
    pass
