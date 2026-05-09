"""The Backline Comedy Theatre Crowdwork scraper."""

import asyncio  # noqa: F401 - re-exported for legacy retry-sleep test monkeypatches

from laughtrack.scrapers.implementations.api.crowdwork.scraper import GenericCrowdworkScraper
from laughtrack.scrapers.implementations.api.crowdwork.utils import RAILS_TO_IANA
from .data import TheBacklinePageData
from .transformer import TheBacklineTransformer


class TheBacklineScraper(GenericCrowdworkScraper):
    """Scraper for The Backline Comedy Theatre via Crowdwork/Fourthwall API."""

    key = "the_backline"
    page_data_cls = TheBacklinePageData
    transformer_cls = TheBacklineTransformer
    default_timezone = "America/Chicago"
    rails_to_iana = RAILS_TO_IANA
