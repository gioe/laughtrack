"""Page data for the generic City Winery API scraper."""

from dataclasses import dataclass

from laughtrack.core.entities.event.city_winery import CityWineryEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class CityWineryPageData(EventListContainer[CityWineryEvent]):
    """Raw event data fetched from the City Winery API."""

    event_list: list[CityWineryEvent]
