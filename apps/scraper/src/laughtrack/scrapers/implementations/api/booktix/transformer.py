"""BookTix event transformer.

BookTixEvent implements ShowConvertible.to_show(), so the transformer is a thin
DataTransformer subtype — the pipeline calls to_show() on each event.
"""

from laughtrack.core.entities.event.booktix import BookTixEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class BookTixEventTransformer(DataTransformer[BookTixEvent]):
    pass
