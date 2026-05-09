"""
Comedy Works South scraper implementation.

Comedy Works South (5345 Landmark Pl, Greenwood Village CO) shares the same
comedyworks.com Rails ticketing platform as Comedy Works Downtown. The site
lists shows for both locations; this scraper filters for South only.

Pipeline:
  1. collect_scraping_targets() -> unique comedian slugs from /events?south=1
  2. get_data(slug)             -> fetch /comedians/{slug}, extract showtimes
  3. transformation_pipeline    -> ComedyWorksDowntownEvent.to_show() -> Show objects
"""

from .data import ComedyWorksSouthPageData
from .extractor import ComedyWorksSouthExtractor
from .transformer import ComedyWorksSouthTransformer
from ..comedy_works_common.scraper import (
    ComedyWorksLocationConfig,
    ComedyWorksLocationScraper,
)


class ComedyWorksSouthScraper(ComedyWorksLocationScraper):
    """
    Scraper for Comedy Works South (Greenwood Village, CO).

    Two-phase scrape:
    1. Fetch /events?south=1 to discover unique comedian slugs
    2. For each slug, fetch /comedians/{slug} to extract all South showtimes
       with full pricing and sold-out status
    """

    key = "comedy_works_south"
    config = ComedyWorksLocationConfig(
        query_value="south=1",
        location_label="South",
        extractor_cls=ComedyWorksSouthExtractor,
        page_data_cls=ComedyWorksSouthPageData,
        transformer_cls=ComedyWorksSouthTransformer,
    )
