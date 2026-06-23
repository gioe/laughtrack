"""AEG/Goldenvoice Carbonhouse venue-page event transformer.

AEGAXSEvent implements ShowConvertible.to_show(), so the transformer is a thin
DataTransformer subtype — the pipeline calls to_show() on each event.
"""

from laughtrack.core.entities.event.aeg_axs import AEGAXSEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class AEGAXSEventTransformer(DataTransformer[AEGAXSEvent]):
    pass
