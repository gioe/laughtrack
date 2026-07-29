"""
Pipeline smoke tests for the generic TixrScraper.

Exercises TixrExtractor, collect_scraping_targets(), and get_data() against
mocked HTML and a mocked TixrClient. Verifies that both short-form and
long-form Tixr URLs are extracted and resolved to TixrEvents.
"""

import html
import importlib.util
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.scrapers.implementations.api.tixr.scraper import TixrPublicCardScraper, TixrScraper
from laughtrack.scrapers.implementations.api.tixr.data import TixrPageData
from laughtrack.scrapers.implementations.api.tixr.extractor import TixrExtractor

CALENDAR_URL = "https://www.hahacomedyclub.com/calendar"
IMPROV_ASYLUM_TIXR_URL = "https://www.tixr.com/groups/improvasylum"
COMIC_STRIP_EDMONTON_PIXL_API_URL = "https://www.pixlcalendar.com/api/events/comic-strip-edmonton"
HOUSE_OF_COMEDY_BC_PIXL_API_URL = "https://www.pixlcalendar.com/api/events/house-of-comedy-bc"
STAND_SCRAPING_URL = "thestandnyc.com"
STAND_PUBLIC_SHOWS_URL = "https://thestandnyc.com/shows"
STAND_TIXR_URL = "https://www.tixr.com/groups/thestandnyc/events/the-stand-presents-josh-ocean-thomas--187376"
STAND_FREE_TIXR_URL = "https://www.tixr.com/groups/thestandnyc/events/free-comedy-night--187377"
STAND_SOLD_OUT_URL = (
    "https://thestandnyc.com/shows/show/12965/"
    "2026-05-08-200000-the-stand-presents-kyle-dunnigan"
)
GOCF_HALIFAX_URL = "https://www.greatoutdoorscomedyfestival.com/cities/halifax"
GOCF_MATT_RIFE_TIXR_URL = (
    "https://www.tixr.com/groups/gocf/events/"
    "great-outdoors-comedy-festival-2026-halifax-152718?sort=RECOMMENDED&COL=13492&A=L"
)
GOCF_HALIFAX_TIXR_URL = (
    "https://www.tixr.com/groups/gocf/events/"
    "great-outdoors-comedy-festival-2026-halifax-152718?sort=RECOMMENDED&COL=16248&A=L"
)


def _club(scraping_url: str = CALENDAR_URL) -> Club:
    _c = Club(id=999, name='Test Tixr Venue', address='123 Main St', website='https://example.com', popularity=0, zip_code='90001', phone_number='', visible=True, timezone='America/Los_Angeles')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=scraping_url, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _improv_asylum_club() -> Club:
    _c = Club(id=141, name='Improv Asylum', address='216 Hanover St', website='https://improvasylum.com', popularity=0, zip_code='02113', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='tixr', scraper_key='tixr', source_url=IMPROV_ASYLUM_TIXR_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _comic_strip_edmonton_club() -> Club:
    _c = Club(
        id=2488,
        name="The Comic Strip West Edmonton Mall",
        address="8882 170 St NW",
        website="https://wem.thecomicstrip.ca",
        popularity=0,
        zip_code="T5T 4J2",
        phone_number="",
        visible=True,
        timezone="America/Edmonton",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="custom",
        scraper_key="tixr",
        source_url=COMIC_STRIP_EDMONTON_PIXL_API_URL,
        external_id=None,
        metadata={"pixl_calendar_api_url": COMIC_STRIP_EDMONTON_PIXL_API_URL},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _house_of_comedy_bc_club() -> Club:
    _c = Club(
        id=2357,
        name="House of Comedy British Columbia",
        address="530 Columbia St",
        website="https://bc.houseofcomedy.net/",
        popularity=0,
        zip_code="V3L 1B1",
        phone_number="",
        visible=True,
        timezone="America/Vancouver",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="custom",
        scraper_key="tixr",
        source_url=HOUSE_OF_COMEDY_BC_PIXL_API_URL,
        external_id=None,
        metadata={"pixl_calendar_api_url": HOUSE_OF_COMEDY_BC_PIXL_API_URL},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _tixr_group_api_club() -> Club:
    _c = Club(id=171, name='Laugh Factory Covina', address='104 N Citrus Ave', website='https://www.laughfactory.com/covina', popularity=0, zip_code='91723', phone_number='', visible=True, timezone='America/Los_Angeles')
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform='tixr',
        scraper_key='tixr',
        source_url='https://www.tixr.com/groups/laughfactorycovina',
        external_id=None,
        metadata={"tixr_group_id": 1613},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _rose_city_group_api_club() -> Club:
    _c = Club(id=1023, name='Rose City Comedy', address='7428 Old Jacksonville Hwy', website='https://rosecitycomedy.club', popularity=0, zip_code='75703', phone_number='', visible=True, timezone='America/Chicago')
    _c.active_scraping_source = ScrapingSource(
        id=438,
        club_id=_c.id,
        platform='tixr',
        scraper_key='tixr',
        source_url='https://rosecitycomedy.club',
        external_id=None,
        metadata={
            "tixr_group_slug": "rosecitycomedy",
            "tixr_group_events_api_fallback": True,
        },
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _stand_club() -> Club:
    _c = Club(id=99, name='The Stand', address='', website='https://thestandnyc.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=STAND_SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _gocf_halifax_club() -> Club:
    _c = Club(
        id=998,
        name="Great Outdoors Comedy Festival Halifax",
        address="Garrison Grounds, Halifax, NS, Canada",
        website=GOCF_HALIFAX_URL,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/Halifax",
        city="Halifax",
        state="NS",
        status="active",
        club_type="festival",
    )
    _c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=_c.id,
        platform="tixr",
        scraper_key="tixr_public_card",
        source_url=GOCF_HALIFAX_URL,
        external_id=None,
        metadata={"gocf_city": "Halifax"},
    )
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_tixr_event(event_id: str, title: str) -> TixrEvent:
    show = Show(
        name=title,
        club_id=999,
        date=datetime(2026, 4, 1, 20, 0, tzinfo=timezone.utc),
        show_page_url=f"https://tixr.com/e/{event_id}",
        lineup=[],
        tickets=[
            Ticket(
                price=0.0,
                purchase_url=f"https://tixr.com/e/{event_id}",
                sold_out=False,
                type="General Admission",
            )
        ],
        supplied_tags=["event"],
        description=None,
        timezone=None,
        room="",
    )
    return TixrEvent.from_tixr_show(
        show=show, source_url=f"https://tixr.com/e/{event_id}", event_id=event_id
    )


def _calendar_html_short(tixr_ids: list) -> str:
    """Calendar page with short-form tixr.com/e/{id} links."""
    links = "".join(
        f'<a href="https://tixr.com/e/{id}" class="buy-tickets-btn">Buy Tickets</a>'
        for id in tixr_ids
    )
    return f"<html><body><div class='calendar'>{links}</div></body></html>"


def _calendar_html_long(slugs: list) -> str:
    """Calendar page with long-form tixr.com/groups/*/events/* links."""
    links = "".join(
        f'<a href="{slug}">Buy Tickets</a>' for slug in slugs
    )
    return f"<html><body><div class='calendar'>{links}</div></body></html>"


def _calendar_html_subdomain(group: str, event_slugs: list) -> str:
    """Calendar page with subdomain-form {group}.tixr.com/{slug} links."""
    links = "".join(
        f'<a href="https://{group}.tixr.com/{slug}">Buy Tickets</a>'
        for slug in event_slugs
    )
    return f"<html><body><div class='calendar'>{links}</div></body></html>"


def _calendar_html_with_more_shows(next_href: str, event_ids: list[str]) -> str:
    links = "".join(
        f'<a href="https://tixr.com/e/{event_id}" class="buy-tickets-btn">Buy Tickets</a>'
        for event_id in event_ids
    )
    return f"""
    <html><body>
    <div class='calendar'>{links}</div>
    <a class="btn btn-outline-light loading-btn" href="{next_href}">More Shows</a>
    </body></html>
    """


def _improv_asylum_pixl_response() -> dict:
    return {
        "events": [
            {
                "id": "d3b148b6-0c3c-4f11-86fa-ef5c6a24c800",
                "title": "Improv Asylum&#39;s Main Stage Show",
                "description": "Fast-paced improv",
                "start": "2026-05-08T23:00:00.000Z",
                "end": "2026-05-09T00:30:00.000Z",
                "price": 30,
                "venue": "Improv Asylum",
                "ticketUrl": "https://www.tixr.com/groups/improvasylum/events/improv-asylum-s-main-stage-show-169028",
                "status": "available",
                "timezone": "America/New_York",
                "sales": [
                    {
                        "id": 1852654,
                        "name": "General Admission",
                        "currentPrice": 33.54,
                        "state": "OPEN",
                    },
                    {
                        "id": 1852658,
                        "name": "Premium",
                        "currentPrice": 37.18,
                        "state": "OPEN",
                    },
                ],
            }
        ]
    }


def _comic_strip_edmonton_pixl_response() -> dict:
    return {
        "events": [
            {
                "id": "1d8a36d3-f9d8-4ef6-9f4f-d27adfd273d2",
                "title": "Sean Lecomber",
                "description": "Headline comedy at West Edmonton Mall",
                "start": "2026-06-13T03:30:00.000Z",
                "end": "2026-06-13T05:00:00.000Z",
                "price": 19.95,
                "venue": "The Comic Strip",
                "ticketUrl": "https://www.tixr.com/groups/comicstripedmonton/events/sean-lecomber-185406",
                "status": "available",
                "timezone": "America/Edmonton",
                "sales": [
                    {
                        "id": 200001,
                        "name": "General Admission",
                        "currentPrice": 22.95,
                        "state": "OPEN",
                    },
                    {
                        "id": 200002,
                        "name": "VIP",
                        "currentPrice": 32.95,
                        "state": "SOLD_OUT",
                    },
                ],
            }
        ]
    }


def _house_of_comedy_bc_pixl_response() -> dict:
    return {
        "events": [
            {
                "id": "8cb1428b-a962-4eaa-922f-420b80b461a5",
                "title": "Drew Behm",
                "description": "Headline comedy in New Westminster",
                "start": "2026-07-03T02:30:00.000Z",
                "end": "2026-07-03T04:00:00.000Z",
                "price": 18,
                "venue": "House of Comedy BC - Main Room",
                "ticketUrl": "https://www.tixr.com/groups/comicstripbc/events/drew-behm-188517",
                "status": "available",
                "timezone": "America/Los_Angeles",
                "sales": [
                    {
                        "id": 2145988,
                        "name": "General Admission",
                        "currentPrice": 18,
                        "state": "OPEN",
                    },
                    {
                        "id": 2145989,
                        "name": "Preferred Seating",
                        "currentPrice": 25,
                        "state": "OPEN",
                    },
                ],
            }
        ]
    }


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
  <h4 class="lineup-head d-none d-sm-block pt-0">The Lineup</h4>
  <div class="row gx-3 d-none d-sm-flex">
    <div><p class="lh-sm pb-o"><small>Stephon Bishop</small></p></div>
    <div><p class="lh-sm pb-o"><small>Ashley King</small></p></div>
    <div><p class="lh-sm pb-o"><small>TBA</small></p></div>
  </div>
  <h4 class="lineup-head d-sm-none mt-0">The Lineup</h4>
  <div class="swiffy-slider comic-slider d-sm-none">
    <ul class="slider-container">
      <li><p class="lh-sm pb-o"><small>Stephon Bishop</small></p></li>
      <li><p class="lh-sm pb-o"><small>Ashley King</small></p></li>
      <li><p class="lh-sm pb-o"><small>TBA</small></p></li>
    </ul>
  </div>
  <div class="text-uppercase">
    <div class="show-price">$32.50</div>
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


def _stand_public_card_html_with_free_ticket() -> str:
    return """<html><body>
<div class="row show_row ">
  <h2 class="showtitle"><a href="/shows/show/12966/2026-05-08-213000-free-comedy-night">Free Comedy Night</a></h2>
  <h3 class="showinfo"><span class="show_date">May 8</span> | <span class="show_date">9:30 PM</span> <span class="list-show-room">Upstairs</span></h3>
  <div class="text-uppercase">
    <div class="show-price">FREE!</div>
    <a href="https://www.tixr.com/groups/thestandnyc/events/free-comedy-night--187377" class="btn btn-stand">Buy Tickets</a>
  </div>
</div>
</body></html>"""


def _stand_public_card_html_with_ticket_container_price() -> str:
    return """<html><body>
<div class="row show_row ">
  <h2 class="showtitle"><a href="/shows/show/12968/2026-05-23-170000-laughing-buddha-comedy">Laughing Buddha Comedy</a></h2>
  <h3 class="showinfo"><span class="show_date">May 23</span> | <span class="show_date">5:00 PM</span> <span class="list-show-room-new">Upstairs</span></h3>
  <div class="col-12 col-sm-9 offset-sm-3 col-md-2 offset-md-0 ticket">
    $30.00
    <div class="text-uppercase d-grid d-block gap-2">More Info</div>
    <div class="text-uppercase d-grid d-block gap-2">
      <a href="https://www.tixr.com/groups/thestandnyc/events/laughing-buddha-comedy-187320" class="btn btn-stand">Buy Tickets</a>
    </div>
  </div>
</div>
</body></html>"""


def _stand_public_card_html_with_free_title_and_missing_ticket_text() -> str:
    return """<html><body>
<div class="row show_row ">
  <h2 class="showtitle"><a href="/shows/show/12967/2026-05-08-220000-free-comedy-night">Free Comedy Night</a></h2>
  <h3 class="showinfo"><span class="show_date">May 8</span> | <span class="show_date">10:00 PM</span> <span class="list-show-room">Upstairs</span></h3>
  <div class="text-uppercase">
    <a href="https://www.tixr.com/groups/thestandnyc/events/free-comedy-night--187378" class="btn btn-stand">Buy Tickets</a>
  </div>
</div>
</body></html>"""


def _stand_public_card_html_without_action() -> str:
    return """<html><body>
<div class="row show_row ">
  <h2 class="showtitle"><a href="/shows/show/12969/2026-05-08-230000-coming-soon">Coming Soon</a></h2>
  <h3 class="showinfo"><span class="show_date">May 8</span> | <span class="show_date">11:00 PM</span> <span class="list-show-room">Upstairs</span></h3>
  <div class="text-uppercase">
    <span class="btn btn-outline-secondary">Coming Soon</span>
  </div>
</div>
</body></html>"""


def _gocf_public_card_html() -> str:
    return f"""
<html><body>
  <div class="show-card-content fade-in stagger">
    <div class="w-layout-hflex pill-wrap show-card-pill-wrap">
      <div class="pill yellow-2 show-card-pill">Aug 6, 2026 7:30 PM</div>
      <div class="pill yellow-2 show-card-pill">Halifax</div>
    </div>
    <div class="w-dyn-list"><div role="list" class="w-dyn-items">
      <div role="listitem" class="w-dyn-item">
        <h2 class="secondary-heading comedian-name light">Matt Rife</h2>
      </div>
    </div></div>
    <div class="w-layout-hflex button-flex">
      <a href="{GOCF_MATT_RIFE_TIXR_URL}" class="btn w-button">Get tickets</a>
      <a href="/shows/halifax-august-6---matt-rife" class="btn outline w-button">learn more</a>
    </div>
  </div>
  <div class="show-card-content fade-in stagger full">
    <div class="w-layout-hflex pill-wrap show-card-pill-wrap">
      <div class="pill yellow-2 show-card-pill">Aug 8, 2026 7:30 PM</div>
      <a href="/shows/halifax-august-8---andrew-schulz-lucas-zelnick-kam-patterson-mark-gagnon"
         class="pill yellow-3 show-card-pill">Halifax</a>
    </div>
    <div class="w-dyn-list"><div role="list" class="w-dyn-items">
      <div role="listitem" class="w-dyn-item">
        <h2 class="secondary-heading sm light">Andrew Schulz</h2>
      </div>
    </div></div>
    <div class="w-dyn-list"><div role="list" class="w-dyn-items">
      <div role="listitem" class="w-dyn-item">
        <h3 class="tertiary-heading light no-marg">Lucas Zelnick</h3>
      </div>
      <div role="listitem" class="w-dyn-item">
        <h3 class="tertiary-heading light no-marg">Kam Patterson</h3>
      </div>
      <div role="listitem" class="w-dyn-item">
        <h3 class="tertiary-heading light no-marg">Mark Gagnon</h3>
      </div>
    </div></div>
    <div class="w-layout-hflex button-flex">
      <a href="{GOCF_HALIFAX_TIXR_URL}" class="btn w-button">Get tickets</a>
      <a href="/shows/halifax-august-8---andrew-schulz-lucas-zelnick-kam-patterson-mark-gagnon"
         class="btn outline w-button">learn more</a>
    </div>
  </div>
  <div class="show-card-content fade-in stagger">
    <div class="w-layout-hflex pill-wrap show-card-pill-wrap">
      <div class="pill yellow-2 show-card-pill">Jul 17, 2026 7:30 PM</div>
      <a href="/shows/winnipeg" class="pill yellow-3 show-card-pill">Winnipeg</a>
    </div>
    <h2 class="secondary-heading sm light">Jim Gaffigan</h2>
    <a href="https://www.tixr.com/groups/gocf/events/great-outdoors-comedy-festival-2026-winnipeg-149724"
       class="btn w-button">Get tickets</a>
  </div>
</body></html>
"""


# ---------------------------------------------------------------------------
# TixrExtractor unit tests
# ---------------------------------------------------------------------------


def test_tixr_scraper_keys_are_distinct():
    """Detail-page and venue-owned public-card Tixr paths are queryable separately."""
    assert TixrScraper.key == "tixr"
    assert TixrPublicCardScraper.key == "tixr_public_card"


def test_extractor_finds_short_form_urls():
    """extract_tixr_urls() picks up tixr.com/e/{id} links."""
    html = _calendar_html_short(["177558", "176996", "175370"])
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == [
        "https://tixr.com/e/177558",
        "https://tixr.com/e/176996",
        "https://tixr.com/e/175370",
    ]


def test_extractor_finds_long_form_urls():
    """extract_tixr_urls() picks up tixr.com/groups/*/events/* links."""
    long_url = "https://www.tixr.com/groups/thestand/events/comedy-show-123456"
    html = _calendar_html_long([long_url])
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == [long_url]


def test_extractor_finds_both_forms():
    """extract_tixr_urls() returns both short and long form URLs from the same page."""
    short_url = "https://tixr.com/e/12345"
    long_url = "https://www.tixr.com/groups/venue/events/show-99999"
    html = (
        f'<a href="{short_url}">Short</a>'
        f'<a href="{long_url}">Long</a>'
    )
    urls = TixrExtractor.extract_tixr_urls(html)
    assert short_url in urls
    assert long_url in urls
    assert len(urls) == 2


def test_extractor_deduplicates_urls():
    """extract_tixr_urls() returns each URL only once."""
    html = (
        '<a href="https://tixr.com/e/12345">Buy</a>'
        '<a href="https://tixr.com/e/12345">Buy Again</a>'
        '<a href="https://tixr.com/e/99999">Other</a>'
    )
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == ["https://tixr.com/e/12345", "https://tixr.com/e/99999"]


def test_extractor_deduplicates_cross_form():
    """extract_tixr_urls() returns at most one URL per event when both short and
    long forms for the same event ID appear on the same page."""
    short_url = "https://tixr.com/e/177558"
    long_url = "https://www.tixr.com/groups/venue/events/comedy-show-177558"
    html = (
        f'<a href="{short_url}">Buy Short</a>'
        f'<a href="{long_url}">Buy Long</a>'
    )
    urls = TixrExtractor.extract_tixr_urls(html)
    # Only the short form should appear; the long form is the same event.
    assert urls == [short_url]


def test_extractor_finds_subdomain_urls():
    """extract_tixr_urls() picks up {group}.tixr.com/{slug} subdomain links."""
    html = (
        '<a href="https://rosecitycomedy.tixr.com/toddbarry">Todd Barry</a>'
        '<a href="https://rosecitycomedy.tixr.com/openmic">Open Mic</a>'
    )
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == [
        "https://rosecitycomedy.tixr.com/toddbarry",
        "https://rosecitycomedy.tixr.com/openmic",
    ]


def test_extractor_deduplicates_subdomain_urls():
    """extract_tixr_urls() deduplicates repeated subdomain URLs."""
    html = (
        '<a href="https://rosecitycomedy.tixr.com/toddbarry">Buy</a>'
        '<a href="https://rosecitycomedy.tixr.com/toddbarry">Buy Again</a>'
    )
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == ["https://rosecitycomedy.tixr.com/toddbarry"]


def test_extractor_excludes_www_subdomain():
    """extract_tixr_urls() does not match www.tixr.com as a subdomain URL."""
    html = '<a href="https://www.tixr.com/groups/venue/events/show-123">Buy</a>'
    urls = TixrExtractor.extract_tixr_urls(html)
    # Should be captured as long-form, not subdomain
    assert len(urls) == 1
    assert "groups/venue/events" in urls[0]


def test_extractor_returns_empty_for_no_tixr_urls():
    """extract_tixr_urls() returns [] when no Tixr links are present."""
    html = "<html><body><p>No shows</p></body></html>"
    urls = TixrExtractor.extract_tixr_urls(html)
    assert urls == []


# ---------------------------------------------------------------------------
# TixrExtractor.extract_org_jsonld_event_urls tests
# ---------------------------------------------------------------------------

_ORG_JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Test Venue",
  "events": [
    {"@type": "Event", "url": "https://tixr.com/groups/venue/events/show-a-111"},
    {"@type": "Event", "url": "https://tixr.com/groups/venue/events/show-b-222"}
  ]
}
</script>
</head><body></body></html>
"""


def test_get_event_id_short_form():
    """get_event_id() returns the numeric ID from a short-form Tixr URL."""
    assert TixrExtractor.get_event_id("https://tixr.com/e/177558") == "177558"


def test_get_event_id_long_form():
    """get_event_id() returns the numeric ID from a long-form Tixr URL."""
    assert TixrExtractor.get_event_id("https://www.tixr.com/groups/venue/events/comedy-show-177558") == "177558"


def test_get_event_id_long_form_with_query_params():
    """get_event_id() ignores collection/query params on long-form Tixr URLs."""
    assert TixrExtractor.get_event_id(GOCF_MATT_RIFE_TIXR_URL) == "152718"


def test_get_event_id_double_dash_url():
    """get_event_id() still extracts the trailing numeric ID from double-dash URLs.
    These are client-side rendered and will be filtered out by the Org JSON-LD
    event ID set (not by URL format), so returning an ID here is correct."""
    assert TixrExtractor.get_event_id("https://tixr.com/groups/venue/events/show--182870") == "182870"


def test_get_event_id_returns_none_for_non_tixr_url():
    """get_event_id() returns None when the URL is not a recognized Tixr URL."""
    assert TixrExtractor.get_event_id("https://example.com/shows/123") is None


def test_extract_org_jsonld_event_urls_returns_urls():
    """extract_org_jsonld_event_urls() returns URLs from Organization JSON-LD block."""
    urls = TixrExtractor.extract_org_jsonld_event_urls(_ORG_JSONLD_HTML)
    assert urls == [
        "https://tixr.com/groups/venue/events/show-a-111",
        "https://tixr.com/groups/venue/events/show-b-222",
    ]


def test_extract_org_jsonld_event_urls_returns_empty_when_no_block():
    """extract_org_jsonld_event_urls() returns [] when no Organization JSON-LD exists."""
    html = "<html><body><p>No structured data</p></body></html>"
    urls = TixrExtractor.extract_org_jsonld_event_urls(html)
    assert urls == []


def test_extract_org_jsonld_event_urls_ignores_non_org_blocks():
    """extract_org_jsonld_event_urls() ignores JSON-LD blocks that aren't @type Organization."""
    html = """
    <script type="application/ld+json">{"@type": "Event", "url": "https://tixr.com/e/123"}</script>
    <script type="application/ld+json">{"@type": "WebPage", "name": "Foo"}</script>
    """
    urls = TixrExtractor.extract_org_jsonld_event_urls(html)
    assert urls == []


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_returns_scraping_url(monkeypatch):
    """collect_scraping_targets() returns the club's scraping_url when no pagination exists."""
    scraper = TixrScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _calendar_html_short(["177558"])

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert targets[0].rstrip("/") == CALENDAR_URL.rstrip("/")


@pytest.mark.asyncio
async def test_collect_targets_prepends_https_when_missing(monkeypatch):
    """collect_scraping_targets() adds https:// when scraping_url has no scheme."""
    scraper = TixrScraper(_club(scraping_url="www.example.com/shows"))

    async def fake_fetch_html(self, url, **kwargs):
        return _calendar_html_short(["177558"])

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    targets = await scraper.collect_scraping_targets()
    assert targets[0].startswith("https://")


@pytest.mark.asyncio
async def test_collect_targets_discovers_more_shows_pages(monkeypatch):
    """collect_scraping_targets() follows bounded same-site pagination links."""
    scraper = TixrScraper(_club(scraping_url="https://thestandnyc.com/shows"))
    page_map = {
        "https://thestandnyc.com/shows": _calendar_html_with_more_shows(
            "/shows?page=2", ["177558"]
        ),
        "https://thestandnyc.com/shows?page=2": _calendar_html_short(["176996"]),
    }

    async def fake_fetch_html(self, url, **kwargs):
        return page_map[url]

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)

    targets = await scraper.collect_scraping_targets()

    assert targets == [
        "https://thestandnyc.com/shows",
        "https://thestandnyc.com/shows?page=2",
    ]


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_resolves_short_form_urls(monkeypatch):
    """get_data() extracts short-form Tixr URLs and resolves them to TixrEvents."""
    scraper = TixrScraper(_club())

    html = _calendar_html_short(["177558", "176996"])
    event_a = _make_tixr_event("177558", "Open Mic Night")
    event_b = _make_tixr_event("176996", "Comedy Night")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(
        side_effect=lambda url: event_a if "177558" in url else event_b
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Open Mic Night" in titles
    assert "Comedy Night" in titles


@pytest.mark.asyncio
async def test_get_data_resolves_long_form_urls(monkeypatch):
    """get_data() extracts long-form Tixr URLs and resolves them to TixrEvents."""
    scraper = TixrScraper(_club())
    long_url = "https://www.tixr.com/groups/venue/events/comedy-show-177558"
    html = _calendar_html_long([long_url])
    event = _make_tixr_event("177558", "Comedy Show")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(return_value=event)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Comedy Show"


@pytest.mark.asyncio
async def test_get_data_resolves_subdomain_urls(monkeypatch):
    """get_data() extracts subdomain-form Tixr URLs and resolves them to TixrEvents."""
    scraper = TixrScraper(_club())

    html = _calendar_html_subdomain("rosecitycomedy", ["toddbarry", "openmic"])
    event_a = _make_tixr_event("100001", "Todd Barry")
    event_b = _make_tixr_event("100002", "Open Mic")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(
        side_effect=lambda url: event_a if "toddbarry" in url else event_b
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 2
    titles = {e.title for e in result.event_list}
    assert "Todd Barry" in titles
    assert "Open Mic" in titles


@pytest.mark.asyncio
async def test_public_card_scraper_avoids_blocked_detail_fetch(monkeypatch):
    """
    The Stand's /shows page exposes title, ISO datetime in the title-link
    slug, and a Tixr ticket URL, so the public-card scraper builds Show
    objects from the page instead of calling the DataDome-blocked Tixr
    detail endpoint. Sold-out cards use their venue show URL.
    """
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(side_effect=AssertionError("Tixr detail pages should not be fetched")),
    )

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 2
    event = next(item for item in result.event_list if item.source_url == STAND_TIXR_URL)
    assert event.title == "The Stand Presents: Josh Ocean Thomas"
    assert event.source_url == STAND_TIXR_URL
    assert event.show.show_page_url == STAND_TIXR_URL
    assert event.show.tickets[0].purchase_url == STAND_TIXR_URL
    assert event.show.tickets[0].sold_out is False
    assert event.show.room == "Upstairs"
    assert event.show.date.year == 2026
    assert event.show.date.month == 5
    assert event.show.date.day == 8
    assert event.show.date.hour == 19
    assert event.show.date.minute == 0
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_public_card_scraper_parses_stand_lineup(monkeypatch):
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert result is not None
    assert [comedian.name for comedian in result.event_list[0].show.lineup] == [
        "Stephon Bishop",
        "Ashley King",
    ]


@pytest.mark.asyncio
async def test_public_card_scraper_deduplicates_stand_responsive_lineup(monkeypatch):
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert result is not None
    lineup = result.event_list[0].show.lineup
    assert [comedian.name for comedian in lineup] == ["Stephon Bishop", "Ashley King"]
    assert len({comedian.uuid for comedian in lineup}) == len(lineup)


@pytest.mark.asyncio
async def test_public_card_scraper_allows_missing_stand_lineup(monkeypatch):
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html_with_free_ticket()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert result is not None
    assert result.event_list[0].show.lineup == []


@pytest.mark.asyncio
async def test_public_card_scraper_parses_stand_paid_ticket_prices(monkeypatch):
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert result is not None
    assert result.event_list[0].show.tickets[0].price == 32.5


@pytest.mark.asyncio
async def test_public_card_scraper_parses_stand_current_ticket_container_prices(monkeypatch):
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html_with_ticket_container_price()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert result is not None
    assert result.event_list[0].title == "Laughing Buddha Comedy"
    assert result.event_list[0].show.room == "Upstairs"
    assert result.event_list[0].show.tickets[0].price == 30.0


@pytest.mark.asyncio
async def test_public_card_scraper_parses_stand_free_ticket_prices(monkeypatch):
    scraper = TixrPublicCardScraper(_stand_club())
    html_by_url = {
        STAND_PUBLIC_SHOWS_URL: _stand_public_card_html_with_free_ticket(),
        f"{STAND_PUBLIC_SHOWS_URL}?missing-ticket-text": (
            _stand_public_card_html_with_free_title_and_missing_ticket_text()
        ),
    }

    async def fake_fetch_html(self, url, **kwargs):
        return html_by_url[url]

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert result is not None
    ticket = result.event_list[0].show.tickets[0]
    assert ticket.purchase_url == STAND_FREE_TIXR_URL
    assert ticket.price == 0.0

    missing_text_result = await scraper.get_data(f"{STAND_PUBLIC_SHOWS_URL}?missing-ticket-text")

    assert missing_text_result is not None
    assert missing_text_result.event_list[0].show.tickets[0].price is None


@pytest.mark.asyncio
async def test_public_card_scraper_preserves_stand_sold_out_cards(monkeypatch):
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert result is not None
    assert result.get_event_count() == 2
    sold_out_event = next(event for event in result.event_list if event.source_url == STAND_SOLD_OUT_URL)
    assert sold_out_event.title == "The Stand Presents: Kyle Dunnigan"
    assert sold_out_event.show.date.year == 2026
    assert sold_out_event.show.date.month == 5
    assert sold_out_event.show.date.day == 8
    assert sold_out_event.show.date.hour == 20
    assert sold_out_event.show.date.minute == 0
    assert sold_out_event.show.room == "Main Room"


@pytest.mark.asyncio
async def test_public_card_scraper_uses_venue_url_for_stand_sold_out_card(monkeypatch):
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert result is not None
    sold_out_event = next(event for event in result.event_list if event.source_url == STAND_SOLD_OUT_URL)
    assert sold_out_event.event_id == ""
    assert sold_out_event.show.show_page_url == STAND_SOLD_OUT_URL
    assert len(sold_out_event.show.tickets) == 1
    ticket = sold_out_event.show.tickets[0]
    assert ticket.purchase_url == STAND_SOLD_OUT_URL
    assert ticket.sold_out is True
    assert ticket.price is None


@pytest.mark.asyncio
async def test_public_card_scraper_keeps_purchasable_stand_ticket_behavior(monkeypatch):
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert result is not None
    event = next(item for item in result.event_list if item.source_url == STAND_TIXR_URL)
    assert event.event_id == "187376"
    assert event.show.show_page_url == STAND_TIXR_URL
    assert [comedian.name for comedian in event.show.lineup] == ["Stephon Bishop", "Ashley King"]
    ticket = event.show.tickets[0]
    assert ticket.purchase_url == STAND_TIXR_URL
    assert ticket.price == 32.5
    assert ticket.sold_out is False


@pytest.mark.asyncio
async def test_public_card_scraper_skips_unactionable_stand_card(monkeypatch):
    scraper = TixrPublicCardScraper(_stand_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _stand_public_card_html_without_action()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(STAND_PUBLIC_SHOWS_URL)

    assert result is None


@pytest.mark.asyncio
async def test_public_card_scraper_parses_gocf_show_cards_and_city_filter(monkeypatch):
    """GOCF's Webflow city page carries complete show cards plus Tixr ticket URLs."""
    scraper = TixrPublicCardScraper(_gocf_halifax_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _gocf_public_card_html()

    monkeypatch.setattr(TixrPublicCardScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        scraper.tixr_client,
        "get_event_detail_from_url",
        AsyncMock(side_effect=AssertionError("Tixr detail pages should not be fetched")),
    )

    result = await scraper.get_data(GOCF_HALIFAX_URL)

    assert isinstance(result, TixrPageData)
    assert result.get_event_count() == 2
    by_title = {event.title: event for event in result.event_list}

    matt = by_title["Matt Rife"]
    assert matt.event_id == "152718"
    assert matt.show.date.isoformat() == "2026-08-06T19:30:00-03:00"
    assert matt.show.show_page_url == GOCF_MATT_RIFE_TIXR_URL
    assert [comedian.name for comedian in matt.show.lineup] == ["Matt Rife"]

    schulz = by_title["Andrew Schulz"]
    assert schulz.event_id == "152718"
    assert schulz.show.date.isoformat() == "2026-08-08T19:30:00-03:00"
    assert schulz.show.show_page_url == GOCF_HALIFAX_TIXR_URL
    assert [comedian.name for comedian in schulz.show.lineup] == [
        "Andrew Schulz",
        "Lucas Zelnick",
        "Kam Patterson",
        "Mark Gagnon",
    ]
    assert schulz.show.tickets[0].purchase_url == GOCF_HALIFAX_TIXR_URL
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_tixr_urls(monkeypatch):
    """get_data() returns None when no Tixr links are found on the page."""
    scraper = TixrScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return "<html><body><p>No shows</p></body></html>"

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_uses_improv_asylum_pixl_fallback_when_tixr_group_is_blocked(monkeypatch):
    """Improv Asylum falls back to the venue-owned Pixl API when the Tixr group page has no event links."""
    scraper = TixrScraper(_improv_asylum_club())

    async def fake_fetch_calendar_html(url):
        raise AssertionError(f"Improv Asylum should not fetch blocked Tixr group page: {url}")

    async def fake_fetch_json(url, **kwargs):
        assert url == "https://calendar.improvasylum.com/api/events/improv-asylum"
        return _improv_asylum_pixl_response()

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)
    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock()

    result = await scraper.get_data(IMPROV_ASYLUM_TIXR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    event = result.event_list[0]
    assert event.title == "Improv Asylum's Main Stage Show"
    assert event.event_id == "169028"
    assert event.show.date.isoformat() == "2026-05-08T19:00:00-04:00"
    assert event.show.show_page_url == (
        "https://www.tixr.com/groups/improvasylum/events/improv-asylum-s-main-stage-show-169028"
    )
    assert [ticket.type for ticket in event.show.tickets] == ["General Admission", "Premium"]
    assert [ticket.price for ticket in event.show.tickets] == [33.54, 37.18]
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_collect_scraping_targets_skips_improv_asylum_tixr_group_discovery(monkeypatch):
    scraper = TixrScraper(_improv_asylum_club())

    async def fake_fetch_calendar_html(url):
        raise AssertionError(f"Improv Asylum should not fetch blocked Tixr group discovery page: {url}")

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)

    assert await scraper.collect_scraping_targets() == [IMPROV_ASYLUM_TIXR_URL]


@pytest.mark.asyncio
async def test_get_data_uses_configured_pixl_calendar_api_without_tixr_detail_fetch(monkeypatch):
    """Comic Strip Edmonton reads the full Pixl inventory instead of the Webflow card subset."""
    scraper = TixrScraper(_comic_strip_edmonton_club())

    async def fail_fetch_calendar_html(url):
        raise AssertionError(f"Pixl Calendar source should not fetch HTML: {url}")

    pixl_url_seen: list[str] = []

    async def fake_fetch_json(url, **kwargs):
        pixl_url_seen.append(url)
        return _comic_strip_edmonton_pixl_response()

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fail_fetch_calendar_html)
    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(
        side_effect=AssertionError("Tixr detail pages should not be fetched for Pixl events")
    )

    assert await scraper.collect_scraping_targets() == [COMIC_STRIP_EDMONTON_PIXL_API_URL]

    result = await scraper.get_data(COMIC_STRIP_EDMONTON_PIXL_API_URL)

    assert pixl_url_seen == [COMIC_STRIP_EDMONTON_PIXL_API_URL]
    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    event = result.event_list[0]
    assert event.title == "Sean Lecomber"
    assert event.event_id == "185406"
    assert event.show.date.isoformat() == "2026-06-12T21:30:00-06:00"
    assert event.show.show_page_url == "https://www.tixr.com/groups/comicstripedmonton/events/sean-lecomber-185406"
    assert [ticket.type for ticket in event.show.tickets] == ["General Admission", "VIP"]
    assert [ticket.price for ticket in event.show.tickets] == [22.95, 32.95]
    assert [ticket.sold_out for ticket in event.show.tickets] == [False, True]
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


def test_pixl_parser_extracts_labeled_comics_from_description():
    data = _comic_strip_edmonton_pixl_response()
    data["events"][0]["description"] = (
        "<p>Sober &amp; Curious Boston creates alcohol-free events.</p>"
        "<p>Comics performing: Tony V, Al Park, Cher Lynn, and Jack Burke.</p>"
    )

    events = TixrScraper(_comic_strip_edmonton_club())._parse_pixl_calendar_events(data)

    assert [comedian.name for comedian in events[0].show.lineup] == [
        "Tony V",
        "Al Park",
        "Cher Lynn",
        "Jack Burke",
    ]


def test_pixl_parser_extracts_spanish_en_escena_lineup():
    data = _house_of_comedy_bc_pixl_response()
    data["events"][0]["description"] = (
        "<p>COMEDIA EN ESPAÑOL EN VANCOUVER!</p>"
        "<p>En escena...así como los vieron en Comedy Central, Just for Laughs, "
        "Latin Comedy Fest y los mejores festivales del mundo..."
        "Stephan Dyer (de Costa Rica), Juan Cajiao (de Colombia)!</p>"
    )

    events = TixrScraper(_house_of_comedy_bc_club())._parse_pixl_calendar_events(data)

    assert [comedian.name for comedian in events[0].show.lineup] == [
        "Stephan Dyer",
        "Juan Cajiao",
    ]


@pytest.mark.parametrize(
    "description",
    [
        "<p>Tony V is a comedian who has appeared on Comedy Central.</p>",
        "<p>Performer lineups subject to change without notice.</p>",
        "<p>Featuring LGBTQIA+ performers from the local comedy community.</p>",
    ],
)
def test_pixl_parser_ignores_performer_boilerplate_and_biographies(description):
    data = _comic_strip_edmonton_pixl_response()
    data["events"][0]["description"] = description

    events = TixrScraper(_comic_strip_edmonton_club())._parse_pixl_calendar_events(data)

    assert events[0].show.lineup == []


def test_pixl_lineup_extraction_preserves_existing_show_fields():
    data = _comic_strip_edmonton_pixl_response()
    raw_description = (
        "<p>Sober &amp; Curious Boston creates alcohol-free events.</p>"
        "<p>Comics performing: Tony V, Al Park, Cher Lynn, and Jack Burke.</p>"
    )
    data["events"][0]["description"] = raw_description

    event = TixrScraper(_comic_strip_edmonton_club())._parse_pixl_calendar_events(data)[0]

    assert event.title == "Sean Lecomber"
    assert event.show.date.isoformat() == "2026-06-12T21:30:00-06:00"
    assert event.show.show_page_url == (
        "https://www.tixr.com/groups/comicstripedmonton/events/sean-lecomber-185406"
    )
    assert [ticket.type for ticket in event.show.tickets] == ["General Admission", "VIP"]
    assert [ticket.price for ticket in event.show.tickets] == [22.95, 32.95]
    assert [ticket.sold_out for ticket in event.show.tickets] == [False, True]
    assert event.show.description == html.unescape(raw_description)


@pytest.mark.asyncio
async def test_get_data_uses_house_of_comedy_bc_pixl_calendar_api_without_tixr_detail_fetch(monkeypatch):
    """House of Comedy BC can use the same Pixl source shape as Comic Strip Edmonton."""
    scraper = TixrScraper(_house_of_comedy_bc_club())

    async def fail_fetch_calendar_html(url):
        raise AssertionError(f"Pixl Calendar source should not fetch HTML: {url}")

    pixl_url_seen: list[str] = []

    async def fake_fetch_json(url, **kwargs):
        pixl_url_seen.append(url)
        return _house_of_comedy_bc_pixl_response()

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fail_fetch_calendar_html)
    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(
        side_effect=AssertionError("Tixr detail pages should not be fetched for Pixl events")
    )

    assert await scraper.collect_scraping_targets() == [HOUSE_OF_COMEDY_BC_PIXL_API_URL]

    result = await scraper.get_data(HOUSE_OF_COMEDY_BC_PIXL_API_URL)

    assert pixl_url_seen == [HOUSE_OF_COMEDY_BC_PIXL_API_URL]
    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    event = result.event_list[0]
    assert event.title == "Drew Behm"
    assert event.event_id == "188517"
    assert event.show.date.isoformat() == "2026-07-02T19:30:00-07:00"
    assert event.show.show_page_url == "https://www.tixr.com/groups/comicstripbc/events/drew-behm-188517"
    assert [ticket.type for ticket in event.show.tickets] == ["General Admission", "Preferred Seating"]
    assert [ticket.price for ticket in event.show.tickets] == [18.0, 25.0]
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_get_data_uses_group_events_api_fallback_when_enabled_and_group_page_returns_none(monkeypatch):
    """Opt-in group-events API fallback can rescue a blocked Tixr group page."""
    monkeypatch.setenv("TIXR_GROUP_EVENTS_API_FALLBACK", "1")
    scraper = TixrScraper(_tixr_group_api_club())
    event = _make_tixr_event("189028", "Comedy Night")

    async def fake_fetch_calendar_html(url):
        raise AssertionError(f"Known DataDome Tixr group should use group API before page fetch: {url}")

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)
    scraper.tixr_client.fetch_group_events = AsyncMock(return_value=[event])
    scraper.tixr_client.get_event_detail_from_url = AsyncMock()

    result = await scraper.get_data("https://www.tixr.com/groups/laughfactorycovina")

    assert isinstance(result, TixrPageData)
    assert [e.event_id for e in result.event_list] == ["189028"]
    scraper.tixr_client.fetch_group_events.assert_awaited_once_with(
        "1613",
        max_pages=1,
        skip_direct=True,
    )
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_collect_scraping_targets_skips_tixr_group_discovery_when_api_fallback_enabled(monkeypatch):
    monkeypatch.setenv("TIXR_GROUP_EVENTS_API_FALLBACK", "1")
    scraper = TixrScraper(_tixr_group_api_club())

    async def fake_fetch_calendar_html(url):
        raise AssertionError(f"Known DataDome Tixr group should not fetch discovery page: {url}")

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)

    assert await scraper.collect_scraping_targets() == ["https://www.tixr.com/groups/laughfactorycovina"]


@pytest.mark.asyncio
async def test_get_data_does_not_use_group_events_api_fallback_when_flag_disabled(monkeypatch):
    """The direct API fallback is inert unless explicitly enabled."""
    monkeypatch.delenv("TIXR_GROUP_EVENTS_API_FALLBACK", raising=False)
    scraper = TixrScraper(_tixr_group_api_club())

    async def fake_fetch_calendar_html(url):
        return None

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)
    scraper.tixr_client.fetch_group_events = AsyncMock(return_value=[_make_tixr_event("189028", "Comedy Night")])
    scraper.tixr_client.get_event_detail_from_url = AsyncMock()

    result = await scraper.get_data("https://www.tixr.com/groups/laughfactorycovina")

    assert result is None
    scraper.tixr_client.fetch_group_events.assert_not_called()
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_get_data_uses_group_events_api_fallback_from_metadata_flag_and_slug(monkeypatch):
    """Per-source metadata can opt a venue-owned Rose City page into the group API fallback."""
    monkeypatch.delenv("TIXR_GROUP_EVENTS_API_FALLBACK", raising=False)
    scraper = TixrScraper(_rose_city_group_api_club())
    event = _make_tixr_event("190001", "Rose City Showcase")

    async def fake_fetch_calendar_html(url):
        return "<html><body>No machine-readable events here</body></html>"

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)
    scraper.tixr_client.fetch_group_events = AsyncMock(return_value=[event])
    scraper.tixr_client.get_event_detail_from_url = AsyncMock()

    result = await scraper.get_data("https://rosecitycomedy.club")

    assert isinstance(result, TixrPageData)
    assert [e.event_id for e in result.event_list] == ["190001"]
    scraper.tixr_client.fetch_group_events.assert_awaited_once_with(
        "rosecitycomedy",
        max_pages=12,
        skip_direct=False,
    )
    scraper.tixr_client.get_event_detail_from_url.assert_not_called()


@pytest.mark.asyncio
async def test_get_data_uses_group_events_api_fallback_when_all_detail_fetches_fail(monkeypatch):
    """Extracted detail URLs that all fail extraction still consult the group API fallback.

    Rose City incident (TASK-2763): the venue homepage fetch succeeds and Tixr
    detail URLs are extracted, but every detail fetch is DataDome-blocked. The
    zero-TixrEvents branch must consult the group-events API fallback instead
    of returning None.
    """
    monkeypatch.delenv("TIXR_GROUP_EVENTS_API_FALLBACK", raising=False)
    club = _rose_city_group_api_club()
    club.active_scraping_source.metadata = {
        "tixr_group_id": 2444,
        "tixr_group_events_api_fallback": True,
    }
    scraper = TixrScraper(club)
    event = _make_tixr_event("190002", "Rose City Late Show")
    html = _calendar_html_short(["177558", "182870"])

    async def fake_fetch_calendar_html(url):
        return html

    monkeypatch.setattr(scraper, "_fetch_calendar_html", fake_fetch_calendar_html)
    scraper.tixr_client.fetch_group_events = AsyncMock(return_value=[event])
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(return_value=None)

    result = await scraper.get_data("https://rosecitycomedy.club")

    assert isinstance(result, TixrPageData)
    assert [e.event_id for e in result.event_list] == ["190002"]
    scraper.tixr_client.fetch_group_events.assert_awaited_once_with(
        "2444",
        max_pages=12,
        skip_direct=False,
    )
    assert scraper.tixr_client.get_event_detail_from_url.await_count == 2


@pytest.mark.asyncio
async def test_get_data_returns_none_when_tixr_client_returns_nothing(monkeypatch):
    """get_data() returns None when TixrClient returns None for all URLs."""
    scraper = TixrScraper(_club())
    html = _calendar_html_short(["177558"])

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(return_value=None)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_filters_by_org_jsonld_when_present(monkeypatch):
    """get_data() only processes URLs found in the Organization JSON-LD block."""
    scraper = TixrScraper(_club())
    kept_url = "https://tixr.com/groups/venue/events/show-a-177558"
    dropped_url = "https://tixr.com/groups/venue/events/show-b--182870"  # double-dash, client-side

    org_jsonld = f"""
    <script type="application/ld+json">
    {{"@type": "Organization", "events": [{{"url": "{kept_url}"}}]}}
    </script>
    """
    html = f'<a href="{kept_url}">Show A</a><a href="{dropped_url}">Show B</a>{org_jsonld}'
    event = _make_tixr_event("177558", "Show A")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(return_value=event)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    # Only the kept URL was passed to the client
    scraper.tixr_client.get_event_detail_from_url.assert_called_once_with(kept_url)


@pytest.mark.asyncio
async def test_get_data_falls_back_to_all_urls_when_no_org_jsonld(monkeypatch):
    """get_data() uses all HTML-extracted URLs when no Organization JSON-LD block exists."""
    scraper = TixrScraper(_club())
    html = _calendar_html_short(["177558", "176996"])
    event_a = _make_tixr_event("177558", "Show A")
    event_b = _make_tixr_event("176996", "Show B")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(
        side_effect=lambda url: event_a if "177558" in url else event_b
    )

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 2


@pytest.mark.asyncio
async def test_get_data_filters_by_event_id_when_url_forms_differ(monkeypatch):
    """get_data() matches events by ID even when HTML has short-form URLs and
    Org JSON-LD has long-form URLs for the same events (or vice versa)."""
    scraper = TixrScraper(_club())

    # HTML has short-form; JSON-LD has long-form for the same event — string
    # equality would produce an empty intersection here.
    short_url = "https://tixr.com/e/177558"
    long_url_jsonld = "https://www.tixr.com/groups/venue/events/comedy-show-177558"
    dropped_long_url = "https://www.tixr.com/groups/venue/events/dropped--182870"

    org_jsonld = f"""
    <script type="application/ld+json">
    {{"@type": "Organization", "events": [{{"url": "{long_url_jsonld}"}}]}}
    </script>
    """
    html = (
        f'<a href="{short_url}">Short</a>'
        f'<a href="{long_url_jsonld}">Long</a>'
        f'<a href="{dropped_long_url}">Dropped</a>'
        + org_jsonld
    )
    event = _make_tixr_event("177558", "Comedy Show")

    async def fake_fetch_html(self, url, **kwargs):
        return html

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)
    scraper.tixr_client.get_event_detail_from_url = AsyncMock(return_value=event)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, TixrPageData)
    assert len(result.event_list) == 1
    # TixrExtractor deduplicates cross-form, keeping the short-form URL
    scraper.tixr_client.get_event_detail_from_url.assert_called_once_with(short_url)


@pytest.mark.asyncio
async def test_get_data_returns_none_on_fetch_error(monkeypatch):
    """get_data() returns None (and logs) when fetch_html raises an exception."""
    scraper = TixrScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        raise RuntimeError("connection timeout")

    monkeypatch.setattr(TixrScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None
