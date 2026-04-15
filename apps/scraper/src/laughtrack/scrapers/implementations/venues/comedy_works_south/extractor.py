"""Comedy Works South data extraction utilities."""

from laughtrack.scrapers.implementations.venues.comedy_works_common.extractor import (
    ComedyWorksBaseExtractor,
)


class ComedyWorksSouthExtractor(ComedyWorksBaseExtractor):
    """Extractor scoped to the South location (CSS class 'club-south')."""

    location_css_class = "club-south"
