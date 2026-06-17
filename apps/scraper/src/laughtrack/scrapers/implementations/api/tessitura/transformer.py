"""Tessitura event transformer.

TessituraEvent implements ShowConvertible.to_show(), so the transformer is a
thin DataTransformer subtype — the pipeline calls to_show() on each event.
"""

from laughtrack.core.entities.event.tessitura import TessituraEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TessituraEventTransformer(DataTransformer[TessituraEvent]):
    pass
