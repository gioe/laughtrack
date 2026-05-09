"""
Public-card smoke test for The Stand NYC.

The dedicated TheStandNYCScraper was deleted once scraping_sources.club_id=5
was repointed to scraper_key='tixr_public_card' (TASK-2015), so The Stand now
flows through the generic TixrPublicCardScraper. This test pins the
public-card path against The Stand's Bootstrap-style /shows markup to
guarantee detail-page fetches (the DataDome-blocked endpoint) stay off the
critical path.
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.tixr.data import TixrPageData
from laughtrack.scrapers.implementations.api.tixr.scraper import TixrPublicCardScraper


SCRAPING_URL = "thestandnyc.com"
PUBLIC_SHOWS_URL = "https://thestandnyc.com/shows"
STAND_TIXR_URL = "https://www.tixr.com/groups/thestandnyc/events/the-stand-presents-josh-ocean-thomas--187376"


def _club() -> Club:
    _c = Club(id=99, name='The Stand', address='', website='https://thestandnyc.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _stand_public_card_html() -> str:
    """Minimal Bootstrap-style show row matching thestandnyc.com/shows.

    The h2.showtitle href encodes the full ISO datetime in its slug; the
    a.btn-stand href carries the Tixr ticket URL. Sold-out shows replace
    the buy link with a span.btn-outline-danger and should be skipped.
    """
    return """<html><body>
<div class="row show_row ">
  <h2 class="showtitle"><a href="https://thestandnyc.com//shows/show/12964/2026-05-08-190000-the-stand-presents-josh-ocean-thomas">The Stand Presents: Josh Ocean Thomas</a></h2>
  <h3 class="showinfo"><span class="show_date">May 8</span> | <span class="show_date">7:00 PM</span> <span class="list-show-room">Upstairs</span></h3>
  <div class="text-uppercase">
    <a href="https://www.tixr.com/groups/thestandnyc/events/the-stand-presents-josh-ocean-thomas--187376" class="btn btn-stand">Buy Tickets</a>
  </div>
</div>
<div class="row show_row ">
  <h2 class="showtitle"><a href="/shows/show/12965/2026-05-08-200000-the-stand-presents-kyle-dunnigan">The Stand Presents: Kyle Dunnigan</a></h2>
  <h3 class="showinfo"><span class="show_date">May 8</span> | <span class="show_date">8:00 PM</span> <span class="list-show-room">Main Room</span></h3>
  <div class="text-uppercase">
    <span class="btn btn-outline-danger">Sold Out</span>
  </div>
</div>
</body></html>"""


@pytest.mark.asyncio
async def test_public_card_scraper_avoids_blocked_detail_fetch(monkeypatch):
    """
    The Stand's /shows page exposes title, ISO datetime in the title-link
    slug, and a Tixr ticket URL — so the public-card scraper builds Show
    objects from the page instead of calling the DataDome-blocked Tixr
    detail endpoint. Sold-out cards have no Tixr URL and are skipped.
    """
    scraper = TixrPublicCardScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(side_effect=AssertionError("Tixr detail pages should not be fetched")),
    )

    result = await scraper.get_data(PUBLIC_SHOWS_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 1
    event = result.event_list[0]
    assert event.title == "The Stand Presents: Josh Ocean Thomas"
    assert event.source_url == STAND_TIXR_URL
    assert event.show.show_page_url == STAND_TIXR_URL
    assert event.show.tickets[0].purchase_url == STAND_TIXR_URL
    assert event.show.tickets[0].sold_out is False
    assert event.show.room == "Upstairs"
    # Title slug "2026-05-08-190000" → 2026-05-08 19:00 in venue timezone (America/New_York).
    assert event.show.date.year == 2026
    assert event.show.date.month == 5
    assert event.show.date.day == 8
    assert event.show.date.hour == 19
    assert event.show.date.minute == 0
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()
