"""
Pipeline smoke tests for CreekAndCaveScraper and CreekAndCaveShow.

Exercises get_data() against mocked Punchup/Next.js calendar HTML matching the
actual www.creekandcave.com/calendar RSC stream (show rows embedded as a
"shows": [...] component prop inside self.__next_f.push() chunks), and
unit-tests the CreekAndCaveShow.to_show() transformation path.
"""

import importlib.util
import json

from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.creek_and_cave.scraper import CreekAndCaveScraper
from laughtrack.scrapers.implementations.venues.creek_and_cave.data import CreekAndCavePageData, CreekAndCaveShow
from laughtrack.scrapers.implementations.venues.creek_and_cave.extractor import CreekAndCaveEventExtractor


_CALENDAR_URL = "https://www.creekandcave.com/calendar"
_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _club() -> Club:
    _c = Club(id=999, name='The Creek and The Cave', address='611 East 7th St', website='https://www.creekandcave.com', popularity=0, zip_code='78701', phone_number='', visible=True, timezone='America/Chicago')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=_CALENDAR_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _show_row(**overrides) -> dict:
    """One raw event row matching the live calendar RSC field set (2099 dates)."""
    row = {
        "id": "b87b52de-4d9f-4ef0-87f2-b5fe5a90eb8d",
        "created_at": "2026-05-27T17:24:06.045044+00:00",
        "location": "Austin, TX",
        "venue": "The Creek and The Cave",
        "ticket_link": "https://event.tixologi.com/event/12297/tickets",
        "comedian_id": None,
        "venue_id": "5dc840a3-14c4-4425-b3c2-371305fda4e7",
        "datetime": "2099-06-11T23:55:00",
        "is_sold_out": False,
        "metadata_text": "FREE! Every Thursday at Midnight\n\nWord Up! Open mic\n\nHosted by: Jordyn Aguilar",
        "vip_ticket_link": None,
        "presale_code": None,
        "flags": [],
        "title": "Word Up! Open Mic",
        "tixologi_event_id": "12297",
        "poster_img": None,
        "published_at": None,
        "comedian": None,
        "show_comedians": [],
        "venue_pages": [{"id": "5a78dea7", "slug": "creekandcave", "is_live": True}],
    }
    row.update(overrides)
    return row


def _calendar_payload(rows: list) -> str:
    """Wrap rows in the RSC component-prop shape the live /calendar page uses."""
    return (
        '8:["$","div",null,{"children":["$","$L19",null,{"shows":'
        + json.dumps(rows)
        + ',"venueSlug":"creekandcave"}]}]'
    )


def _push_html(*payloads: str) -> str:
    """Embed payloads as JS-escaped self.__next_f.push([1, "..."]) script chunks."""
    scripts = "".join(
        f"<script>self.__next_f.push([1,{json.dumps(p)}])</script>" for p in payloads
    )
    return f"<html><body>{scripts}</body></html>"


def _calendar_html(rows: list) -> str:
    return _push_html(_calendar_payload(rows))


def _stub_tixologi(monkeypatch):
    """Bypass Tixologi enrichment in tests that don't exercise pricing."""

    async def identity(self, shows):
        return shows

    monkeypatch.setattr(CreekAndCaveScraper, "_enrich_tixologi_tickets", identity)


# ---------------------------------------------------------------------------
# Registry key
# ---------------------------------------------------------------------------


def test_scraper_key_in_registry():
    from laughtrack.app.registry import SCRAPERS

    assert SCRAPERS.get("creek_and_cave") is CreekAndCaveScraper


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_calendar_url():
    """collect_scraping_targets() returns the single /calendar page URL."""
    scraper = CreekAndCaveScraper(_club())
    targets = await scraper.collect_scraping_targets()

    assert targets == [_CALENDAR_URL]


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() parses the RSC stream and returns CreekAndCavePageData."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _calendar_html([_show_row()])

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_html_bare", fake_fetch_html_bare)
    _stub_tixologi(monkeypatch)

    result = await scraper.get_data(_CALENDAR_URL)

    assert isinstance(result, CreekAndCavePageData)
    assert len(result.event_list) == 1
    event = result.event_list[0]
    assert event.title == "Word Up! Open Mic"
    assert event.datetime_str == "2099-06-11T23:55:00"
    assert event.ticket_link == "https://event.tixologi.com/event/12297/tickets"
    assert event.tixologi_event_id == "12297"
    assert event.is_sold_out is False


@pytest.mark.asyncio
async def test_get_data_parses_real_trimmed_snippet(monkeypatch):
    """get_data() parses the trimmed real calendar RSC snippet fixture."""
    scraper = CreekAndCaveScraper(_club())
    snippet = (_FIXTURES_DIR / "calendar_rsc_snippet.html").read_text()

    async def fake_fetch_html_bare(self, url: str) -> str:
        return snippet

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_html_bare", fake_fetch_html_bare)
    _stub_tixologi(monkeypatch)

    result = await scraper.get_data(_CALENDAR_URL)

    assert isinstance(result, CreekAndCavePageData)
    titles = {e.title for e in result.event_list}
    assert titles == {"Word Up! Open Mic", "Kate Berlant"}
    kate = next(e for e in result.event_list if e.title == "Kate Berlant")
    assert [c["display_name"] for c in kate.show_comedians] == ["Kate Berlant"]


@pytest.mark.asyncio
async def test_get_data_dedupes_rows_across_payloads(monkeypatch):
    """The same row appearing in more than one chunk yields a single event."""
    scraper = CreekAndCaveScraper(_club())
    row = _show_row()

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _push_html(_calendar_payload([row]), _calendar_payload([row]))

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_html_bare", fake_fetch_html_bare)
    _stub_tixologi(monkeypatch)

    result = await scraper.get_data(_CALENDAR_URL)

    assert isinstance(result, CreekAndCavePageData)
    assert len(result.event_list) == 1


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when fetch_html_bare returns falsy."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return ""

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_html_bare", fake_fetch_html_bare)
    _stub_tixologi(monkeypatch)

    result = await scraper.get_data(_CALENDAR_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_event_rows(monkeypatch):
    """get_data() returns None when the page has no event-shaped rows."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _push_html('8:["$","div",null,{"children":"no shows here"}]')

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_html_bare", fake_fetch_html_bare)
    _stub_tixologi(monkeypatch)

    result = await scraper.get_data(_CALENDAR_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_propagates_fetch_exception(monkeypatch):
    """Fetch errors propagate to the BaseScraper retry/diagnostics layer.

    Creek is single-target, so swallowing a fetch error here would
    misclassify a full site outage as an empty calendar (review 5131
    comment 2954); the Gotham feed scraper propagates the same way.
    """
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        raise RuntimeError("network error")

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_html_bare", fake_fetch_html_bare)

    with pytest.raises(RuntimeError, match="network error"):
        await scraper.get_data(_CALENDAR_URL)


# ---------------------------------------------------------------------------
# Tixologi ticket-type enrichment (TASK-2840) — mirrors west_side
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_enriches_tixologi_ticket_types(monkeypatch):
    """Shows carry Tixologi initial_price tickets via the west_side enrichment pattern."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _calendar_html([_show_row()])

    async def fake_fetch_event_ticket_types(event_id: str):
        assert event_id == "12297"
        return [{"name": "General Admission", "initial_price": 15, "sold_out": False}]

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(
        scraper.tixologi_client,
        "fetch_event_ticket_types",
        fake_fetch_event_ticket_types,
    )

    result = await scraper.get_data(_CALENDAR_URL)

    assert isinstance(result, CreekAndCavePageData)
    show = result.event_list[0].to_show(_club())
    assert show is not None
    assert show.tickets[0].price == 15.0
    assert show.tickets[0].type == "General Admission"


@pytest.mark.asyncio
async def test_get_data_enrichment_preserves_vip_ticket_row(monkeypatch):
    """The CreekAndCaveShow subclass survives enrichment: VIP row still appended."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _calendar_html([
            _show_row(vip_ticket_link="https://event.tixologi.com/event/12297/vip")
        ])

    async def fake_fetch_event_ticket_types(event_id: str):
        return [{"name": "General Admission", "initial_price": 15, "sold_out": False}]

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(
        scraper.tixologi_client,
        "fetch_event_ticket_types",
        fake_fetch_event_ticket_types,
    )

    result = await scraper.get_data(_CALENDAR_URL)

    enriched = result.event_list[0]
    assert isinstance(enriched, CreekAndCaveShow)
    show = enriched.to_show(_club())
    types = [(t.type, t.price) for t in show.tickets]
    assert ("General Admission", 15.0) in types
    assert ("VIP", None) in types


@pytest.mark.asyncio
async def test_get_data_enrichment_skips_shows_without_tixologi_event_id(monkeypatch):
    """Shows without a resolvable tixologi_event_id never trigger a client call."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        # Non-tixologi ticket link and no explicit id → extractor leaves the id unset.
        return _calendar_html([
            _show_row(
                tixologi_event_id=None,
                ticket_link="https://www.eventbrite.com/e/some-show-12345",
            )
        ])

    # Record calls rather than raising: the enrichment guard catches Exception
    # (including AssertionError), so an exploding mock could be swallowed and
    # the test would pass even if the client WERE called.
    client_calls: list = []

    async def recording_fetch_event_ticket_types(event_id: str):
        client_calls.append(event_id)
        return []

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(
        scraper.tixologi_client,
        "fetch_event_ticket_types",
        recording_fetch_event_ticket_types,
    )

    result = await scraper.get_data(_CALENDAR_URL)

    assert isinstance(result, CreekAndCavePageData)
    assert client_calls == [], "client must not be called for shows without an event id"
    show = result.event_list[0].to_show(_club())
    assert show.tickets[0].price is None


@pytest.mark.asyncio
async def test_get_data_enrichment_failure_keeps_show_with_fallback_ticket(monkeypatch):
    """A Tixologi outage degrades one show to the priceless fallback, not a dropped calendar."""
    scraper = CreekAndCaveScraper(_club())

    async def fake_fetch_html_bare(self, url: str) -> str:
        return _calendar_html([_show_row()])

    async def raising_fetch_event_ticket_types(event_id: str):
        raise RuntimeError("tixologi down")

    monkeypatch.setattr(CreekAndCaveScraper, "fetch_html_bare", fake_fetch_html_bare)
    monkeypatch.setattr(
        scraper.tixologi_client,
        "fetch_event_ticket_types",
        raising_fetch_event_ticket_types,
    )

    result = await scraper.get_data(_CALENDAR_URL)

    assert isinstance(result, CreekAndCavePageData)
    show = result.event_list[0].to_show(_club())
    assert show is not None
    assert show.tickets[0].price is None


# ---------------------------------------------------------------------------
# CreekAndCaveEventExtractor unit tests
# ---------------------------------------------------------------------------


def test_extract_shows_skips_row_missing_datetime():
    rows = [_show_row(datetime=""), _show_row(id="other-id")]
    shows = CreekAndCaveEventExtractor.extract_shows(_calendar_html(rows))
    assert len(shows) == 1


def test_extract_shows_skips_row_missing_title():
    rows = [_show_row(title=""), _show_row(id="other-id")]
    shows = CreekAndCaveEventExtractor.extract_shows(_calendar_html(rows))
    assert len(shows) == 1


def test_extract_shows_skips_row_missing_ticket_link():
    """Every emitted Show must carry at least one Ticket — link-less rows drop."""
    rows = [_show_row(ticket_link=""), _show_row(id="other-id")]
    shows = CreekAndCaveEventExtractor.extract_shows(_calendar_html(rows))
    assert len(shows) == 1


def test_extract_shows_infers_tixologi_event_id_from_ticket_link():
    rows = [_show_row(tixologi_event_id=None)]
    shows = CreekAndCaveEventExtractor.extract_shows(_calendar_html(rows))
    assert len(shows) == 1
    assert shows[0].tixologi_event_id == "12297"


def test_extract_shows_falls_back_to_punchup_query_cache():
    """With no component-prop rows, the shared Punchup query-cache path is used."""
    payload = {
        "queries": [
            {
                "queryKey": ["venuePageCarousel", "creek-venue-uuid"],
                "state": {
                    "data": {
                        "mode": "custom",
                        "items": [
                            {
                                "type": "show",
                                "id": "item-uuid-1",
                                "show": {
                                    "id": "show-uuid-1",
                                    "title": "Creek Carousel Show",
                                    "datetime": "2099-04-15T20:00:00",
                                    "ticket_link": "https://event.tixologi.com/event/42/tickets",
                                    "tixologi_event_id": "42",
                                    "is_sold_out": False,
                                    "metadata_text": None,
                                    "show_comedians": [],
                                },
                            }
                        ],
                    },
                    "status": "success",
                },
            }
        ]
    }
    html = f"<html><body><script>{json.dumps(payload)}</script></body></html>"
    shows = CreekAndCaveEventExtractor.extract_shows(html)

    assert len(shows) == 1
    assert isinstance(shows[0], CreekAndCaveShow)
    assert shows[0].title == "Creek Carousel Show"


def test_extract_shows_returns_empty_for_empty_html():
    assert CreekAndCaveEventExtractor.extract_shows("") == []


# ---------------------------------------------------------------------------
# CreekAndCaveShow.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_show(
    title="Word Up! Open Mic",
    datetime_str="2099-06-11T23:55:00",
    ticket_link="https://event.tixologi.com/event/12297/tickets",
    tixologi_event_id="12297",
    is_sold_out=False,
    metadata_text=None,
    show_comedians=None,
    vip_ticket_link=None,
) -> CreekAndCaveShow:
    return CreekAndCaveShow(
        id="b87b52de-4d9f-4ef0-87f2-b5fe5a90eb8d",
        title=title,
        datetime_str=datetime_str,
        ticket_link=ticket_link,
        tixologi_event_id=tixologi_event_id,
        is_sold_out=is_sold_out,
        metadata_text=metadata_text,
        show_comedians=show_comedians or [],
        vip_ticket_link=vip_ticket_link,
    )


def test_to_show_returns_show_with_correct_name_and_date():
    """to_show() localizes the naive datetime to the club timezone (America/Chicago)."""
    event = _make_show(datetime_str="2099-06-11T23:55:00")
    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Word Up! Open Mic"
    # Naive local time stays local: 2099-06-11 23:55 in America/Chicago
    assert show.date.year == 2099
    assert show.date.month == 6
    assert show.date.day == 11
    assert show.date.hour == 23
    assert show.date.minute == 55
    assert show.date.utcoffset() is not None


def test_to_show_creates_ticket_from_ticket_link():
    """to_show() always emits at least one Ticket using the Tixologi ticket_link."""
    event = _make_show()
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://event.tixologi.com/event/12297/tickets"
    assert show.tickets[0].sold_out is False


def test_to_show_propagates_sold_out_flag():
    event = _make_show(is_sold_out=True)
    show = event.to_show(_club())

    assert show is not None
    assert all(t.sold_out for t in show.tickets)


def test_to_show_adds_vip_ticket_row():
    """vip_ticket_link produces an additional VIP ticket alongside GA."""
    event = _make_show(vip_ticket_link="https://event.tixologi.com/event/12297/vip")
    show = event.to_show(_club())

    assert show is not None
    assert len(show.tickets) == 2
    vip = show.tickets[1]
    assert vip.purchase_url == "https://event.tixologi.com/event/12297/vip"
    assert vip.type == "VIP"


def test_to_show_builds_plain_lineup_from_show_comedians():
    """Lineup entries are plain comedian names ordered by 'ordering' — no roles."""
    event = _make_show(
        title="Kate Berlant",
        show_comedians=[
            {"display_name": "Surprise Guest", "ordering": 1},
            {"display_name": "Kate Berlant", "ordering": 0},
        ],
    )
    show = event.to_show(_club())

    assert show is not None
    assert [c.name for c in show.lineup] == ["Kate Berlant", "Surprise Guest"]


def test_to_show_empty_lineup_when_no_show_comedians():
    event = _make_show(show_comedians=[])
    show = event.to_show(_club())

    assert show is not None
    assert show.lineup == []


def test_to_show_uses_metadata_text_as_description():
    event = _make_show(metadata_text="FREE! Every Thursday at Midnight")
    show = event.to_show(_club())

    assert show is not None
    assert show.description == "FREE! Every Thursday at Midnight"


def test_to_show_returns_none_on_unparseable_date():
    """to_show() returns None when the datetime cannot be parsed."""
    event = _make_show(datetime_str="not-a-date")
    show = event.to_show(_club())

    assert show is None
