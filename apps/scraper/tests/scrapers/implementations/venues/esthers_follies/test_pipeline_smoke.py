"""
Pipeline smoke tests for EsthersFolliesScraper and EsthersFolliesEvent.

Exercises get_data() against mocked VBO Tickets HTTP responses and unit-tests
the EsthersFolliesEvent.to_show() transformation path.
"""

import re
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.esthers_follies import EsthersFolliesEvent, SeatTier
from laughtrack.scrapers.implementations.venues.esthers_follies.data import (
    EsthersFolliesPageData,
)
from laughtrack.scrapers.implementations.venues.esthers_follies.extractor import (
    EsthersFolliesEventExtractor,
)
from laughtrack.scrapers.implementations.venues.esthers_follies.scraper import (
    EsthersFolliesScraper,
    _VBO_LOADPLUGIN_URL,
)
from laughtrack.scrapers.implementations.venues.esthers_follies.seat_pricing import (
    extract_eventdateid_guid,
    parse_seat_tiers,
)

_SCRAPING_URL = "https://www.esthersfollies.com/tickets"

# Fake VBO session UUID used in mocked responses
_FAKE_SESSION = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"

# Minimal loadplugin HTML that embeds a session UUID
_LOADPLUGIN_HTML = f"""
<html><head></head><body>
<script>
    document.addEventListener("DOMContentLoaded", function () {{
        window.parent.postMessage(
            JSON.stringify({{
                type: "userSessionID",
                orgID: "7876",
                value: "{_FAKE_SESSION}"
            }}),
            "*"
        );
        window.location.href = "https://plugin.vbotickets.com/v5.0/event.asp?s={_FAKE_SESSION}";
    }});
</script>
</body></html>
"""


def _date_slider_html(*shows, include_calendar_box: bool = True) -> str:
    """Build a VBO date slider HTML fragment mirroring the live markup.

    Each ``show`` is ``(edid, month, day, weekday, time)``. Show boxes use the
    current ``onclick="LoadSpinner('<edid>'); LoadEvent('<eid>','<edid>');"``
    handler (VBO no longer leads with ``LoadEvent``).

    When ``include_calendar_box`` is set, a leading "More Event Dates" calendar
    button is prepended exactly as VBO renders it — it uses
    ``onclick="LoadEventCalendar(...)"`` and has no DateMonth/DateDay markup, so
    the extractor must skip it (TASK-2490 regression guard).
    """
    items = []
    if include_calendar_box and shows:
        cal_edid = shows[0][0]
        items.append(f"""
            <li>
                <div role="tab" tabindex="0" class="DateMsg SelectorBox Black"
                     id="edid{cal_edid}" onclick="LoadEventCalendar('39242','{cal_edid}');">
                    <div class="EventDateSliderMorePosRel">
                        <div class="EventDateSliderMore"> More Event Dates<br><i class="fal fa-calendar-alt"></i></div>
                    </div>
                </div>
            </li>
        """)
    for edid, month, day, weekday, time in shows:
        items.append(f"""
            <li>
                <div role="tab" tabindex="0" class="SelectorBox Black"
                     id="edid{edid}" onclick="LoadSpinner('{edid}'); LoadEvent('39242','{edid}');">
                    <div class="DateMonth __edid{edid}">{month}<div></div></div>
                    <div class="DateDay __edid{edid}">{day}<div></div></div>
                    <div class="DateTime __edid{edid}">
                        <span class="WeekDay">{weekday}</span>
                        <span class="WeekDayTime"> - {time}</span>
                        <div></div>
                    </div>
                </div>
            </li>
        """)
    return "<ul>" + "".join(items) + "</ul>"


def _club() -> Club:
    _c = Club(id=999, name="Esther's Follies", address='525 E. 6th Street', website='https://www.esthersfollies.com', popularity=0, zip_code='78701', phone_number='', visible=True, timezone='America/Chicago')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=_SCRAPING_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


# ---------------------------------------------------------------------------
# EsthersFolliesEventExtractor unit tests
# ---------------------------------------------------------------------------


def test_extractor_parses_single_show():
    html = _date_slider_html(("645532", "Mar", "26", "Thu", "7:00 PM"))
    events = EsthersFolliesEventExtractor.extract_shows(html)

    assert len(events) == 1
    ev = events[0]
    assert ev.edid == "645532"
    assert ev.month == "Mar"
    assert ev.day == 26
    assert ev.weekday == "Thu"
    assert ev.time == "7:00 PM"


def test_extractor_parses_multiple_shows():
    html = _date_slider_html(
        ("645591", "Mar", "27", "Fri", "7:00 PM"),
        ("645592", "Mar", "27", "Fri", "9:00 PM"),
        ("645857", "Mar", "28", "Sat", "7:00 PM"),
        ("645858", "Mar", "28", "Sat", "9:00 PM"),
    )
    events = EsthersFolliesEventExtractor.extract_shows(html)

    assert len(events) == 4
    times = {(e.month, e.day, e.time) for e in events}
    assert ("Mar", 27, "7:00 PM") in times
    assert ("Mar", 27, "9:00 PM") in times
    assert ("Mar", 28, "7:00 PM") in times
    assert ("Mar", 28, "9:00 PM") in times


def test_extractor_parses_full_slider_and_skips_calendar_box():
    """A realistic ~60-box slider parses every LoadSpinner show and skips the
    leading LoadEventCalendar 'More Event Dates' button.

    Regression for TASK-2490: VBO moved show boxes off a leading LoadEvent
    handler to LoadSpinner('<edid>'), so the old LoadEvent-anchored regex only
    matched by spanning from the calendar box into the first show — capping
    output at 1. The fixture mirrors the live LoadSpinner structure.
    """
    shows = [
        (str(660000 + i), "Jun", str((i % 28) + 1), "Fri", "7:00 PM")
        for i in range(60)
    ]
    html = _date_slider_html(*shows)
    # Sanity: the fixture really contains the calendar button we expect to skip.
    assert "LoadEventCalendar" in html

    events = EsthersFolliesEventExtractor.extract_shows(html)

    # All 60 LoadSpinner boxes parse; the calendar box (which shares the first
    # show's edid) does not inflate the count.
    assert len(events) == 60
    assert [e.edid for e in events] == [s[0] for s in shows]


def test_extractor_deduplicates_same_edid():
    # Duplicate EDID should only appear once
    html = _date_slider_html(
        ("645532", "Mar", "26", "Thu", "7:00 PM"),
        ("645532", "Mar", "26", "Thu", "7:00 PM"),
    )
    events = EsthersFolliesEventExtractor.extract_shows(html)
    assert len(events) == 1


def test_extractor_returns_empty_for_empty_html():
    events = EsthersFolliesEventExtractor.extract_shows("")
    assert events == []


def test_extractor_returns_empty_for_no_matches():
    events = EsthersFolliesEventExtractor.extract_shows("<ul><li>No shows</li></ul>")
    assert events == []


# ---------------------------------------------------------------------------
# EsthersFolliesEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def test_event_to_show_returns_valid_show():
    club = _club()
    # Use a future date guaranteed to be upcoming
    ev = EsthersFolliesEvent(edid="645532", month="Apr", day=3, weekday="Fri", time="7:00 PM")

    with patch("laughtrack.core.entities.event.esthers_follies.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 25)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        show = ev.to_show(club)

    assert show is not None
    assert show.name == "Esther's Follies"
    assert show.description == "Sketch Comedy | Political Satire | Award-winning Magic"
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://www.esthersfollies.com/tickets"


def test_event_to_show_year_rollover():
    """A past month/day should advance to the next year."""
    club = _club()
    # January show when today is March 25 — should be Jan 2027
    ev = EsthersFolliesEvent(edid="999999", month="Jan", day=10, weekday="Sat", time="9:00 PM")

    with patch("laughtrack.core.entities.event.esthers_follies.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 25)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        show = ev.to_show(club)

    assert show is not None
    assert show.date.year == 2027


def test_event_to_show_invalid_month_returns_none():
    club = _club()
    ev = EsthersFolliesEvent(edid="0", month="Xyz", day=1, weekday="Mon", time="7:00 PM")
    show = ev.to_show(club)
    assert show is None


# ---------------------------------------------------------------------------
# EsthersFolliesScraper.get_data() integration-style smoke test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data(monkeypatch):
    """get_data() extracts shows when VBO API responds with valid HTML."""
    club = _club()
    scraper = EsthersFolliesScraper(club)

    slider_html = _date_slider_html(
        ("645532", "Mar", "26", "Thu", "7:00 PM"),
        ("645591", "Mar", "27", "Fri", "7:00 PM"),
        ("645592", "Mar", "27", "Fri", "9:00 PM"),
    )

    async def fake_fetch_html(url, **kwargs):
        if "loadplugin" in url:
            return _LOADPLUGIN_HTML
        return slider_html

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())

    result = await scraper.get_data(_SCRAPING_URL)

    assert isinstance(result, EsthersFolliesPageData)
    assert len(result.event_list) == 3
    edids = {e.edid for e in result.event_list}
    assert "645532" in edids
    assert "645591" in edids
    assert "645592" in edids


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_session(monkeypatch):
    """get_data() returns None if session UUID is missing from loadplugin response."""
    club = _club()
    scraper = EsthersFolliesScraper(club)

    async def fake_fetch_html(url, **kwargs):
        return "<html><body>No session here</body></html>"

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())

    result = await scraper.get_data(_SCRAPING_URL)
    assert result is None


# ---------------------------------------------------------------------------
# VBO seat-pricing helpers: GUID extraction + getseats tier parsing
# ---------------------------------------------------------------------------


def _seat(section, price, total, status, type_="Full Price"):
    """Build one getseats seat dict matching the live VBO schema."""
    return {
        "SeatID": 1,
        "Status": status,
        "Price": price,
        "Total": total,
        "Type": type_,
        "Section": section,
        "Name": section,
    }


def _getseats_payload(seats):
    return {"Seats": seats}


# A realistic three-tier payload: Tier 1 mixed A/S (with a Handicap seat),
# Tier 2 fully sold (every seat S/C, no A), Tier 3 available.
_GETSEATS_FIXTURE = _getseats_payload(
    [
        _seat("Tier 1", 40.0, 45.75, "A"),
        _seat("Tier 1", 40.0, 45.75, "S"),
        _seat("Tier 1", 40.0, 45.75, "A", type_="Handicap"),
        _seat("Tier 2", 35.0, 40.75, "S"),
        _seat("Tier 2", 35.0, 40.75, "C"),  # held — still not available
        _seat("Tier 3", 30.0, 35.75, "A"),
        _seat("Tier 3", 30.0, 35.75, "A"),
    ]
)


def test_parse_seat_tiers_derives_distinct_tiers():
    tiers = parse_seat_tiers(_GETSEATS_FIXTURE)

    # Three distinct sections, ordered highest price first.
    assert [t.type for t in tiers] == ["Tier 1", "Tier 2", "Tier 3"]
    # Stores the Total (incl. $5.75 fee), not the base Price.
    assert [t.price for t in tiers] == [45.75, 40.75, 35.75]


def test_parse_seat_tiers_sold_out_when_no_available_seats():
    tiers = {t.type: t for t in parse_seat_tiers(_GETSEATS_FIXTURE)}

    # Tier 2 has only S/C seats -> sold out.
    assert tiers["Tier 2"].sold_out is True
    # Tiers 1 and 3 still have Status='A' seats -> available.
    assert tiers["Tier 1"].sold_out is False
    assert tiers["Tier 3"].sold_out is False


def test_parse_seat_tiers_handles_malformed_payload():
    assert parse_seat_tiers(None) == []
    assert parse_seat_tiers({}) == []
    assert parse_seat_tiers({"Seats": []}) == []
    assert parse_seat_tiers({"Seats": "nope"}) == []
    # Seats missing Section/Total are skipped, not crashed on.
    assert parse_seat_tiers({"Seats": [{"Status": "A"}]}) == []


def test_parse_seat_tiers_drops_non_positive_totals():
    """A Total of 0/negative is not a real tier price -> the tier is dropped.

    Pins the free-vs-unknown distinction: a $0 seat must not surface as a
    priced tier (Esther's never lists free seats), and a tier whose only seats
    have non-positive totals yields no SeatTier at all.
    """
    payload = _getseats_payload(
        [
            _seat("Tier 1", 40.0, 45.75, "A"),
            _seat("Comp", 0.0, 0.0, "A"),
            _seat("Comp", 0.0, -5.0, "A"),
        ]
    )
    tiers = parse_seat_tiers(payload)
    assert [t.type for t in tiers] == ["Tier 1"]


def test_extract_eventdateid_guid_picks_getseats_guid():
    session = "0502a945-7f25-418e-89ee-32143dd0f475"
    event_date_guid = "70D33085-625B-41B5-9E86-8E7ED0EA8B1D"
    svg = (
        f"<script>var seatmap; eventDateId: '667954'; "
        f"url: 'https://plugin.vbotickets.com/plugin/seatmap/getseats/"
        f"{event_date_guid}?s={session}&MapID=5835';</script>"
    )
    # Must return the getseats GUID, not the session UUID also present.
    assert extract_eventdateid_guid(svg) == event_date_guid


def test_extract_eventdateid_guid_returns_none_when_absent():
    assert extract_eventdateid_guid("") is None
    assert extract_eventdateid_guid(None) is None
    assert extract_eventdateid_guid("<svg>no getseats url here</svg>") is None


# ---------------------------------------------------------------------------
# to_show() ticket rendering: per-tier tickets vs. fallback
# ---------------------------------------------------------------------------


def test_event_to_show_renders_one_ticket_per_tier():
    club = _club()
    ev = EsthersFolliesEvent(
        edid="645532", month="Apr", day=3, weekday="Fri", time="7:00 PM",
        tiers=[
            SeatTier(type="Tier 1", price=45.75, sold_out=False),
            SeatTier(type="Tier 2", price=40.75, sold_out=True),
            SeatTier(type="Tier 3", price=35.75, sold_out=False),
        ],
    )

    with patch("laughtrack.core.entities.event.esthers_follies.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 25)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        show = ev.to_show(club)

    assert show is not None
    assert len(show.tickets) == 3
    by_type = {t.type: t for t in show.tickets}
    assert by_type["Tier 1"].price == 45.75
    assert by_type["Tier 2"].sold_out is True
    # purchase_url stays the stable venue page — never the session-scoped URL.
    assert all(t.purchase_url == "https://www.esthersfollies.com/tickets" for t in show.tickets)


def test_event_to_show_falls_back_to_single_ticket_without_tiers():
    """Enrichment failure leaves tiers=None -> one price-unknown fallback ticket."""
    club = _club()
    ev = EsthersFolliesEvent(edid="645532", month="Apr", day=3, weekday="Fri", time="7:00 PM")
    assert ev.tiers is None

    with patch("laughtrack.core.entities.event.esthers_follies.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 25)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        show = ev.to_show(club)

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].price is None
    assert show.tickets[0].purchase_url == "https://www.esthersfollies.com/tickets"


# ---------------------------------------------------------------------------
# Scraper enrichment: tiers populated on success, None on fetch failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_enriches_events_with_tiers(monkeypatch):
    """get_data() attaches parsed tiers when seat-map + getseats succeed."""
    club = _club()
    scraper = EsthersFolliesScraper(club)

    slider_html = _date_slider_html(("667954", "May", "28", "Thu", "7:00 PM"))
    guid = "70D33085-625B-41B5-9E86-8E7ED0EA8B1D"
    svg_html = (
        f"<script>url:'https://plugin.vbotickets.com/plugin/seatmap/getseats/"
        f"{guid}?s={_FAKE_SESSION}&MapID=5835';</script>"
    )

    async def fake_fetch_html(url, **kwargs):
        if "loadplugin" in url:
            return _LOADPLUGIN_HTML
        if "load_seat_map_svg" in url:
            return svg_html
        return slider_html

    async def fake_fetch_json(url, **kwargs):
        assert guid in url
        return _GETSEATS_FIXTURE

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())

    result = await scraper.get_data(_SCRAPING_URL)

    assert result is not None
    ev = result.event_list[0]
    assert ev.tiers is not None
    assert [t.type for t in ev.tiers] == ["Tier 1", "Tier 2", "Tier 3"]


@pytest.mark.asyncio
async def test_get_data_leaves_tiers_none_when_enrichment_fails(monkeypatch):
    """A failing seat-map fetch never aborts the run; tiers stay None."""
    club = _club()
    scraper = EsthersFolliesScraper(club)

    slider_html = _date_slider_html(("667954", "May", "28", "Thu", "7:00 PM"))

    async def fake_fetch_html(url, **kwargs):
        if "loadplugin" in url:
            return _LOADPLUGIN_HTML
        if "load_seat_map_svg" in url:
            raise RuntimeError("seat map endpoint down")
        return slider_html

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())

    result = await scraper.get_data(_SCRAPING_URL)

    assert result is not None
    assert len(result.event_list) == 1
    assert result.event_list[0].tiers is None


@pytest.mark.asyncio
async def test_get_data_enrichment_concurrency_is_bounded(monkeypatch):
    """Full-slider enrichment never exceeds the _ENRICH_CONCURRENCY cap.

    Regression guard for TASK-2490: now that the extractor parses ~60 slots
    (each costing two fetches), enrichment must fan out under a bounded
    semaphore rather than firing all slots at once or strictly serializing.
    """
    import asyncio as _asyncio

    from laughtrack.scrapers.implementations.venues.esthers_follies import (
        scraper as scraper_module,
    )

    club = _club()
    scraper = EsthersFolliesScraper(club)

    shows = [(str(670000 + i), "Jun", (i % 28) + 1, "Fri", "7:00 PM") for i in range(40)]
    slider_html = _date_slider_html(*shows)
    guid = "70D33085-625B-41B5-9E86-8E7ED0EA8B1D"
    svg_html = (
        f"<script>url:'https://plugin.vbotickets.com/plugin/seatmap/getseats/"
        f"{guid}?s={_FAKE_SESSION}&MapID=5835';</script>"
    )

    in_flight = 0
    peak = 0

    async def fake_fetch_html(url, **kwargs):
        nonlocal in_flight, peak
        if "loadplugin" in url:
            return _LOADPLUGIN_HTML
        if "load_seat_map_svg" in url:
            in_flight += 1
            peak = max(peak, in_flight)
            await _asyncio.sleep(0)  # yield so overlapping tasks accumulate
            in_flight -= 1
            return svg_html
        return slider_html

    async def fake_fetch_json(url, **kwargs):
        return _GETSEATS_FIXTURE

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())

    result = await scraper.get_data(_SCRAPING_URL)

    assert result is not None
    assert len(result.event_list) == 40
    # Every slot got enriched...
    assert all(ev.tiers is not None for ev in result.event_list)
    # ...but never more than the cap ran concurrently.
    assert peak <= scraper_module._ENRICH_CONCURRENCY
    assert peak > 1  # confirms work actually overlapped (not strictly serial)


@pytest.mark.asyncio
async def test_get_data_returns_none_when_slider_empty(monkeypatch):
    """get_data() returns None if the date slider returns no shows."""
    club = _club()
    scraper = EsthersFolliesScraper(club)

    async def fake_fetch_html(url, **kwargs):
        if "loadplugin" in url:
            return _LOADPLUGIN_HTML
        return "<ul></ul>"

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", AsyncMock())

    result = await scraper.get_data(_SCRAPING_URL)
    assert result is None
