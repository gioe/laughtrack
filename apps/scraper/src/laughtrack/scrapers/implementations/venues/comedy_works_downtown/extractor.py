"""Comedy Works Downtown data extraction utilities."""

from laughtrack.scrapers.implementations.venues.comedy_works_common.extractor import (
    ComedyWorksBaseExtractor,
)


class ComedyWorksDowntownExtractor(ComedyWorksBaseExtractor):
    """Extractor scoped to the Downtown location (CSS class 'club-downtown')."""

    location_css_class = "club-downtown"
