"""FareHarbor event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import FareHarborEvent


class FareHarborEventTransformer(DataTransformer[FareHarborEvent]):
    pass
