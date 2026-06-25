"""Denver Comedy Lounge event transformer."""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import DenverComedyLoungeShow


class DenverComedyLoungeTransformer(DataTransformer[DenverComedyLoungeShow]):
    """Convert DenverComedyLoungeShow objects to Show objects.

    Delegates to DenverComedyLoungeShow.to_show() via the DataTransformer base.
    """

    pass
