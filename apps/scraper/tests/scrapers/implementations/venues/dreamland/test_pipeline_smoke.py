"""Pipeline smoke tests for the Nantucket Dreamland Live Comedy scraper (TASK-3152).

Covers archive-card parsing (title / date / room / ticket+detail URLs), the
abbreviated- and full-month date formats, and the full get_data → PageData path.
The archive is comedy-only by the venue's own taxonomy, so there is no
comedy_filter to exercise.
"""

from unittest.mock import AsyncMock

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.dreamland.data import DreamlandPageData
from laughtrack.scrapers.implementations.venues.dreamland.extractor import DreamlandExtractor
from laughtrack.scrapers.implementations.venues.dreamland.scraper import DreamlandScraper

SOURCE_URL = "https://www.nantucketdreamland.org/event-type/live-comedy"

_FIXTURE = """
<div class="agile-feed agile-feed-archive"><div class="event-feed-wrap">
<figure class="event-image-wrap"><img src="x.jpg" /></figure>
<div class="ticket-wrap"><div class="ticket-text">
  <a href="https://www.nantucketdreamland.org/events/dreamland-comedy-t-j-miller" title="Dreamland Comedy: T.J. Miller"><h3 class="show-title">Dreamland Comedy: T.J. Miller</h3></a>
  <p><strong>Next Show:</strong>
  <a class="agile-link next-event" href="https://tickets.nantucketdreamland.org/websales/pages/ticketsearchcriteria.aspx?evtinfo=1013762" target="agileEmbed">Jul 3, 2026 at 8:00 pm in the Main Theater</a></p>
</div></div>
<figure class="event-image-wrap"><img src="y.jpg" /></figure>
<div class="ticket-wrap"><div class="ticket-text">
  <a href="https://www.nantucketdreamland.org/events/dreamland-comedy-brian-glowacki" title="Dreamland Comedy: Brian Glowacki"><h3 class="show-title">Dreamland Comedy: Brian Glowacki</h3></a>
  <p><strong>Next Show:</strong>
  <a class="agile-link next-event" href="https://tickets.nantucketdreamland.org/websales/pages/ticketsearchcriteria.aspx?evtinfo=2002" target="agileEmbed">July 31, 2026 at 7:30 pm in the Studio Theater</a></p>
</div></div>
</div>
"""


def _club() -> Club:
    _c = Club(id=555, name="Nantucket Dreamland", address='17 South Water St', website='http://nantucketdreamland.org/', popularity=0, zip_code='02554', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='dreamland', source_url=SOURCE_URL)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def test_extractor_parses_cards():
    events = DreamlandExtractor.extract_events(_FIXTURE)
    assert len(events) == 2
    tj = events[0]
    assert tj.title == "Dreamland Comedy: T.J. Miller"
    assert (tj.date.year, tj.date.month, tj.date.day, tj.date.hour) == (2026, 7, 3, 20)
    assert tj.room == "Main Theater"
    assert "evtinfo=1013762" in tj.ticket_url
    assert tj.show_page_url.endswith("/events/dreamland-comedy-t-j-miller")
    # Second card uses the full-month format ("July 31, 2026").
    brian = events[1]
    assert (brian.date.month, brian.date.day, brian.date.hour, brian.date.minute) == (7, 31, 19, 30)
    assert brian.room == "Studio Theater"


@pytest.mark.asyncio
async def test_get_data_returns_page_data():
    scraper = DreamlandScraper(_club())
    scraper.fetch_html = AsyncMock(return_value=_FIXTURE)

    result = await scraper.get_data(SOURCE_URL)

    assert isinstance(result, DreamlandPageData)
    assert len(result.event_list) == 2


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html():
    scraper = DreamlandScraper(_club())
    scraper.fetch_html = AsyncMock(return_value="")

    assert await scraper.get_data(SOURCE_URL) is None


def test_event_to_show_uses_ticket_and_page_urls():
    events = DreamlandExtractor.extract_events(_FIXTURE)
    show = events[0].to_show(_club())
    assert show is not None
    assert show.name == "Dreamland Comedy: T.J. Miller"
    assert show.show_page_url.endswith("/events/dreamland-comedy-t-j-miller")
    assert show.room == "Main Theater"
    assert len(show.tickets) == 1
