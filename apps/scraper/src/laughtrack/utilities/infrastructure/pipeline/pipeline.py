"""
Data transformation pipeline for orchestrating multiple transformers.

This module provides the main pipeline class that manages transformers,
field extractors, and validators.
"""

from typing import Callable, Dict, List, Type

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


def _discover_transformer_classes() -> List[Type[DataTransformer]]:
    """
    Auto-discover all concrete DataTransformer subclasses under
    laughtrack.scrapers.implementations by importing every *.transformer module
    and then walking the DataTransformer subclass tree.

    Mirrors the approach used by ScraperMapping for BaseScraper discovery.
    """
    import importlib
    import pkgutil

    # Import all *.transformer modules so their classes are registered as subclasses
    try:
        impl_root = importlib.import_module("laughtrack.scrapers.implementations")
        pkg_path = getattr(impl_root, "__path__", None)
        pkg_name = getattr(impl_root, "__name__", "laughtrack.scrapers.implementations")

        if pkg_path:
            for mod in pkgutil.walk_packages(pkg_path, pkg_name + "."):
                if mod.name.endswith(".transformer"):
                    try:
                        importlib.import_module(mod.name)
                    except Exception as e:
                        Logger.warn(f"Failed importing transformer module {mod.name}: {e}")
    except Exception as e:
        Logger.error(f"Error discovering transformer modules: {e}")

    # Walk the DataTransformer subclass tree and collect all concrete subclasses
    seen: set = set()
    classes: List[Type[DataTransformer]] = []
    stack: List[Type[DataTransformer]] = [DataTransformer]

    while stack:
        current = stack.pop()
        for subclass in current.__subclasses__():
            if subclass in seen:
                continue
            seen.add(subclass)
            stack.append(subclass)
            classes.append(subclass)

    # Sort for deterministic registration order
    classes.sort(key=lambda cls: (cls.__module__, cls.__name__))
    return classes


def create_standard_pipeline(club: Club) -> ShowTransformationPipeline:
    """Create a pipeline with auto-discovered transformers."""
    pipeline = ShowTransformationPipeline(club)

    for cls in _discover_transformer_classes():
        pipeline.register_transformer(cls(club))

    return pipeline
