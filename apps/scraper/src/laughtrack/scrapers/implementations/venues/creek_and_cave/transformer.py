"""Creek and Cave event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import CreekAndCaveShow


class CreekAndCaveEventTransformer(DataTransformer[CreekAndCaveShow]):
    """
    Transformer for converting CreekAndCaveShow objects to Show objects.

    Delegates to CreekAndCaveShow.to_show() via the DataTransformer base class.
    """

    pass
