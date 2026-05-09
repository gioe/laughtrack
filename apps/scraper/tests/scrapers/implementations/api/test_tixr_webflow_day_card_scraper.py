"""Tests for the generic Webflow day-card + Tixr scraper.

The same code path serves multiple venues (The Comic Strip Edmonton, House of
Comedy BC, ...) by reading ``source_url`` from ``scraping_sources`` and
``tixr_group_fragment`` from ``scraping_sources.metadata``.
"""

from datetime import datetime

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.tixr.scraper import (
    TixrWebflowDayCardScraper,
)
from laughtrack.scrapers.implementations.api.tixr.webflow_day_card import (
    WebflowDayCardPageData,
)


_BC_SOURCE_URL = "https://bc.houseofcomedy.net/"
_BC_FRAGMENT = "tixr.com/groups/comicstripbc/events/"
_BC_EVENT_URL = "https://www.tixr.com/groups/comicstripbc/events/rell-battle-174083"

_EDMONTON_SOURCE_URL = "https://wem.thecomicstrip.ca/"
_EDMONTON_FRAGMENT = "tixr.com/groups/comicstripedmonton/events/"
_EDMONTON_EVENT_URL = (
    "https://www.tixr.com/groups/comicstripedmonton/events/sean-lecomber-185406"
)


def _club(
    *,
    club_id: int,
    name: str,
    source_url: str,
    fragment: str,
    timezone: str,
    metadata_extra: dict | None = None,
) -> Club:
    metadata = {"tixr_group_fragment": fragment}
    if metadata_extra:
        metadata.update(metadata_extra)
    club = Club(
        id=club_id,
        name=name,
        address="",
        website=source_url,
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        timezone=timezone,
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="tixr_webflow_day_card",
        source_url=source_url,
        external_id=None,
        metadata=metadata,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _bc_club(metadata_extra: dict | None = None) -> Club:
    return _club(
        club_id=2001,
        name="House of Comedy British Columbia",
        source_url=_BC_SOURCE_URL,
        fragment=_BC_FRAGMENT,
        timezone="America/Vancouver",
        metadata_extra=metadata_extra,
    )


def _edmonton_club(metadata_extra: dict | None = None) -> Club:
    return _club(
        club_id=2002,
        name="The Comic Strip West Edmonton Mall",
        source_url=_EDMONTON_SOURCE_URL,
        fragment=_EDMONTON_FRAGMENT,
        timezone="America/Edmonton",
        metadata_extra=metadata_extra,
    )


def _bc_html() -> str:
    return f"""<html><body>
<a class="day-card w-inline-block" href="{_BC_EVENT_URL}" target="_blank">
  <div class="event-name show">Rell Battle</div>
  <p class="event-name spaced">East Village</p>
  <div class="date">
    <p class="b-venue">May 7, 2026</p>
    <p class="b-venue">7:30 pm</p>
  </div>
</a>
<a class="day-card w-inline-block" href="https://www.tixr.com/groups/someoneelse/events/foreign-1">
  <div class="event-name show">Foreign Group Show</div>
  <div class="date"><p class="b-venue">May 7, 2026</p><p class="b-venue">7:30 pm</p></div>
</a>
</body></html>"""


def _edmonton_html() -> str:
    return f"""<html><body>
<a class="day-card w-inline-block" href="{_EDMONTON_EVENT_URL}" target="_blank">
  <div class="event-name show">Sean Lecomber</div>
  <p class="event-name spaced">Main Stage</p>
  <div class="date">
    <p class="b-venue">June 12, 2026</p>
    <p class="b-venue">9:00 pm</p>
  </div>
</a>
</body></html>"""


def test_construct_requires_tixr_group_fragment_in_metadata():
    club = _bc_club()
    club.active_scraping_source.metadata = {}

    with pytest.raises(ValueError, match="tixr_group_fragment"):
        TixrWebflowDayCardScraper(club)


def test_construct_requires_source_url():
    club = _bc_club()
    club.active_scraping_source.source_url = ""

    with pytest.raises(ValueError, match="source_url"):
        TixrWebflowDayCardScraper(club)


@pytest.mark.asyncio
async def test_get_data_returns_page_data_for_bc(monkeypatch):
    scraper = TixrWebflowDayCardScraper(_bc_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _bc_html()

    monkeypatch.setattr(TixrWebflowDayCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(_BC_SOURCE_URL)

    assert isinstance(result, WebflowDayCardPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Rell Battle"
    assert result.event_list[0].ticket_url == _BC_EVENT_URL


@pytest.mark.asyncio
async def test_get_data_returns_page_data_for_edmonton(monkeypatch):
    scraper = TixrWebflowDayCardScraper(_edmonton_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _edmonton_html()

    monkeypatch.setattr(TixrWebflowDayCardScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(_EDMONTON_SOURCE_URL)

    assert isinstance(result, WebflowDayCardPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Sean Lecomber"
    assert result.event_list[0].ticket_url == _EDMONTON_EVENT_URL


@pytest.mark.asyncio
async def test_get_data_filters_foreign_group_cards(monkeypatch):
    # BC's fragment must not match Edmonton's group URL even though both pages
    # share the a.day-card markup — that's the whole point of the fragment.
    scraper = TixrWebflowDayCardScraper(_bc_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _edmonton_html()  # Edmonton URLs only — none match BC fragment

    monkeypatch.setattr(TixrWebflowDayCardScraper, "fetch_html", fake_fetch_html)

    assert await scraper.get_data(_BC_SOURCE_URL) is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_event_cards(monkeypatch):
    scraper = TixrWebflowDayCardScraper(_bc_club())

    async def fake_fetch_html(self, url, **kwargs):
        return "<html><body>No shows scheduled</body></html>"

    monkeypatch.setattr(TixrWebflowDayCardScraper, "fetch_html", fake_fetch_html)

    assert await scraper.get_data(_BC_SOURCE_URL) is None


@pytest.mark.asyncio
async def test_collect_scraping_targets_uses_source_url():
    scraper = TixrWebflowDayCardScraper(_bc_club())

    targets = await scraper.collect_scraping_targets()

    assert targets == [_BC_SOURCE_URL]


def test_transformation_pipeline_produces_show_with_club_timezone(monkeypatch):
    scraper = TixrWebflowDayCardScraper(_bc_club())

    from laughtrack.scrapers.implementations.api.tixr.webflow_day_card import (
        WebflowDayCardExtractor,
    )

    page_data = WebflowDayCardPageData(
        event_list=WebflowDayCardExtractor.extract_events(
            _bc_html(),
            source_url=_BC_SOURCE_URL,
            config=scraper.config,
        )
    )

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 1
    assert isinstance(shows[0], Show)
    assert shows[0].name == "Rell Battle"
    assert shows[0].show_page_url == _BC_EVENT_URL
    assert shows[0].date == datetime(2026, 5, 7, 19, 30, tzinfo=shows[0].date.tzinfo)
