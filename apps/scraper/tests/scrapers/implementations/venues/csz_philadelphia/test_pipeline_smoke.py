"""
Smoke tests for the CSz Philadelphia (ComedySportz) scraper pipeline.

Exercises the three-stage pipeline with HTML fixtures that match the
real VBO Tickets plugin responses:

  Stage 1 – collect_scraping_targets():
    Fetches showevents HTML, returns one target per comedy show.

  Stage 2 – get_data(target):
    Fetches date-slider HTML, returns one CszPhillyShowInstance per date.

  Stage 3 – transformation_pipeline:
    CszPhillyShowInstance → Show (year-inference + datetime parse).
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.csz_philadelphia.scraper import (
    CszPhiladelphiaScraper,
)
from laughtrack.scrapers.implementations.venues.csz_philadelphia.extractor import (
    CszPhillyEventExtractor,
)
from laughtrack.scrapers.implementations.venues.csz_philadelphia.page_data import (
    CszPhillyPageData,
    CszPhillyShowInstance,
)


SESSION_KEY = "4610c334-6cb9-4033-b991-1c1a89918a19"
SHOWEVENTS_URL = (
    f"https://plugin.vbotickets.com/Plugin/events/showevents"
    f"?ViewType=list&EventType=current&day=&s={SESSION_KEY}"
)
DATE_SLIDER_URL_PREFIX = "https://plugin.vbotickets.com/v5.0/controls/events.asp"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _club() -> Club:
    return Club(
        id=99,
        name="CSz Philadelphia",
        address="2030 Sansom Street",
        website="https://www.comedysportzphilly.com",
        scraping_url=f"https://plugin.vbotickets.com/Plugin/events?s={SESSION_KEY}",
        popularity=0,
        zip_code="19103",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


def _showevents_html() -> str:
    """
    Minimal VBO showevents HTML containing two comedy shows and one class.
    The comedy-show divs carry data-event-subcategory="Comedy".
    The class div carries data-event-subcategory="Core - Level 1" and must
    NOT appear in collect_scraping_targets() output.
    """
    return """
<div id="CurrentEvents" role="list">
  <div id="EDID655663" class="EventListWrapper EID2062 EDID655663 __FilterableEvent"
       data-event-name="ComedySportz"
       data-event-category="Performing Arts"
       data-event-subcategory="Comedy"
       role="listitem">
    <a href="https://plugin.vbotickets.com/v5.0/event.asp?eid=2062&amp;s=SESSION">
      Buy tickets for ComedySportz
    </a>
  </div>
  <div id="EDID674117" class="EventListWrapper EID190467 EDID674117 __FilterableEvent"
       data-event-name="What If?"
       data-event-category="Performing Arts"
       data-event-subcategory="Comedy"
       role="listitem">
    <a href="https://plugin.vbotickets.com/v5.0/event.asp?eid=190467&amp;s=SESSION">
      Buy tickets for What If?
    </a>
  </div>
  <div id="EDID660657" class="EventListWrapper EID9161 EDID660657 __FilterableEvent"
       data-event-name="CSz 101: Introduction to Improv"
       data-event-category="Classes"
       data-event-subcategory="Core - Level 1"
       role="listitem">
    <a href="https://plugin.vbotickets.com/v5.0/event.asp?eid=9161&amp;s=SESSION">
      Enroll
    </a>
  </div>
</div>
""".strip()


def _date_slider_html_comedysportz() -> str:
    """
    Minimal VBO date-slider HTML for ComedySportz (eid=2062).
    Contains two upcoming Saturday-evening instances.
    """
    return """
<script>/* slider init */</script>
<div class="EventDatesWrapper">
  <ul class="uk-slider-items">
    <li>
      <div class="SelectorBox SelectorBoxSelected" id="edid655663"
           onclick="LoadEvent('2062','655663');">
        <div class="DateMonth __edid655663">Mar<div></div></div>
        <div class="DateDay __edid655663">28<div></div></div>
        <div class="DateTime __edid655663">
          <span class="WeekDay">Sat</span>
          <span class="WeekDayTime"> - 7:00 PM</span>
          <div></div>
        </div>
      </div>
    </li>
    <li>
      <div class="SelectorBox Black" id="edid657712"
           onclick="LoadEvent('2062','657712');">
        <div class="DateMonth __edid657712">Apr<div></div></div>
        <div class="DateDay __edid657712">4<div></div></div>
        <div class="DateTime __edid657712">
          <span class="WeekDay">Sat</span>
          <span class="WeekDayTime"> - 7:00 PM</span>
          <div></div>
        </div>
      </div>
    </li>
  </ul>
</div>
""".strip()


def _date_slider_html_single_date() -> str:
    """Date-slider HTML for an event with exactly one upcoming performance."""
    return """
<div class="EventDatesWrapper">
  <ul class="uk-slider-items">
    <li>
      <div class="SelectorBox" id="edid674117">
        <div class="DateMonth __edid674117">Apr<div></div></div>
        <div class="DateDay __edid674117">10<div></div></div>
        <div class="DateTime __edid674117">
          <span class="WeekDay">Fri</span>
          <span class="WeekDayTime"> - 7:00 PM</span>
          <div></div>
        </div>
      </div>
    </li>
  </ul>
</div>
""".strip()


# ---------------------------------------------------------------------------
# Unit tests for the extractor
# ---------------------------------------------------------------------------

class TestCszPhillyEventExtractor:
    def test_parse_comedy_events_filters_classes(self):
        events = CszPhillyEventExtractor.parse_comedy_events(_showevents_html())
        names = [title for _, _, title in events]
        assert "ComedySportz" in names
        assert "What If?" in names
        assert "CSz 101: Introduction to Improv" not in names

    def test_parse_comedy_events_returns_correct_ids(self):
        events = CszPhillyEventExtractor.parse_comedy_events(_showevents_html())
        eid_map = {title: eid for eid, _, title in events}
        assert eid_map["ComedySportz"] == 2062
        assert eid_map["What If?"] == 190467

    def test_parse_show_dates_returns_two_instances(self):
        instances = CszPhillyEventExtractor.parse_show_dates(
            _date_slider_html_comedysportz(), event_id=2062, event_name="ComedySportz"
        )
        assert len(instances) == 2

    def test_parse_show_dates_fields(self):
        instances = CszPhillyEventExtractor.parse_show_dates(
            _date_slider_html_comedysportz(), event_id=2062, event_name="ComedySportz"
        )
        first = instances[0]
        assert first.event_id == 2062
        assert first.event_date_id == 655663
        assert first.event_name == "ComedySportz"
        assert first.month == "Mar"
        assert first.day == 28
        assert first.weekday == "Sat"
        assert first.time == "7:00 PM"

    def test_parse_show_dates_empty_html(self):
        instances = CszPhillyEventExtractor.parse_show_dates(
            "<html></html>", event_id=2062, event_name="ComedySportz"
        )
        assert instances == []


# ---------------------------------------------------------------------------
# Smoke tests — full pipeline with mocked fetch_html
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_comedy_shows(monkeypatch):
    """collect_scraping_targets() must return targets only for comedy shows."""
    scraper = CszPhiladelphiaScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _showevents_html()

    monkeypatch.setattr(CszPhiladelphiaScraper, "fetch_html", fake_fetch_html)

    targets = await scraper.collect_scraping_targets()

    assert len(targets) == 2, f"Expected 2 comedy-show targets, got {len(targets)}: {targets}"
    names = [t.split("|", 2)[2] for t in targets]
    assert "ComedySportz" in names
    assert "What If?" in names
    # Classes must be excluded
    assert all("CSz 101" not in n for n in names)


@pytest.mark.asyncio
async def test_collect_scraping_targets_stale_session_key(monkeypatch, caplog):
    """
    When showevents returns HTML without 'CurrentEvents' or 'EventListWrapper',
    collect_scraping_targets() must log a stale-session-key warning and return [].
    """
    import logging
    scraper = CszPhiladelphiaScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        # Simulate a VBO redirect / error page — no expected structural markers
        return "<html><body><p>Session expired. Please reload.</p></body></html>"

    monkeypatch.setattr(CszPhiladelphiaScraper, "fetch_html", fake_fetch_html)

    with caplog.at_level(logging.WARNING):
        targets = await scraper.collect_scraping_targets()

    assert targets == [], f"Expected empty list for stale session, got {targets}"
    assert any(
        "session key may be stale" in record.message
        for record in caplog.records
    ), f"Expected stale-session warning in logs; got: {[r.message for r in caplog.records]}"


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_instances(monkeypatch):
    """get_data() must parse all date-slider entries into CszPhillyShowInstances."""
    scraper = CszPhiladelphiaScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _date_slider_html_comedysportz()

    monkeypatch.setattr(CszPhiladelphiaScraper, "fetch_html", fake_fetch_html)

    target = f"2062|655663|ComedySportz"
    result = await scraper.get_data(target)

    assert isinstance(result, CszPhillyPageData)
    assert len(result.event_list) == 2
    assert all(isinstance(e, CszPhillyShowInstance) for e in result.event_list)
    assert result.event_list[0].event_name == "ComedySportz"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """
    Full pipeline smoke test: collect_scraping_targets() → get_data() per target.
    Asserts the combined event list is non-empty.
    """
    scraper = CszPhiladelphiaScraper(_club())

    date_slider_responses = {
        2062: _date_slider_html_comedysportz(),
        190467: _date_slider_html_single_date(),
    }

    async def fake_fetch_html(self, url: str) -> str:
        if "showevents" in url:
            return _showevents_html()
        # Date-slider requests include eid= in the URL
        for eid, html in date_slider_responses.items():
            if f"eid={eid}" in url:
                return html
        return ""

    monkeypatch.setattr(CszPhiladelphiaScraper, "fetch_html", fake_fetch_html)

    targets = await scraper.collect_scraping_targets()
    assert len(targets) > 0, "collect_scraping_targets() returned 0 targets"

    all_instances = []
    for target in targets:
        page_data = await scraper.get_data(target)
        if page_data:
            all_instances.extend(page_data.event_list)

    assert len(all_instances) > 0, (
        "Full pipeline produced 0 show instances — "
        "collect_scraping_targets() found targets but get_data() extracted nothing"
    )


@pytest.mark.asyncio
async def test_transformation_pipeline_produces_shows(monkeypatch):
    """transformation_pipeline must convert CszPhillyShowInstances into Show objects."""
    scraper = CszPhiladelphiaScraper(_club())

    async def fake_fetch_html(self, url: str) -> str:
        return _date_slider_html_comedysportz()

    monkeypatch.setattr(CszPhiladelphiaScraper, "fetch_html", fake_fetch_html)

    target = f"2062|655663|ComedySportz"
    page_data = await scraper.get_data(target)

    assert page_data is not None
    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, "transformation_pipeline produced 0 Show objects"
    for show in shows:
        assert show.name == "ComedySportz"
        assert show.date is not None
        assert show.club_id == 99
