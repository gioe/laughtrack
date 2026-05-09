"""
Comedy Works Downtown scraper implementation.

Comedy Works Downtown (1226 15th St, Denver CO) sells tickets exclusively
through their own Rails site at comedyworks.com. The site lists shows for
both Downtown and South locations; this scraper filters for Downtown only.

Pipeline:
  1. collect_scraping_targets() → unique comedian slugs from /events?downtown=1
  2. get_data(slug)             → fetch /comedians/{slug}, extract showtimes
  3. transformation_pipeline    → ComedyWorksDowntownEvent.to_show() → Show objects
"""

from .data import ComedyWorksDowntownPageData
from .extractor import ComedyWorksDowntownExtractor
from .transformer import ComedyWorksDowntownTransformer
from ..comedy_works_common.scraper import (
    ComedyWorksLocationConfig,
    ComedyWorksLocationScraper,
)


class ComedyWorksDowntownScraper(ComedyWorksLocationScraper):
    """
    Scraper for Comedy Works Downtown (Denver, CO).

    Two-phase scrape:
    1. Fetch /events?downtown=1 to discover unique comedian slugs
    2. For each slug, fetch /comedians/{slug} to extract all Downtown showtimes
       with full pricing and sold-out status
    """

    key = "comedy_works_downtown"
    config = ComedyWorksLocationConfig(
        query_value="downtown=1",
        location_label="Downtown",
        extractor_cls=ComedyWorksDowntownExtractor,
        page_data_cls=ComedyWorksDowntownPageData,
        transformer_cls=ComedyWorksDowntownTransformer,
    )
