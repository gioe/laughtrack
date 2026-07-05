"""
Pipeline smoke tests for VboTicketsScraper and VboEvent.

Exercises get_data() against mocked VBO Tickets responses matching the live
two-step flow (loadplugin → showevents listing), modelled on the Amish Country
Theater listing, plus unit tests for the VboEvent.to_show() transformation.
"""

from datetime import date

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
    assert show.lineup == []
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 15.0


def test_to_show_rejects_exact_title_as_headliner_without_explicit_signal():
    """Exact two-word titles are risky for VBO's mixed comedy/music feeds."""
    event = VboEvent(
        eid="200",
        name="Williamson Branch",
        date_str="Tue, 6/16/2099 @ 7:00 PM",
        url="https://plugin.vbotickets.com/v5.0/event.asp?eid=200",
        price_min=15.0,
    )
    show = event.to_show(_club())
    assert show is not None
    assert show.lineup == []


def test_to_show_returns_none_on_unparseable_date():
    event = VboEvent(eid="1", name="Mystery Show", date_str="TBD", url="http://x", price_min=None)
    assert event.to_show(_club()) is None


# ---------------------------------------------------------------------------
# category filter + free-form/recurring date expansion
# (the consolidated The Nest Theatre path — see TASK-2938)
# ---------------------------------------------------------------------------


def _nest_block(edid: str, eid: str, name: str, category: str, date_str: str, price: str) -> str:
    """A VBO list block shaped like The Nest Theatre's (category + free-form date + room line)."""
    return f"""
<div id="EDID{edid}" class="EventListWrapper EventListBgd clearfix EID{eid} EDID{edid} __FilterableEvent" data-event-name="{name}" data-event-category="{category}" data-event-subcategory="Improv" role="listitem">
  <div class="EventListPosterWrapper"><div class="EventListPoster">
    <a href="https://plugin.vbotickets.com/v5.0/event.asp?eid={eid}&amp;s=SESSION">buy</a>
    <div class="EventListPriceWrapper"><div class="EventListPriceBgd"><div class="EventListPrice">{price}</div></div></div>
  </div></div>
  <div class="EventListDetails"><div class="EventListText">
    <h2 class="HeaderEventName">{name}</h2>
    <div class="EventListVenue">The Nest Theatre - Mainstage</div>
    <div class="TextEventDate FloatLeft">{date_str}</div>
  </div></div>
</div>
"""


NEST_HTML = (
    '<div class="clearfix gridrow" id="CurrentEvents" role="list">'
    + _nest_block("690621", "194647", "Troika Improv Contest", "Live Shows",
                  "Fri 9:30pm 6/5, 6/19, 6/26, 7/10", "$15.00")
    + _nest_block("700001", "200001", "PROUD: A Variety Show!", "Live Shows",
                  "Thu 6/18 7:30pm", "$13.00")
    + _nest_block("700002", "200002", "Improv Level 1", "Classes",
                  "Mondays 6/1-6/29 6:30PM-8:30PM", "$200.00")
    + "</div>"
)

_REF_TODAY = date(2026, 6, 17)


def test_category_filter_keeps_only_allowed_categories():
    """A category_filter drops events whose data-event-category is not allowed."""
    filtered = VboTicketsExtractor.extract_events(
        NEST_HTML, category_filter="Live Shows", club_name="The Nest Theatre", today=_REF_TODAY
    )
    assert {e.name for e in filtered} == {"Troika Improv Contest", "PROUD: A Variety Show!"}
    assert "Improv Level 1" not in {e.name for e in filtered}  # Classes excluded

    # Without a filter the class is included. Its free-form range
    # "Mondays 6/1-6/29 6:30PM-8:30PM" parses like any recurring line: 6/1 is
    # dropped as past, 6/29 is kept, so the class surfaces as a single 6/29
    # occurrence — which is why a category_filter (not date-unparseability) is
    # what keeps classes out.
    unfiltered = VboTicketsExtractor.extract_events(
        NEST_HTML, club_name="The Nest Theatre", today=_REF_TODAY
    )
    classes = [e for e in unfiltered if e.name == "Improv Level 1"]
    assert [e.start_iso for e in classes] == ["2026-06-29 18:30:00"]


def test_category_filter_accepts_iterable():
    events = VboTicketsExtractor.extract_events(
        NEST_HTML, category_filter=["live shows"], club_name="The Nest Theatre", today=_REF_TODAY
    )
    assert {e.name for e in events} == {"Troika Improv Contest", "PROUD: A Variety Show!"}


def test_freeform_recurring_dates_expand_to_one_event_per_upcoming_date():
    """A recurring free-form date line yields one VboEvent per upcoming occurrence."""
    events = VboTicketsExtractor.extract_events(
        NEST_HTML, category_filter="Live Shows", club_name="The Nest Theatre", today=_REF_TODAY
    )
    troika = [e for e in events if e.name == "Troika Improv Contest"]
    # 6/5 is in the past relative to 2026-06-17 → dropped; 6/19, 6/26, 7/10 remain.
    assert [e.start_iso for e in troika] == [
        "2026-06-19 21:30:00",
        "2026-06-26 21:30:00",
        "2026-07-10 21:30:00",
    ]
    assert all(e.room == "Mainstage" for e in troika)
    assert all(e.price_min == 15.0 for e in troika)

    single = next(e for e in events if e.name == "PROUD: A Variety Show!")
    assert single.start_iso == "2026-06-18 19:30:00"
    assert single.room == "Mainstage"


def test_to_show_uses_precomputed_start_iso():
    """When start_iso is set it takes precedence over date_str parsing."""
    event = VboEvent(
        eid="194647", name="Troika Improv Contest",
        date_str="Fri 9:30pm 6/19, 6/26",  # raw free-form, not directly parseable
        url="https://plugin.vbotickets.com/v5.0/event.asp?eid=194647",
        price_min=15.0, start_iso="2026-06-19 21:30:00", room="Mainstage",
    )
    show = event.to_show(_club())
    assert show is not None
    assert show.date.year == 2026 and show.date.month == 6 and show.date.day == 19
    assert show.date.hour == 21 and show.date.minute == 30
    assert show.room == "Mainstage"
    assert show.tickets[0].price == 15.0


def test_structured_rows_unaffected_by_freeform_path():
    """Structured '@' rows still produce one event with no start_iso (Amish path)."""
    events = VboTicketsExtractor.extract_events(SHOWEVENTS_HTML)
    assert len(events) == 2
    assert all(e.start_iso is None and e.room == "" for e in events)


# ---------------------------------------------------------------------------
# title filter — mixed-use performing-arts venues (TASK-3204, Fair Oaks PAC)
# ---------------------------------------------------------------------------


# A Fair Oaks-shaped mixed-use listing: a comedy series alongside concerts /
# films / theatre, all sharing non-comedy-exclusive VBO categories.
MIXED_USE_HTML = (
    '<div class="clearfix gridrow" id="CurrentEvents" role="list">'
    + _event_block("1", "187150", "Comedy Under the Stars - Jon Stringer", "Fri, 7/11/2099 @ 7:30 PM", "$25.00")
    + _event_block("2", "188573", "The Ultimate Tribute Concert: Queen Revisited", "Sat, 7/12/2099 @ 8:00 PM", "$35.00")
    + _event_block("3", "190951", "Zak Mirz - Presents Kid at Heart Magic Show", "Sun, 7/13/2099 @ 2:00 PM", "$15.00")
    + "</div>"
)


def _fair_oaks_club(metadata: dict) -> Club:
    site_id = "AB1E7875-362D-4528-A36D-CEBDFC7BEDA9"
    loadplugin = f"https://plugin.vbotickets.com/plugin/loadplugin?siteid={site_id}&page=ListEvents"
    c = Club(
        id=9000, name="Fair Oaks Performing Arts Center",
        address="7991 California Ave", website="https://www.fairoaksarts.org",
        popularity=0, zip_code="95628", phone_number="", visible=True,
        timezone="America/Los_Angeles",
    )
    c.active_scraping_source = ScrapingSource(
        id=2, club_id=c.id, platform="vbo_tickets", scraper_key="vbo_tickets",
        source_url=loadplugin, external_id=None, metadata=metadata,
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


def _make_fake_fetch(showevents_html: str):
    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        if "loadplugin" in url:
            return LOADPLUGIN_HTML
        if "showevents" in url:
            return showevents_html
        raise AssertionError(f"unexpected url {url}")
    return fake_fetch_html


def _date_slider_html(*entries: tuple[str, str, int, str, str]) -> str:
    boxes = []
    for edid, month, day, weekday, time in entries:
        boxes.append(
            f"""
<div class="SelectorBox" id="edid{edid}" onclick="LoadSpinner('{edid}'); LoadEvent('1','{edid}');">
  <div class="DateMonth __edid{edid}">{month}<div></div></div>
  <div class="DateDay __edid{edid}">{day}<div></div></div>
  <div class="DateTime __edid{edid}">
    <span class="WeekDay">{weekday}</span>
    <span class="WeekDayTime"> - {time}</span>
  </div>
</div>
"""
        )
    return "\n".join(boxes)


def _malformed_date_slider_html() -> str:
    return """
<div class="SelectorBox" id="edid801001" onclick="LoadSpinner('801001'); LoadEvent('1','801001');">
  <div class="DateMonth __edid801001">Jul<div></div></div>
  <div class="DateDay __edid801001">11<div></div></div>
  <div class="DateTime __edid801001">
    <span class="WeekDay">Sat</span>
  </div>
</div>
<div class="SelectorBox" id="edid801003" onclick="LoadSpinner('801003'); LoadEvent('1','801003');">
  <div class="DateMonth __edid801003">Jul<div></div></div>
  <div class="DateDay __edid801003">18<div></div></div>
  <div class="DateTime __edid801003">
    <span class="WeekDay">Sat</span>
    <span class="WeekDayTime"> - 8:00 PM</span>
  </div>
</div>
"""


MADE_UP_HTML = (
    '<div class="clearfix gridrow" id="CurrentEvents" role="list">'
    + _nest_block("801001", "211001", "Laugh Track City", "MUT Shows",
                  "Saturdays at 8:00pm", "$20.00")
    + _nest_block("801002", "211002", "Family Friendly Matinee", "MUT Shows",
                  "Select Sundays at 2:30pm", "$12.00")
    + "</div>"
)


MADE_UP_SLIDERS = {
    "211001": _date_slider_html(
        ("801001", "Jul", 11, "Sat", "8:00 PM"),
        ("801003", "Jul", 18, "Sat", "8:00 PM"),
    ),
    "211002": _date_slider_html(
        ("801002", "Jul", 12, "Sun", "2:30 PM"),
    ),
}


@pytest.mark.asyncio
async def test_unparseable_recurring_rows_expand_from_detail_date_slider(monkeypatch):
    """Open-ended recurring listing rows use VBO's concrete detail-page dates."""
    fetched_urls: list[str] = []

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        fetched_urls.append(url)
        if "loadplugin" in url:
            return LOADPLUGIN_HTML
        if "showevents" in url:
            return MADE_UP_HTML
        if "load_eventdate_slider" in url:
            for eid, html in MADE_UP_SLIDERS.items():
                if f"eid={eid}" in url:
                    return html
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(VboTicketsScraper, "fetch_html", fake_fetch_html)

    # get_data() calls the slider extractor without a `today`, so the year-less
    # "Jul 11" boxes roll over on the wall clock — the month-granular expected-year
    # formula this test used diverged from the extractor's per-date rollover every
    # July 11-31. Pin `today` instead so the assertions stay literal (TASK-3586).
    real_expand = VboTicketsExtractor.extract_events_from_date_slider
    monkeypatch.setattr(
        VboTicketsExtractor,
        "extract_events_from_date_slider",
        staticmethod(
            lambda slider_html, target, today=None: real_expand(
                slider_html, target, today=date(2026, 6, 24)
            )
        ),
    )
    club = _fair_oaks_club({"category_filter": "MUT Shows"})
    club.name = "Made Up Theatre"
    club.timezone = "America/Los_Angeles"

    result = await VboTicketsScraper(club).get_data(club.active_scraping_source.source_url)

    assert isinstance(result, VboTicketsPageData)
    assert [(e.name, e.start_iso) for e in result.event_list] == [
        ("Laugh Track City", "2026-07-11 20:00:00"),
        ("Laugh Track City", "2026-07-18 20:00:00"),
        ("Family Friendly Matinee", "2026-07-12 14:30:00"),
    ]
    assert {e.url for e in result.event_list} == {
        "https://plugin.vbotickets.com/v5.0/event.asp?eid=211001",
        "https://plugin.vbotickets.com/v5.0/event.asp?eid=211002",
    }
    detail_fetches = [url for url in fetched_urls if "load_eventdate_slider" in url]
    assert len(detail_fetches) == 2
    assert all("s=e5fc5abd-aeae-4e80-8a9c-0fd090ed40b0" in url for url in detail_fetches)


def test_date_slider_parser_skips_malformed_boxes_without_cross_box_pairing():
    """A malformed slider box must not steal the next box's time."""
    target = VboTicketsExtractor.extract_detail_expansion_targets(
        MADE_UP_HTML,
        category_filter="MUT Shows",
        club_name="Made Up Theatre",
    )[0]

    events = VboTicketsExtractor.extract_events_from_date_slider(
        _malformed_date_slider_html(),
        target,
        today=date(2026, 6, 24),
    )

    assert [e.start_iso for e in events] == ["2026-07-18 20:00:00"]


@pytest.mark.asyncio
async def test_structured_rows_do_not_fetch_detail_date_slider(monkeypatch):
    """Rows with concrete listing dates stay on the listing-only path."""
    fetched_urls: list[str] = []

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        fetched_urls.append(url)
        if "loadplugin" in url:
            return LOADPLUGIN_HTML
        if "showevents" in url:
            return SHOWEVENTS_HTML
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(VboTicketsScraper, "fetch_html", fake_fetch_html)
    result = await VboTicketsScraper(_club()).get_data(LOADPLUGIN_URL)

    assert isinstance(result, VboTicketsPageData)
    assert len(result.event_list) == 2
    assert not any("load_eventdate_slider" in url for url in fetched_urls)


@pytest.mark.asyncio
async def test_include_title_patterns_keeps_only_comedy(monkeypatch):
    """include_title_patterns keeps only the comedy series on a mixed-use listing."""
    monkeypatch.setattr(
        VboTicketsScraper, "fetch_html",
        _make_fake_fetch(MIXED_USE_HTML),
    )
    club = _fair_oaks_club({"include_title_patterns": ["Comedy Under the Stars"]})
    result = await VboTicketsScraper(club).get_data(club.active_scraping_source.source_url)
    assert isinstance(result, VboTicketsPageData)
    assert {e.name for e in result.event_list} == {"Comedy Under the Stars - Jon Stringer"}


@pytest.mark.asyncio
async def test_no_title_filter_keeps_all_events(monkeypatch):
    """With no title filter configured the full mixed-use listing passes through."""
    monkeypatch.setattr(
        VboTicketsScraper, "fetch_html",
        _make_fake_fetch(MIXED_USE_HTML),
    )
    club = _fair_oaks_club({})
    result = await VboTicketsScraper(club).get_data(club.active_scraping_source.source_url)
    assert isinstance(result, VboTicketsPageData)
    assert len(result.event_list) == 3


@pytest.mark.asyncio
async def test_exclude_title_patterns_drops_matches(monkeypatch):
    """exclude_title_patterns drops matching titles (e.g. magic shows)."""
    monkeypatch.setattr(
        VboTicketsScraper, "fetch_html",
        _make_fake_fetch(MIXED_USE_HTML),
    )
    club = _fair_oaks_club({"exclude_title_patterns": ["Magic Show"]})
    result = await VboTicketsScraper(club).get_data(club.active_scraping_source.source_url)
    assert isinstance(result, VboTicketsPageData)
    names = {e.name for e in result.event_list}
    assert "Zak Mirz - Presents Kid at Heart Magic Show" not in names
    assert len(names) == 2


@pytest.mark.asyncio
async def test_include_and_exclude_compose(monkeypatch):
    """include + exclude compose: keep comedy, then drop an excluded comedy night."""
    monkeypatch.setattr(
        VboTicketsScraper, "fetch_html",
        _make_fake_fetch(MIXED_USE_HTML),
    )
    club = _fair_oaks_club({
        "include_title_patterns": ["Comedy Under the Stars"],
        "exclude_title_patterns": ["Jon Stringer"],
    })
    result = await VboTicketsScraper(club).get_data(club.active_scraping_source.source_url)
    # The only comedy event is the excluded one → nothing left → None.
    assert result is None
