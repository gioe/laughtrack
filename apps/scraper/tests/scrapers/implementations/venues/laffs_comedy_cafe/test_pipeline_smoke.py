"""
Pipeline smoke tests for LaffsComedyCafeScraper and LaffsComedyCafeEvent.

Exercises get_data() against mocked HTML that matches the actual
laffstucson.com/coming-soon.html structure, and unit-tests the
LaffsComedyCafeEvent.to_show() transformation path.
"""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.laffs_comedy_cafe import LaffsComedyCafeEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.venues.laffs_comedy_cafe.scraper import (
    LaffsComedyCafeScraper,
)
from laughtrack.scrapers.implementations.venues.laffs_comedy_cafe.data import (
    LaffsComedyCafePageData,
)

PAGE_URL = "https://www.laffstucson.com/coming-soon.html"


def _club() -> Club:
    _c = Club(id=999, name='Laffs Comedy Cafe', address='2900 E Broadway Blvd', website='https://www.laffstucson.com', popularity=0, zip_code='85716', phone_number='', visible=True, timezone='America/Phoenix')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url=PAGE_URL, external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _form_html(
    data_name: str = "Adam_Dominguez",
    action: str = "make-res.php",
    showtimes: list[str] | None = None,
) -> str:
    """Render a minimal Laffs reservation form matching the live HTML structure."""
    if showtimes is None:
        showtimes = [
            "Friday, April 10 @ 8 PM",
            "Friday, April 10 @ 10:30 PM",
            "Saturday, April 11 @ 7 PM",
            "Saturday, April 11 @ 9:30 PM",
        ]

    radio_html = "\n".join(
        f'<div><input type="radio" id="st_{i}" name="showtimeDateTime" value="v" required>'
        f'<label for="st_{i}">{st}</label></div>'
        for i, st in enumerate(showtimes)
    )

    return f"""
<div style="display:none;">
  <div class="form-modal" id="rz_1" uk-modal>
    <div class="uk-modal-dialog">
      <form class="rsvForm" action="{action}" method="post" data-name="{data_name}">
        <input type="hidden" name="formComicName" value="{data_name}">
        <div class="formComicShowtimes">
          <label class="chsTime">Choose Your Showtime</label>
          {radio_html}
        </div>
      </form>
    </div>
  </div>
</div>"""


def _page(forms: list[str]) -> str:
    """Wrap forms in a minimal page shell."""
    return f"""<html><body>
<div id="primary" class="page-coming-soon">
{''.join(forms)}
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# get_data() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    """get_data() parses a page and returns LaffsComedyCafePageData."""
    scraper = LaffsComedyCafeScraper(_club())
    html = _page([
        _form_html(data_name="Adam_Dominguez"),
        _form_html(
            data_name="Justin_Berkman",
            showtimes=[
                "Friday, April 17 @ 8 PM",
                "Saturday, April 18 @ 7 PM",
            ],
        ),
    ])

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return html

    monkeypatch.setattr(LaffsComedyCafeScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(PAGE_URL)

    assert isinstance(result, LaffsComedyCafePageData)
    assert len(result.event_list) == 6  # 4 + 2 showtimes
    names = {e.comedian_name for e in result.event_list}
    assert "Adam Dominguez" in names
    assert "Justin Berkman" in names


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_html(monkeypatch):
    """get_data() returns None when the page returns no HTML."""
    scraper = LaffsComedyCafeScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return ""

    monkeypatch.setattr(LaffsComedyCafeScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(PAGE_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_events(monkeypatch):
    """get_data() returns None when the page contains no forms."""
    scraper = LaffsComedyCafeScraper(_club())

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return "<html><body><p>No upcoming shows</p></body></html>"

    monkeypatch.setattr(LaffsComedyCafeScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(PAGE_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_skips_ticket_forms(monkeypatch):
    """get_data() only processes reservation forms, not ticket purchase forms."""
    scraper = LaffsComedyCafeScraper(_club())
    html = _page([
        _form_html(data_name="Adam_Dominguez", action="make-res.php"),
        _form_html(data_name="Adam_Dominguez", action="tix2.php"),
    ])

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return html

    monkeypatch.setattr(LaffsComedyCafeScraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(PAGE_URL)

    assert isinstance(result, LaffsComedyCafePageData)
    # Only 4 events (from make-res.php), not 8
    assert len(result.event_list) == 4


# ---------------------------------------------------------------------------
# collect_scraping_targets() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_returns_single_url():
    """collect_scraping_targets() returns only the coming-soon page URL."""
    scraper = LaffsComedyCafeScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert "laffstucson.com" in targets[0]


# ---------------------------------------------------------------------------
# LaffsComedyCafeEvent.to_show() unit tests
# ---------------------------------------------------------------------------


def _make_event(
    comedian_name: str = "Adam Dominguez",
    showtime_str: str = "Friday, April 10 @ 8 PM",
    ticket_url: str = PAGE_URL,
) -> LaffsComedyCafeEvent:
    return LaffsComedyCafeEvent(
        comedian_name=comedian_name,
        showtime_str=showtime_str,
        ticket_url=ticket_url,
    )


def test_to_show_returns_show_with_correct_name():
    """to_show() produces a Show with the comedian name."""
    event = _make_event()
    show = event.to_show(_club())
    assert isinstance(show, Show)
    assert show.name == "Adam Dominguez"


def test_to_show_parses_datetime_correctly():
    """to_show() parses 'Friday, April 10 @ 8 PM' into a correct datetime."""
    event = _make_event(showtime_str="Friday, April 10 @ 8 PM")
    show = event.to_show(_club())
    assert show is not None
    assert show.date.hour == 20
    assert show.date.minute == 0
    assert show.date.month == 4
    assert show.date.day == 10


def test_to_show_parses_half_hour_time():
    """to_show() handles '10:30 PM' time format."""
    event = _make_event(showtime_str="Friday, April 10 @ 10:30 PM")
    show = event.to_show(_club())
    assert show is not None
    assert show.date.hour == 22
    assert show.date.minute == 30


def test_to_show_creates_ticket():
    """to_show() creates a fallback ticket with the page URL."""
    event = _make_event()
    show = event.to_show(_club())
    assert show is not None
    assert len(show.tickets) == 1
    assert "laffstucson.com" in show.tickets[0].purchase_url


def test_to_show_returns_none_for_empty_name():
    """to_show() returns None when comedian_name is empty."""
    event = _make_event(comedian_name="")
    show = event.to_show(_club())
    assert show is None


def test_to_show_returns_none_for_bad_showtime():
    """to_show() returns None when showtime cannot be parsed."""
    event = _make_event(showtime_str="TBD")
    show = event.to_show(_club())
    assert show is None


def test_to_show_uses_phoenix_timezone():
    """to_show() localizes datetime to America/Phoenix (no DST)."""
    event = _make_event(showtime_str="Friday, April 10 @ 8 PM")
    show = event.to_show(_club())
    assert show is not None
    assert str(show.date.tzinfo) == "America/Phoenix"


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------


def test_extractor_extracts_multiple_comedians():
    """Extractor produces events for each comedian on the page."""
    from laughtrack.scrapers.implementations.venues.laffs_comedy_cafe.extractor import (
        LaffsComedyCafeExtractor,
    )

    html = _page([
        _form_html(data_name="Adam_Dominguez", showtimes=["Friday, April 10 @ 8 PM"]),
        _form_html(data_name="Todd_Royce", showtimes=["Friday, April 24 @ 8 PM"]),
    ])

    events = LaffsComedyCafeExtractor.extract_events(html)
    assert len(events) == 2
    names = {e.comedian_name for e in events}
    assert names == {"Adam Dominguez", "Todd Royce"}


def test_extractor_skips_non_showtime_labels():
    """Extractor ignores labels that don't match showtime pattern (e.g. seating)."""
    from laughtrack.scrapers.implementations.venues.laffs_comedy_cafe.extractor import (
        LaffsComedyCafeExtractor,
    )

    html = _page([
        _form_html(
            data_name="Test_Comic",
            showtimes=["Friday, April 10 @ 8 PM"],
        ),
    ])
    # Add a seating label that should be ignored
    html = html.replace(
        "</form>",
        '<div><label for="seat">General - $15</label></div></form>',
    )

    events = LaffsComedyCafeExtractor.extract_events(html)
    assert len(events) == 1
    assert events[0].showtime_str == "Friday, April 10 @ 8 PM"


def test_extractor_returns_empty_for_no_html():
    """Extractor returns empty list for empty HTML."""
    from laughtrack.scrapers.implementations.venues.laffs_comedy_cafe.extractor import (
        LaffsComedyCafeExtractor,
    )

    assert LaffsComedyCafeExtractor.extract_events("") == []


def test_extractor_handles_name_with_underscores():
    """Extractor converts data-name underscores to spaces."""
    from laughtrack.scrapers.implementations.venues.laffs_comedy_cafe.extractor import (
        LaffsComedyCafeExtractor,
    )

    html = _page([
        _form_html(
            data_name="Mary_Jane_Smith",
            showtimes=["Saturday, April 11 @ 7 PM"],
        ),
    ])

    events = LaffsComedyCafeExtractor.extract_events(html)
    assert len(events) == 1
    assert events[0].comedian_name == "Mary Jane Smith"


# ---------------------------------------------------------------------------
# Transformation pipeline tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_transforms_events_to_shows(monkeypatch):
    """Full pipeline: HTML → events → shows."""
    scraper = LaffsComedyCafeScraper(_club())
    html = _page([
        _form_html(
            data_name="Adam_Dominguez",
            showtimes=["Friday, April 10 @ 8 PM"],
        ),
    ])

    async def fake_fetch_html(self, url: str, **kwargs) -> str:
        return html

    monkeypatch.setattr(LaffsComedyCafeScraper, "fetch_html", fake_fetch_html)

    page_data = await scraper.get_data(PAGE_URL)
    assert page_data is not None

    shows = scraper.transformation_pipeline.transform(page_data)
    assert len(shows) == 1
    assert isinstance(shows[0], Show)
    assert shows[0].name == "Adam Dominguez"
