"""Logan Square Improv Crowdwork scraper."""

import asyncio  # noqa: F401 - re-exported for legacy retry-sleep test monkeypatches

from laughtrack.scrapers.implementations.api.crowdwork.scraper import GenericCrowdworkScraper
from laughtrack.scrapers.implementations.api.crowdwork.utils import RAILS_TO_IANA
from .data import LoganSquareImprovPageData
from .transformer import LoganSquareImprovTransformer


class LoganSquareImprovScraper(GenericCrowdworkScraper):
    """Scraper for Logan Square Improv via Crowdwork/Fourthwall API."""

    key = "logan_square_improv"
    page_data_cls = LoganSquareImprovPageData
    transformer_cls = LoganSquareImprovTransformer
    default_timezone = "America/Chicago"
    rails_to_iana = RAILS_TO_IANA
