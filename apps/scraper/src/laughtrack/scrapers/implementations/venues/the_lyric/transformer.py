"""Event transformer for the Indy Systems (The Lyric) scraper."""

from laughtrack.scrapers.implementations.venues.the_lyric.event import TheLyricEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TheLyricEventTransformer(DataTransformer[TheLyricEvent]):
    """Transforms TheLyricEvent objects into Show objects via event.to_show()."""

    pass
