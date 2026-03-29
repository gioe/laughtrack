"""Four Day Weekend Comedy event transformer."""

from laughtrack.core.entities.event.four_day_weekend import FourDayWeekendEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class FourDayWeekendEventTransformer(DataTransformer[FourDayWeekendEvent]):
    """Transforms FourDayWeekendEvent objects into Show objects via event.to_show()."""

    pass
