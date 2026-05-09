"""iO Theater Chicago Crowdwork scraper."""

import asyncio  # noqa: F401 - re-exported for legacy retry-sleep test monkeypatches

from laughtrack.scrapers.implementations.api.crowdwork.scraper import GenericCrowdworkScraper
from laughtrack.scrapers.implementations.api.crowdwork.utils import RAILS_TO_IANA
from .data import IOTheaterPageData
from .transformer import IOTheaterTransformer


class IOTheaterScraper(GenericCrowdworkScraper):
    """Scraper for iO Theater Chicago via Crowdwork/Fourthwall API."""

    key = "io_theater"
    page_data_cls = IOTheaterPageData
    transformer_cls = IOTheaterTransformer
    default_timezone = "America/Chicago"
    rails_to_iana = RAILS_TO_IANA
