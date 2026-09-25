"""Tests for generic Etix fetch routing."""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.etix.scraper import EtixScraper


def _club() -> Club:
    club = Club(
        id=207,
        name="Dr. Grins Comedy Club",
        address="",
        website="https://www.thebob.com/dr-grins",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone="America/Detroit",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="etix",
        scraper_key="dr_grins",
        source_url=(
            "https://www.etix.com/ticket/mvc/online/upcomingEvents/venue" "?venue_id=35455&orderBy=1&pageNumber=1"
        ),
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


@pytest.mark.asyncio
async def test_etix_fetches_use_shared_etix_proxy_key(monkeypatch):
    """Venue-specific Etix subclasses still route HTTP through scraper_key='etix'."""
    scraper = EtixScraper(_club())
    fetch_html = AsyncMock(return_value="<html></html>")
    monkeypatch.setattr(scraper, "fetch_html", fetch_html)

    await scraper.collect_scraping_targets()

    assert fetch_html.await_args.kwargs["scraper_key"] == "etix"


@pytest.mark.asyncio
@pytest.mark.parametrize("public_source", [False, True])
@pytest.mark.parametrize(
    "response",
    [None, RuntimeError("upstream transport failure"), "<html>DataDome challenge</html>", "<html>maintenance</html>"],
)
async def test_blocked_source_recovery_status(monkeypatch, public_source, response):
    """Failed mandatory inventory must not authorize stale-show deletion."""
    from types import SimpleNamespace
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
    )
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    club = _club()
    if public_source:
        club.active_scraping_source.source_url = "https://venue.example/shows/"
    scraper = EtixScraper(club)
    fetch = AsyncMock(
        side_effect=response if isinstance(response, Exception) else None,
        return_value=response if not isinstance(response, Exception) else None,
    )
    monkeypatch.setattr(scraper, "fetch_html_bare" if public_source else "_fetch_etix_html", fetch)
    scraper.rate_limiter = SimpleNamespace(await_if_needed=AsyncMock())
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        results = await scraper._fetch_all_raw_data([club.scraping_url])
    finally:
        reset_diagnostics(token)
    assert results[0][0] is None
    assert diagnostics.fetches_failed == 1
    assert diagnostics.fetches_ok == 0
    assert diagnostics.scrape_errors
    assert fetch.await_count == 1  # HIGH DataError prevents another whole-source retry.
    result = SimpleNamespace(
        error=None,
        shows=[],
        bot_block_detected=diagnostics.bot_block_detected,
        fetches_failed=diagnostics.fetches_failed,
        fetches_ok=diagnostics.fetches_ok,
        items_before_filter=0,
    )
    assert not ScrapingResultProcessor._is_clean_for_reconciliation(result)


@pytest.mark.asyncio
async def test_verified_public_recovery_is_healthy(monkeypatch):
    """A real Rockhouse fixture recovers inventory without probing blocked Etix."""
    import runpy
    from pathlib import Path
    from types import SimpleNamespace
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
    )
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    fixture = runpy.run_path(str(Path(__file__).with_name("test_tampa_funny_bone_fallback.py")))
    scraper = EtixScraper(fixture["_club"]())
    fetch = AsyncMock(return_value=fixture["_shows_html"]())
    monkeypatch.setattr(scraper, "fetch_html_bare", fetch)
    monkeypatch.setattr(
        scraper, "_fetch_etix_html", AsyncMock(side_effect=AssertionError("blocked Etix must not be probed"))
    )
    scraper.rate_limiter = SimpleNamespace(await_if_needed=AsyncMock())
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        targets = await scraper.collect_scraping_targets()
        results = await scraper._fetch_all_raw_data(targets)
    finally:
        reset_diagnostics(token)
    events = results[0][0].event_list
    assert len(events) == 3
    assert all(event.ticket_url.startswith("https://www.etix.com/ticket/") for event in events)
    assert diagnostics.fetches_ok == 1
    assert diagnostics.fetches_failed == 0
    assert not diagnostics.bot_block_detected
    result = SimpleNamespace(
        error=None,
        shows=events,
        bot_block_detected=False,
        fetches_failed=0,
        fetches_ok=1,
        items_before_filter=len(events),
    )
    assert ScrapingResultProcessor._is_clean_for_reconciliation(result)


# Trimmed from the observed Winery Rockhouse empty-calendar wrapper.
_VERIFIED_EMPTY = """<div id="desktopView">
<h1 class="rhp-events-page-title">Upcoming Events</h1>
<form id="rhp-bar-form">
<input id="rhp_bar_search_box" value="">
<input id="rhp_bar_rhp_month" value="0">
<input id="rhp-bar-just-announced" value="0">
</form><div class="generalView rhp-desktop-list rhp-mobile-list"></div>
<div class="p-4 noEventsNotice">There were no results found.</div></div>"""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "html,healthy",
    [
        (_VERIFIED_EMPTY, True),
        (_VERIFIED_EMPTY + "<title>DataDome</title>", False),
        ("<html>Maintenance: There were no results found.</html>", False),
        ('<div class="noEventsNotice">There were no results found.</div>', False),
        (_VERIFIED_EMPTY.replace('value="0"', 'value="1"'), False),
        (_VERIFIED_EMPTY.replace("</form>", '</form><div class="eventWrapper">Unparseable event</div>'), False),
        (_VERIFIED_EMPTY.replace('id="desktopView"', 'id="other"'), False),
    ],
)
async def test_verified_rockhouse_empty_requires_calendar_structure(monkeypatch, html, healthy):
    from types import SimpleNamespace
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
    )
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    club = _club()
    club.active_scraping_source.source_url = "https://venue.example/events/"
    scraper = EtixScraper(club)
    scraper.fetch_html_bare = AsyncMock(return_value=html)
    scraper.rate_limiter = SimpleNamespace(await_if_needed=AsyncMock())
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        results = await scraper._fetch_all_raw_data([club.scraping_url])
    finally:
        reset_diagnostics(token)
    assert diagnostics.fetches_ok == int(healthy)
    assert diagnostics.fetches_failed == int(not healthy)
    if healthy:
        assert results[0][0].event_list == []
    result = SimpleNamespace(
        error=None,
        shows=[],
        bot_block_detected=diagnostics.bot_block_detected,
        fetches_failed=diagnostics.fetches_failed,
        fetches_ok=diagnostics.fetches_ok,
        items_before_filter=0,
    )
    assert ScrapingResultProcessor._is_clean_for_reconciliation(result) is healthy


@pytest.mark.asyncio
async def test_conflicting_public_performances_keep_safe_events_but_block_cleanup():
    import runpy
    from pathlib import Path
    from types import SimpleNamespace
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
    )
    from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor

    fixture = runpy.run_path(str(Path(__file__).with_name("test_rockhouse_recovery.py")))
    series = fixture["series"]
    html = series("CAM ROWE", "cam-rowe", [("Oct 15", "Show | 7 pm", fixture["MIKE"])])
    html += series("MIKE CRONIN", "mike-cronin", [("Oct 15", "Show | 7 pm", fixture["MIKE"])])
    html += series("SAFE SHOW", "safe-show", [("Oct 16", "Show | 7 pm", fixture["THANKSGIVING"])])
    club = _club()
    club.active_scraping_source.source_url = "https://www.comedycastle.com/events/"
    scraper = EtixScraper(club)
    scraper.fetch_html_bare = AsyncMock(return_value=html)
    scraper.rate_limiter = SimpleNamespace(await_if_needed=AsyncMock())
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        results = await scraper._fetch_all_raw_data([club.scraping_url])
    finally:
        reset_diagnostics(token)
    events = results[0][0].event_list
    assert [event.title for event in events] == ["SAFE SHOW"]
    assert diagnostics.fetches_failed == 1
    assert diagnostics.fetches_ok == 1
    assert "62115951" in diagnostics.scrape_errors[0]
    result = SimpleNamespace(
        error=None, shows=events, bot_block_detected=False, fetches_failed=diagnostics.fetches_failed, fetches_ok=1
    )
    assert not ScrapingResultProcessor._is_clean_for_reconciliation(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("broken", [False, True])
async def test_official_tribe_source_routes_verified_cards_and_fails_closed(broken):
    import runpy
    from pathlib import Path
    from types import SimpleNamespace
    from laughtrack.foundation.infrastructure.http.diagnostics import (
        ScrapeDiagnostics,
        bind_diagnostics,
        reset_diagnostics,
    )

    fixture = runpy.run_path(str(Path(__file__).with_name("test_tribe_recovery.py")))
    html = fixture["SOURCE_HTML"]
    if broken:
        html += '<a class="tribe-events-c-nav__next" href="/events/page/2/">Next Events</a>'
    club = _club()
    club.active_scraping_source.source_url = "https://desplainestheatre.com/events/category/comedy/"
    scraper = EtixScraper(club)
    scraper.fetch_html_bare = AsyncMock(return_value=html)
    scraper._fetch_etix_html = AsyncMock(side_effect=AssertionError("must use official source"))
    scraper.rate_limiter = SimpleNamespace(await_if_needed=AsyncMock())
    diagnostics = ScrapeDiagnostics()
    token = bind_diagnostics(diagnostics)
    try:
        targets = await scraper.collect_scraping_targets()
        assert targets == [club.scraping_url]
        results = await scraper._fetch_all_raw_data(targets)
    finally:
        reset_diagnostics(token)
    scraper._fetch_etix_html.assert_not_called()
    if broken:
        assert results[0][0] is None
        assert diagnostics.fetches_failed == 1
        assert diagnostics.fetches_ok == 0
    else:
        assert len(results[0][0].event_list) == 1
        assert "TERRY FATOR" in results[0][0].event_list[0].title
        assert diagnostics.fetches_failed == 0
        assert diagnostics.fetches_ok == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "excluded_title", ["Sitting Down to Stand Up Comedy Class", "O Christmas Tea: A British Comedy"]
)
async def test_explicit_title_exclusion_precedes_every_positive_comedy_signal(monkeypatch, excluded_title):
    from types import SimpleNamespace
    from laughtrack.scrapers.implementations.api.etix.data import EtixPageData
    import laughtrack.scrapers.implementations.api.etix.scraper as module

    club = _club()
    club.active_scraping_source.metadata = {
        "comedy_filter": True,
        "comedy_title_allowlist": [excluded_title],
        "excluded_event_titles": ["  " + excluded_title.upper() + "  "],
    }
    scraper = EtixScraper(club)
    safe = SimpleNamespace(title="Lucy's Comedy")
    rejected = SimpleNamespace(title=excluded_title)
    # Preserve a different complete title even when it contains the exclusion.
    other = SimpleNamespace(title=excluded_title + " Retrospective")
    scraper._get_data_raw = AsyncMock(return_value=EtixPageData(event_list=[safe, rejected, other]))
    seen = []

    def positive_filter(titles, **kwargs):
        seen.extend(titles)
        return set(titles)  # Even an all-positive keyword/name/allowlist result cannot resurrect it.

    monkeypatch.setattr(module, "select_comedy_titles", positive_filter)
    result = await scraper.get_data(club.scraping_url)
    assert result.event_list == [safe, other]
    assert excluded_title not in seen
    assert seen == [safe.title, other.title]


@pytest.mark.asyncio
async def test_title_exclusion_is_optional_and_applies_without_comedy_filter():
    from types import SimpleNamespace
    from laughtrack.scrapers.implementations.api.etix.data import EtixPageData

    club = _club()
    club.active_scraping_source.metadata = {"excluded_event_titles": ["O Christmas Tea: A British Comedy"]}
    scraper = EtixScraper(club)
    scraper._get_data_raw = AsyncMock(
        return_value=EtixPageData(event_list=[SimpleNamespace(title="O Christmas Tea: A British Comedy")])
    )
    assert (await scraper.get_data(club.scraping_url)).event_list == []
