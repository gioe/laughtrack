import pathlib

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.broadway_comedy_club.extractor import BroadwayEventExtractor

FIXTURE = pathlib.Path(__file__).parents[4] / "fixtures" / "html" / "broadway_listing_sample.html"


def test_extract_events_uses_room_from_card_footer():
    html = FIXTURE.read_text(encoding="utf-8")

    events = BroadwayEventExtractor.extract_events(html)
    assert len(events) == 1

    ev = events[0]
    assert ev.id == "18195"
    assert ev.room == "Main Room"
    # externalLink should have been set from the card href when empty
    assert ev.externalLink and "/shows/" in ev.externalLink


def test_to_show_prefers_extracted_room_over_venue():
    html = FIXTURE.read_text(encoding="utf-8")
    events = BroadwayEventExtractor.extract_events(html)
    ev = events[0]

    club = Club(id=1, name='Broadway Comedy Club', address='', website='', popularity=0, zip_code='', phone_number='', visible=True)
    club.active_scraping_source = ScrapingSource(id=1, club_id=club.id, platform='custom', scraper_key='', source_url='https://www.broadwaycomedyclub.com', external_id=None)
    club.scraping_sources = [club.active_scraping_source]

    show = ev.to_show(club, enhanced=False)
    assert show is not None
    assert show.room == "Main Room"
