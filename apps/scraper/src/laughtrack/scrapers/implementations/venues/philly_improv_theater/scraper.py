"""Philly Improv Theater (PHIT) Crowdwork scraper."""

import asyncio  # noqa: F401 - re-exported for legacy retry-sleep test monkeypatches

from laughtrack.scrapers.implementations.api.crowdwork.scraper import GenericCrowdworkScraper
from .data import PhillyImprovPageData
from .transformer import PhillyImprovTransformer


class PhillyImprovTheaterScraper(GenericCrowdworkScraper):
    """Scraper for Philly Improv Theater (PHIT) via Crowdwork/Fourthwall API."""

    key = "philly_improv_theater"
    page_data_cls = PhillyImprovPageData
    transformer_cls = PhillyImprovTransformer
    default_timezone = "America/New_York"
