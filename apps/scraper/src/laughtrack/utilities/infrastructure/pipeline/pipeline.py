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
                        if transformer_show is not None:
                            shows.append(transformer_show)
                        else:
                            Logger.debug(
                                f"{transformer.__class__.__name__} returned None for event "
                                f"{type(event_data).__name__} at {self.club.name} — skipped"
                            )
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
    """Create an empty pipeline. Each scraper registers its own transformer via __init__."""
    return ShowTransformationPipeline(club)
