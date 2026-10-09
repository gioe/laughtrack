"""Ann Arbor's explicitly timed official highlights remain incomplete inventory."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.etix.public_ann_arbor import HOME, extract_highlights
from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper
from laughtrack.utilities.domain.show.utils import ShowUtils

HTML = (Path(__file__).parent / "fixtures/ann_arbor_home.html").read_text()
SOURCE = "https://www.etix.com/ticket/v/515/ann-arbor-comedy-showcase"


def scraper():
    club = Club(id=16122, name="Ann Arbor Comedy Showcase", address="212 S 4th Ave",
                website=HOME, popularity=0, zip_code="48104", phone_number="",
                visible=True, timezone="America/Detroit")
    club.active_scraping_source = ScrapingSource(id=7682, club_id=16122, platform="etix",
                                               scraper_key="etix", source_url=SOURCE)
    return EtixScraper(club)


def test_real_feature_multiple_showtimes_and_repeat_identity():
    from laughtrack.scrapers.implementations.api.etix.data import EtixPageData
    events = extract_highlights(HTML)
    assert [e.start_date for e in events] == ["2026-10-08T19:15:00", "2026-10-09T19:15:00",
                                             "2026-10-10T19:15:00", "2026-10-10T21:45:00"]
    assert {e.title for e in events} == {"Jay Stevens"}
    assert {e.ticket_url for e in events} == {"https://www.etix.com/ticket/e/1059733"}
    parser = scraper()
    shows = parser.transformation_pipeline.transform(EtixPageData(event_list=events))
    repeated = parser.transformation_pipeline.transform(EtixPageData(event_list=extract_highlights(HTML)))
    assert len(shows) == len(ShowUtils.deduplicate_shows(shows + repeated)) == 4
    assert shows[-1].date.isoformat() == "2026-10-10T21:45:00-04:00"
    assert all(s.club_id == 16122 and not s.room for s in shows)
    assert all([c.name for c in s.lineup] == ["Jay Stevens"] for s in shows)
    assert all(s.infer_lineup_from_title is False for s in shows)
    assert all(s.tickets[0].purchase_url == "https://www.etix.com/ticket/e/1059733" for s in shows)


def test_performer_requires_own_explicit_biographical_evidence():
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(HTML, "html.parser")
    heading = next(n for n in soup.select("h1") if n.get_text(strip=True) == "Jay Stevens")
    section = heading.find_parent(class_="dmRespCol")
    for paragraph in section.select("p"):
        paragraph.decompose()
    unrelated = "<aside><p>Jay Stevens is a comedian.</p></aside>"
    assert all(e.performer_names == [] for e in extract_highlights(str(soup) + unrelated))
    assert all(e.performer_names == [] for e in extract_highlights(HTML.replace("Comedian Overview", "Event Details")))


def test_generic_etix_keeps_existing_title_inference_default():
    from laughtrack.core.entities.event.etix import EtixEvent
    event = EtixEvent(title="Comedy Showcase", start_date="2026-10-09T19:15:00",
                      time_str="7:15pm", ticket_url="https://www.etix.com/ticket/p/123/example")
    show = event.to_show(scraper().club, enhanced=False)
    assert show.lineup == [] and show.infer_lineup_from_title is True


@pytest.mark.parametrize("old,new", [
    ("stevens26", "stevens"), ("7:15pm", "doors at 7:15pm"),
    ("9:45pm", "25:45pm"), ("October 8th 9th &amp; 10th", "October 9th &amp; 10th"),
    ("www.etix.com/ticket/e/1059733", "evil.example/ticket/e/1059733"),
    ("Jay Stevens", "Gift Cards"), ("Jay Stevens", "Comedy Workshop"),
    ("Jay Stevens", "Happy Hour"),
])
def test_missing_or_conflicting_evidence_fails_closed(old, new):
    assert old in HTML
    assert extract_highlights(HTML.replace(old, new)) == []


def test_feature_is_not_hardcoded_and_unrelated_times_never_substitute():
    from bs4 import BeautifulSoup
    changed = HTML.replace("Jay Stevens", "Example Comic").replace("stevens26", "example27")
    assert extract_highlights(changed)[0].start_date == "2027-10-08T19:15:00"
    soup = BeautifulSoup(HTML, "html.parser")
    for row in soup.select("h4"):
        row.decompose()
    assert extract_highlights(str(soup) + "<footer>Friday 7:15pm Saturday 7:15pm &amp; 9:45pm</footer>") == []


@pytest.mark.asyncio
async def test_native_dispatch_preserves_primary_and_incomplete_diagnostics():
    from laughtrack.foundation.infrastructure.http.diagnostics import ScrapeDiagnostics, bind_diagnostics, reset_diagnostics
    parser = scraper()
    parser._fetch_etix_html = AsyncMock(return_value="DataDome: please enable JS and disable any ad blocker")
    parser.fetch_html_bare = AsyncMock(return_value=HTML)
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        targets = await parser.collect_scraping_targets()
        result = await parser.get_data(targets[0])
    finally:
        reset_diagnostics(token)
    assert len(result.event_list) == 4
    assert parser.club.scraping_url == SOURCE
    assert "venue_id=515" in targets[0]
    parser.fetch_html_bare.assert_awaited_once_with(HOME)
    assert diagnostics.fetches_failed > 0 and diagnostics.scrape_errors


@pytest.mark.asyncio
async def test_healthy_primary_never_requests_highlights():
    parser = scraper()
    parser._fetch_etix_html = AsyncMock(return_value='''<div class="row performance">
    <a class="performance-name" href="/ticket/p/123/example">Example Comic</a>
    <meta itemprop="startDate" content="2026-10-09T19:15:00"/>
    </div>''')
    parser._get_partial_public_data = AsyncMock()
    # The primary parser is independently covered; assert dispatcher routing.
    from laughtrack.core.entities.event.etix import EtixEvent
    from unittest.mock import patch
    event = EtixEvent(title="Example Comic", start_date="2026-10-09T19:15:00",
                      time_str="7:15pm", ticket_url="https://www.etix.com/ticket/p/123/example")
    with patch("laughtrack.scrapers.implementations.api.etix.scraper.EtixExtractor.extract_events", return_value=[event]):
        result = await parser.get_data(SOURCE)
    assert result.event_list == [event]
    parser._get_partial_public_data.assert_not_awaited()
