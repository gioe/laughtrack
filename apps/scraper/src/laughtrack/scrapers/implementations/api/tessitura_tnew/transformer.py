"""Tessitura TNEW event transformer."""

from laughtrack.core.entities.event.tessitura_tnew import TessituraTNEWEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class TessituraTNEWEventTransformer(DataTransformer[TessituraTNEWEvent]):
    pass
