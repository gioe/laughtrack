"""
Data transformation pipeline for orchestrating multiple transformers.

This module provides the main pipeline class that manages transformers,
field extractors, and validators.
"""

from typing import Callable, Dict, List

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer

from ..transformer.base import DataTransformer


class ShowTransformationPipeline:
    """
    Pipeline that applies multiple transformers to convert raw data to Shows.

    Features:
    - Multiple transformer support
    - Automatic format detection
    - Validation and error handling
    - Extensible transformer registration
    """

    def __init__(self, club: Club):
        self.club = club
        self.transformers: List[DataTransformer] = []
        self.field_extractors: Dict[str, Callable] = {}
        self.validators: List[Callable[[Show], bool]] = []

    def register_transformer(self, transformer: DataTransformer):
        """Register a data transformer."""
        self.transformers.append(transformer)

    def register_validator(self, validator: Callable[[Show], bool]):
        """Register a show validator function."""
        self.validators.append(validator)

    def transform(self, raw_data: EventListContainer) -> List[Show]:
        """
        Transform raw data to Show objects using registered transformers.

        Args:
            raw_data: Raw scraped data containing event_list

        Returns:
            List of validated Show objects
        """
        shows = []

        # Process each event in the event_list
        for event_data in raw_data.event_list:
            # Find compatible transformer for this specific event
            matched = False
            for transformer in self.transformers:
                try:
                    if transformer.can_transform(event_data):
                        transformer_show = transformer.transform_to_show(event_data)
                        shows.append(transformer_show)
                        matched = True
                        break
                except Exception as e:
                    Logger.error(
                        f"Transformer {transformer.__class__.__name__} failed for event: {e}",
                    )
                    continue
            if not matched:
                Logger.debug(
                    f"No transformer matched event of type {type(event_data).__name__} for {self.club.name}"
                )

        if not shows:
            Logger.warn(f"No valid shows found for {self.club.name}")

        return shows


def create_standard_pipeline(club: Club) -> ShowTransformationPipeline:
    """Create a pipeline with common transformers and validators."""
    pipeline = ShowTransformationPipeline(club)

    # Register common transformers
    # Import transformers lazily to avoid import-time cycles during discovery
    from laughtrack.scrapers.implementations.json_ld.transformer import JsonLdTransformer
    from laughtrack.scrapers.implementations.venues.broadway_comedy_club.transformer import (
        BroadwayEventTransformer,
    )
    from laughtrack.scrapers.implementations.venues.bushwick.transformer import BushwickEventTransformer
    from laughtrack.scrapers.implementations.venues.comedy_cellar.transformer import (
        ComedyCellarEventTransformer,
    )
    from laughtrack.scrapers.implementations.venues.gotham.transformer import GothamEventTransformer
    from laughtrack.scrapers.implementations.venues.grove_34.transformer import Grove34EventTransformer
    from laughtrack.scrapers.implementations.venues.uncle_vinnies.transformer import UncleVinniesEventTransformer
    from laughtrack.scrapers.implementations.api.eventbrite.transformer import EventbriteEventTransformer
    from laughtrack.scrapers.implementations.api.ticketmaster.transformer import TicketmasterEventTransformer
    from laughtrack.scrapers.implementations.api.seatengine.transformer import SeatEngineEventTransformer

    pipeline.register_transformer(JsonLdTransformer(club))
    pipeline.register_transformer(BroadwayEventTransformer(club))
    pipeline.register_transformer(BushwickEventTransformer(club))
    pipeline.register_transformer(ComedyCellarEventTransformer(club))
    pipeline.register_transformer(GothamEventTransformer(club))
    pipeline.register_transformer(Grove34EventTransformer(club))
    pipeline.register_transformer(UncleVinniesEventTransformer(club))
    pipeline.register_transformer(EventbriteEventTransformer(club))
    pipeline.register_transformer(TicketmasterEventTransformer(club))
    pipeline.register_transformer(SeatEngineEventTransformer(club))

    return pipeline
