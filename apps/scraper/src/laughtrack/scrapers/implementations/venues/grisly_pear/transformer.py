"""Grisly Pear data transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import GrislyPearEvent


class GrislyPearTransformer(DataTransformer[GrislyPearEvent]):
    """Transform Grisly Pear events via their ShowConvertible implementation."""

