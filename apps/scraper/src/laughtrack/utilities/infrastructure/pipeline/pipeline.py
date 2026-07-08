"""
Data transformation pipeline for orchestrating multiple transformers.

This module provides the main pipeline class that manages transformers
and field extractors.
"""

from typing import Callable, Dict, List

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.ports.scraping import EventListContainer

from ..transformer.base import DataTransformer


class ShowTransformationPipeline:
    """
    Pipeline that applies multiple transformers to convert raw data to Shows.

    Features:
    - Multiple transformer support
    - Automatic format detection
    - Error handling
    - Extensible transformer registration
    """

    def __init__(self, club: Club):
        self.club = club
        self.transformers: List[DataTransformer] = []
        self.field_extractors: Dict[str, Callable] = {}

    def register_transformer(self, transformer: DataTransformer):
        """Register a data transformer."""
        self.transformers.append(transformer)

    def transform(self, raw_data: EventListContainer) -> List[Show]:
        """
        Transform raw data to Show objects using registered transformers.

        Args:
            raw_data: Raw scraped data containing event_list

        Returns:
            List of validated Show objects
        """
        if not self.transformers:
            Logger.error(
                f"No transformers registered for {self.club.name} — "
                f"did you forget to call register_transformer in __init__?"
            )
            return []

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
                            self._warn_if_ticketless(transformer_show)
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

    def _warn_if_ticketless(self, show: Show) -> None:
        """WARN and tick the run diagnostics counter for a show with no tickets.

        Every show must emit >=1 ticket — all three clients hide ticketless
        shows, so a scraper regression that stops attaching tickets makes
        shows invisible while the run still classifies HEALTHY. The show is
        never dropped: enrichment may attach tickets later.
        """
        if show.tickets:
            return
        Logger.warn(
            f"Ticketless show '{show.name}' at {self.club.name} — clients hide "
            f"shows with zero tickets; persisting anyway (enrichment may attach "
            f"tickets later)"
        )
        diagnostics = current_diagnostics()
        if diagnostics is not None:
            diagnostics.record_ticketless_show()


def create_standard_pipeline(club: Club) -> ShowTransformationPipeline:
    """Create an empty pipeline. Each scraper registers its own transformer via __init__."""
    return ShowTransformationPipeline(club)
