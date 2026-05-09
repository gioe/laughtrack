"""Rails Comedy Crowdwork scraper."""

import asyncio  # noqa: F401 - re-exported for legacy retry-sleep test monkeypatches

from laughtrack.scrapers.implementations.api.crowdwork.scraper import GenericCrowdworkScraper
from laughtrack.scrapers.implementations.api.crowdwork.utils import RAILS_TO_IANA
from .data import RailsComedyPageData
from .transformer import RailsComedyTransformer


class RailsComedyScraper(GenericCrowdworkScraper):
    """Scraper for Rails Comedy via Crowdwork/Fourthwall API."""

    key = "rails_comedy"
    page_data_cls = RailsComedyPageData
    transformer_cls = RailsComedyTransformer
    default_timezone = "America/New_York"
    rails_to_iana = RAILS_TO_IANA
