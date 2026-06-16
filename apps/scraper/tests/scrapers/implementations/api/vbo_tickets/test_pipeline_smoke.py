"""
Pipeline smoke tests for VboTicketsScraper and VboEvent.

Exercises get_data() against mocked VBO Tickets responses matching the live
two-step flow (loadplugin → showevents listing), modelled on the Amish Country
Theater listing, plus unit tests for the VboEvent.to_show() transformation.
"""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.vbo_tickets import VboEvent
from laughtrack.scrapers.implementations.api.vbo_tickets.data import VboTicketsPageData
from laughtrack.scrapers.implementations.api.vbo_tickets.extractor import VboTicketsExtractor
from laughtrack.scrapers.implementations.api.vbo_tickets.scraper import VboTicketsScraper

_SITE_ID = "4A6B1B18-AF73-4099-9005-D183148A1A68"
LOADPLUGIN_URL = f"https://plugin.vbotickets.com/plugin/loadplugin?siteid={_SITE_ID}&page=ListEvents"

# Minimal loadplugin response: posts the user-session UUID to the parent frame.
LOADPLUGIN_HTML = """
<!DOCTYPE html><html><head></head><body>
<script type="text/javascript">
  window.parent.postMessage(JSON.stringify({
    type: "userSessionID", orgID: "8965",
    value: "e5fc5abd-aeae-4e80-8a9c-0fd090ed40b0"
  }), "*");
</script></body></html>
"""

# Trimmed showevents listing with two real-shaped event blocks.
def _event_block(edid: str, eid: str, name: str, date_str: str, price: str) -> str:
    return f"""
<div id="EDID{edid}" class="EventListWrapper EventListBgd clearfix EID{eid} EDID{edid} __FilterableEvent" data-event-name="{name}" data-event-category="Theater" data-event-subcategory="Comedy" role="listitem">
  <div class="EventListPosterWrapper"><div class="EventListPoster">
    <a href="https://plugin.vbotickets.com/v5.0/event.asp?eid={eid}&amp;s=SESSION">buy</a>
    <div class="EventListPriceWrapper"><div class="EventListPriceBgd"><div class="EventListPrice">{price}</div></div></div>
  </div></div>
  <div class="EventListDetails"><div class="EventListText">
    <h2 class="HeaderEventName"><a href='https://plugin.vbotickets.com/v5.0/event.asp?eid={eid}&s=SESSION'>{name}</a></h2>
    <div class="TextEventDate FloatLeft">{date_str}</div>
  </div></div>
</div>
"""


SHOWEVENTS_HTML = (
    '<div class="clearfix gridrow" id="CurrentEvents" role="list">'
    + _event_block("615463", "175043", "Macho Mule Comedy Show  6/16", "Tue, 6/16/2099 @ 7:00 PM", "$15.00 - $32.95")
    + _event_block("588367", "166874", "Bringing Home the Bacon Comedy Show  6/18", "Thu, 6/18/2099 @ 7:00 PM", "$12.00 - $32.95")
    + "</div>"
)


def _club() -> Club:
    c = Club(
        id=400, name="Amish Country Theater", address="4365 OH-39",
        website="https://amishcountrytheater.com", popularity=0, zip_code="44610",
        phone_number="", visible=True, timezone="America/New_York",
    )
    c.active_scraping_source = ScrapingSource(
        id=1, club_id=c.id, platform="vbo_tickets", scraper_key="vbo_tickets",
        source_url=LOADPLUGIN_URL, external_id=None,
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


# ---------------------------------------------------------------------------
# extractor unit tests
# ---------------------------------------------------------------------------


def test_extract_session():
    assert VboTicketsExtractor.extract_session(LOADPLUGIN_HTML) == "e5fc5abd-aeae-4e80-8a9c-0fd090ed40b0"
    assert VboTicketsExtractor.extract_session("no session here") is None


def test_extract_events_parses_name_date_price_eid():
    events = VboTicketsExtractor.extract_events(SHOWEVENTS_HTML)
    assert len(events) == 2
    first = events[0]
    assert first.eid == "175043"
    assert first.name == "Macho Mule Comedy Show  6/16"
    assert first.date_str == "Tue, 6/16/2099 @ 7:00 PM"
    assert first.price_min == 15.0
    assert first.url == "https://plugin.vbotickets.com/v5.0/event.asp?eid=175043"


# ---------------------------------------------------------------------------
# get_data tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_two_step_flow(monkeypatch):
    """get_data() acquires a session then parses the showevents listing."""
    scraper = VboTicketsScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        if "loadplugin" in url:
            return LOADPLUGIN_HTML
        if "showevents" in url:
            assert "s=e5fc5abd-aeae-4e80-8a9c-0fd090ed40b0" in url
            return SHOWEVENTS_HTML
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(VboTicketsScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(LOADPLUGIN_URL)

    assert isinstance(result, VboTicketsPageData)
    assert len(result.event_list) == 2
    assert {e.name for e in result.event_list} == {
        "Macho Mule Comedy Show  6/16",
        "Bringing Home the Bacon Comedy Show  6/18",
    }


@pytest.mark.asyncio
async def test_get_data_returns_none_without_session(monkeypatch):
    scraper = VboTicketsScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html>no session</html>"

    monkeypatch.setattr(VboTicketsScraper, "fetch_html", fake_fetch_html)
    assert await scraper.get_data(LOADPLUGIN_URL) is None


def test_to_show_parses_date_strips_trailing_date_and_sets_price():
    event = VboEvent(
        eid="175043",
        name="Macho Mule Comedy Show  6/16",
        date_str="Tue, 6/16/2099 @ 7:00 PM",
        url="https://plugin.vbotickets.com/v5.0/event.asp?eid=175043",
        price_min=15.0,
    )
    show = event.to_show(_club())
    assert show is not None
    assert show.name == "Macho Mule Comedy Show"  # trailing " 6/16" stripped
    assert show.date.year == 2099 and show.date.month == 6 and show.date.day == 16
    assert show.date.hour == 19
    assert show.show_page_url == "https://plugin.vbotickets.com/v5.0/event.asp?eid=175043"
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 15.0


def test_to_show_returns_none_on_unparseable_date():
    event = VboEvent(eid="1", name="Mystery Show", date_str="TBD", url="http://x", price_min=None)
    assert event.to_show(_club()) is None
