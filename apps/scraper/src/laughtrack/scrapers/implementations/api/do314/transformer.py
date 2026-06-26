"""do314 event transformer for the DoStuff Media platform scraper."""

from laughtrack.core.entities.event.do314 import Do314Event
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class Do314EventTransformer(DataTransformer[Do314Event]):
    """Transforms Do314Event objects into Show objects via event.to_show()."""

    pass
