"""Hartford's captured public calendar: series, DST, exclusions and identity."""

from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper
from laughtrack.utilities.domain.show.utils import ShowUtils

URL = "https://hartford.funnybone.com/shows/"
EXCLUSIONS = [
    "Hocus Pocus Tribute Drag Brunch",
    "Dolly Parton Hard Candy Christmas Tribute Drag Brunch",
]


@pytest.fixture
def scraper(monkeypatch):
    club = Club(
        id=4904, name="Hartford Funny Bone", address="194 Buckland Hills Drive, Manchester, CT",
        website="https://hartford.funnybone.com", popularity=0, zip_code="06042",
        phone_number="", visible=True, timezone="America/New_York",
    )
    source = ScrapingSource(
        club_id=4904, platform="etix", scraper_key="etix", source_url=URL,
        metadata={"excluded_event_titles": EXCLUSIONS},
    )
    club.active_scraping_source = source
    club.scraping_sources = [source]
    scraper = EtixScraper(club)
    html = (Path(__file__).parent / "fixtures/hartford_funny_bone.html").read_text()
    # The live, fully populated calendar also loads this normal vendor tag.
    html = '<script src="https://js.datadome.co/tags.js" async></script>' + html

    async def fetch(url):
        assert url == URL
        return html

    monkeypatch.setattr(scraper, "fetch_html_bare", fetch)
    return scraper


@pytest.mark.asyncio
async def test_hartford_direct_source_series_and_exclusions(scraper):
    assert await scraper.collect_scraping_targets() == [URL]
    data = await scraper.get_data(URL)
    assert len(data.event_list) == 12
    assert not any(event.title in EXCLUSIONS for event in data.event_list)
    assert len({event.ticket_url for event in data.event_list}) == 12
    jeff = next(e for e in data.event_list if e.title.startswith("Jeff Allen"))
    assert jeff.start_date == "2026-10-29T19:00:00"
    assert "/ticket/p/95937184/" in jeff.ticket_url
    assert jeff.ticket_price == 42


@pytest.mark.asyncio
async def test_hartford_multiple_showtimes_dst_and_repeat_identity(scraper):
    first = await scraper.get_data(URL)
    second = await scraper.get_data(URL)
    shows = scraper.transformation_pipeline.transform(first)
    repeated = scraper.transformation_pipeline.transform(second)
    assert len(shows) == 12
    assert len(ShowUtils.deduplicate_shows(shows + repeated)) == 12
    assert all(show.club_id == 4904 and not show.room for show in shows)
    pat = [s for s in shows if s.name == "Ms. Pat"]
    assert [s.date.isoformat() for s in pat] == [
        "2026-10-09T19:00:00-04:00", "2026-10-09T21:30:00-04:00",
        "2026-10-10T18:30:00-04:00", "2026-10-10T21:00:00-04:00",
    ]
    assert len({s.tickets[0].purchase_url for s in pat}) == 4
    winter = [s for s in shows if s.name == "Karlous Miller"]
    assert winter[0].date.isoformat() == "2027-01-08T19:00:00-05:00"
    assert all(s.show_page_url.startswith("https://hartford.funnybone.com/") for s in shows)


@pytest.mark.parametrize("challenge", [
    "<html>DataDome: please enable JS and disable any ad blocker</html>",
    '<script src="https://js.datadome.co/tags.js"></script><iframe src="https://geo.captcha-delivery.com/captcha/"></iframe>',
])
def test_hartford_rejects_actual_challenges_even_with_calendar_markup(scraper, challenge):
    from laughtrack.foundation.exceptions.scraping_errors import DataError

    html = (Path(__file__).parent / "fixtures/hartford_funny_bone.html").read_text()
    with pytest.raises(DataError, match="blocked"):
        scraper._require_source_html(challenge + html, URL)
