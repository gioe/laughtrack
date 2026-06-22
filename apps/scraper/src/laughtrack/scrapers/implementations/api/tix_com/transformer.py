"""Tix.com event transformer (pass-through to TixComEvent.to_show)."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import TixComEvent


class TixComEventTransformer(DataTransformer[TixComEvent]):
    pass
