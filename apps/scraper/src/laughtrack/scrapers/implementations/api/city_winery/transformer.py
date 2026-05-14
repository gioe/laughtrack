"""City Winery event transformer."""

from laughtrack.core.entities.event.city_winery import CityWineryEvent
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer


class CityWineryEventTransformer(DataTransformer[CityWineryEvent]):
    """Transforms City Winery API events into Show objects via event.to_show()."""

    pass
