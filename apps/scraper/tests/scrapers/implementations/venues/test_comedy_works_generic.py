"""Generic Comedy Works scraper behavior tests."""

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.comedy_works_common.extractor import (
    ComedyWorksBaseExtractor,
)
from laughtrack.scrapers.implementations.venues.comedy_works_common.scraper import (
    ComedyWorksLocationConfig,
    ComedyWorksLocationScraper,
)
from laughtrack.scrapers.implementations.venues.comedy_works_downtown.data import (
    ComedyWorksDowntownPageData,
)
from laughtrack.scrapers.implementations.venues.comedy_works_downtown.transformer import (
    ComedyWorksDowntownTransformer,
)


def _club() -> Club:
    club = Club(
        id=300,
        name="Comedy Works Test",
        address="1226 15th St",
        website="https://www.comedyworks.com",
        popularity=0,
        zip_code="80202",
        phone_number="",
        visible=True,
        timezone="America/Denver",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="",
        source_url="https://www.comedyworks.com/events?test=1",
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


class TestLocationExtractor(ComedyWorksBaseExtractor):
    location_css_class = "club-test"


class TestLocationScraper(ComedyWorksLocationScraper):
    key = "comedy_works_test"
    config = ComedyWorksLocationConfig(
        query_value="test=1",
        location_label="Test",
        extractor_cls=TestLocationExtractor,
        page_data_cls=ComedyWorksDowntownPageData,
        transformer_cls=ComedyWorksDowntownTransformer,
    )

    def __init__(self):
        super().__init__(_club())
        self.fetched_urls = []

    async def fetch_html(self, url: str, **kwargs):
        self.fetched_urls.append(url)
        if url.endswith("/events?test=1"):
            return """
            <ul>
              <li class="comedian-box">
                <h2 class="comedian-box-title">
                  <a href="/comedians/test-comic">Test Comic</a>
                </h2>
              </li>
            </ul>
            """
        return """
        <div class="comedian-intro"><h1>Test Comic</h1></div>
        <div class="ticket-location">
          <p class="club-title club-other">Other Location</p>
        </div>
        <ul class="show-times">
          <li><p class="show-day">Thursday, Jan 1 2099  7:15PM</p></li>
        </ul>
        <div class="ticket-location">
          <p class="club-title club-test">Test Location</p>
        </div>
        <ul class="show-times">
          <li><p class="show-day">Friday, Jan 2 2099  9:30PM</p></li>
        </ul>
        """


async def test_discovers_location_specific_slugs_from_config():
    scraper = TestLocationScraper()

    slugs = await scraper.collect_scraping_targets()

    assert slugs == ["test-comic"]
    assert scraper.fetched_urls == ["https://www.comedyworks.com/events?test=1"]


async def test_filters_detail_showtimes_by_location_class():
    scraper = TestLocationScraper()

    page_data = await scraper.get_data("test-comic")

    assert page_data is not None
    assert [event.showtime.datetime_str for event in page_data.event_list] == [
        "Friday, Jan 2 2099  9:30PM"
    ]
    assert scraper.fetched_urls == ["https://www.comedyworks.com/comedians/test-comic"]
