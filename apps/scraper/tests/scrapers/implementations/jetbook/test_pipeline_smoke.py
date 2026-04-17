"""
Pipeline smoke tests for JetBookScraper, JetBookExtractor, and JetBookEvent.

Covers:
- get_data() against mocked msearch response bodies
- JetBookExtractor filtering rules (visibility flags, future-only, dedup)
- JetBookEvent.to_show() transformation
- Transformation pipeline end-to-end (required by CONTRIBUTING.md)
- A smoke test against the real captured msearch fixture to ensure the
  shape of Bubble.io's Elasticsearch response has not drifted

Per convention #11, test helpers default to a far-future start timestamp
(2099-01-01) so the extractor's "skip past events" filter never turns a
passing test into a time-bomb failure.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.event.jetbook import JetBookEvent
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.jetbook.data import JetBookPageData
from laughtrack.scrapers.implementations.jetbook.extractor import JetBookExtractor
from laughtrack.scrapers.implementations.jetbook.scraper import JetBookScraper

FIXTURE_DIR = Path(__file__).parent / "fixtures"
IFRAME_URL = "https://jetbook.co/o_iframe/improv-collective-srzaf"

# Far-future epoch ms — 2099-01-01T00:00:00Z. Prevents the extractor's
# "future-only" filter from rejecting fixtures as time passes.
FAR_FUTURE_MS = int(
    datetime(2099, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
)


def _club() -> Club:
    return Club(
        id=794,
        name="The Improv Collective",
        address="1215 Baker Street",
        website="https://improvcollective.fun",
        scraping_url=IFRAME_URL,
        popularity=0,
        zip_code="92626",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )


def _event_source(
    *,
    record_id: str = "evt-001",
    name: str = "Tan Sedan",
    slug: str = "tan-sedan-abc1",
    start_ms: int = FAR_FUTURE_MS,
    visble: bool = True,
    ticket_page_visible: bool = True,
    typevisible: str = "visible",
    description: str = "Improv night at the Improv Collective.",
) -> dict:
    """Build a minimal event _source matching the Bubble.io schema."""
    return {
        "_id": record_id,
        "name_text": name,
        "Slug": slug,
        "parsedate_start_date": start_ms,
        "description_text": description,
        "visble_boolean": visble,
        "ticket_page_visible_boolean": ticket_page_visible,
        "typevisible_option_typevisible": typevisible,
    }


def _msearch_body(sources: list[dict]) -> str:
    """Wrap event _source dicts in the full Bubble msearch response shape."""
    hits = [
        {"_id": src["_id"], "_source": src}
        for src in sources
    ]
    return json.dumps({"responses": [{"hits": {"hits": hits}}]})


# ---------------------------------------------------------------------------
# JetBookExtractor.parse_msearch_responses tests
# ---------------------------------------------------------------------------


def test_parse_msearch_returns_bookable_events():
    body = _msearch_body([_event_source()])
    events = JetBookExtractor.parse_msearch_responses([body])

    assert len(events) == 1
    assert events[0].title == "Tan Sedan"
    assert events[0].slug == "tan-sedan-abc1"
    assert events[0].start_time_ms == FAR_FUTURE_MS


def test_parse_msearch_filters_hidden_by_visble_boolean():
    body = _msearch_body([_event_source(visble=False)])
    assert JetBookExtractor.parse_msearch_responses([body]) == []


def test_parse_msearch_filters_hidden_by_ticket_page_visible():
    body = _msearch_body([_event_source(ticket_page_visible=False)])
    assert JetBookExtractor.parse_msearch_responses([body]) == []


def test_parse_msearch_filters_by_typevisible():
    body = _msearch_body([_event_source(typevisible="hidden")])
    assert JetBookExtractor.parse_msearch_responses([body]) == []


def test_parse_msearch_filters_past_events_by_default():
    past_ms = 1_000_000_000  # 2001
    body = _msearch_body([_event_source(start_ms=past_ms)])
    assert JetBookExtractor.parse_msearch_responses([body]) == []


def test_parse_msearch_includes_past_when_flag_set():
    past_ms = 1_000_000_000
    body = _msearch_body([_event_source(start_ms=past_ms)])
    events = JetBookExtractor.parse_msearch_responses(
        [body], include_past=True
    )
    assert len(events) == 1


def test_parse_msearch_dedupes_by_record_id():
    """Events repeated across multiple msearch batches dedupe by _id."""
    body1 = _msearch_body([_event_source(record_id="evt-dup")])
    body2 = _msearch_body([_event_source(record_id="evt-dup")])
    events = JetBookExtractor.parse_msearch_responses([body1, body2])
    assert len(events) == 1


def test_parse_msearch_skips_non_event_records():
    """Venue/ticket/v2_venues records ride in the same response — ignore them."""
    not_an_event = {
        "_id": "venue-999",
        "name_text": "A Venue",
        "Slug": "some-venue",
        # Missing parsedate_start_date — not an event
    }
    body = json.dumps({"responses": [{"hits": {"hits": [
        {"_id": "venue-999", "_source": not_an_event},
        {"_id": "evt-1", "_source": _event_source(record_id="evt-1")},
    ]}}]})
    events = JetBookExtractor.parse_msearch_responses([body])
    assert len(events) == 1
    assert events[0].title == "Tan Sedan"


def test_parse_msearch_sorts_by_start_time():
    later = FAR_FUTURE_MS + 86_400_000   # +1 day
    earlier = FAR_FUTURE_MS
    body = _msearch_body([
        _event_source(record_id="b", name="Later", slug="later-x", start_ms=later),
        _event_source(record_id="a", name="Earlier", slug="earlier-x", start_ms=earlier),
    ])
    events = JetBookExtractor.parse_msearch_responses([body])
    assert [e.title for e in events] == ["Earlier", "Later"]


def test_parse_msearch_ignores_malformed_json():
    events = JetBookExtractor.parse_msearch_responses(["not json at all"])
    assert events == []


def test_parse_msearch_handles_empty_input():
    assert JetBookExtractor.parse_msearch_responses([]) == []
    assert JetBookExtractor.parse_msearch_responses([""]) == []


def test_build_ticket_url():
    assert (
        JetBookExtractor.build_ticket_url("some-slug")
        == "https://jetbook.co/e/some-slug"
    )
    assert JetBookExtractor.build_ticket_url("") is None
    assert JetBookExtractor.build_ticket_url("  ") is None


# ---------------------------------------------------------------------------
# Fixture-based test — ensures Bubble.io response shape hasn't changed
# ---------------------------------------------------------------------------


def test_real_msearch_fixture_parses():
    """Parse a real captured /elasticsearch/msearch response body.

    Uses include_past=True so the test doesn't become a time bomb once the
    real event's date passes.
    """
    fixture_path = FIXTURE_DIR / "msearch_sample.json"
    body = fixture_path.read_text()
    events = JetBookExtractor.parse_msearch_responses(
        [body], include_past=True
    )
    assert len(events) == 1
    ev = events[0]
    assert ev.title
    assert ev.slug
    assert ev.start_time_ms > 0


# ---------------------------------------------------------------------------
# JetBookScraper.get_data tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_with_events(monkeypatch):
    scraper = JetBookScraper(_club())
    body = _msearch_body([_event_source()])

    async def fake_capture(self, url: str) -> list[str]:
        return [body]

    monkeypatch.setattr(
        JetBookScraper, "_capture_msearch_responses", fake_capture
    )

    result = await scraper.get_data(IFRAME_URL)
    assert isinstance(result, JetBookPageData)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Tan Sedan"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_responses(monkeypatch):
    scraper = JetBookScraper(_club())

    async def fake_capture(self, url: str) -> list[str]:
        return []

    monkeypatch.setattr(
        JetBookScraper, "_capture_msearch_responses", fake_capture
    )

    assert await scraper.get_data(IFRAME_URL) is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_no_bookable_events(monkeypatch):
    scraper = JetBookScraper(_club())
    # All events hidden
    body = _msearch_body([_event_source(visble=False)])

    async def fake_capture(self, url: str) -> list[str]:
        return [body]

    monkeypatch.setattr(
        JetBookScraper, "_capture_msearch_responses", fake_capture
    )

    assert await scraper.get_data(IFRAME_URL) is None


@pytest.mark.asyncio
async def test_get_data_returns_none_on_capture_exception(monkeypatch):
    scraper = JetBookScraper(_club())

    async def fake_capture(self, url: str) -> list[str]:
        raise RuntimeError("Playwright exploded")

    monkeypatch.setattr(
        JetBookScraper, "_capture_msearch_responses", fake_capture
    )

    assert await scraper.get_data(IFRAME_URL) is None


# ---------------------------------------------------------------------------
# collect_scraping_targets — inherited default should return [scraping_url]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_targets_uses_scraping_url():
    scraper = JetBookScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert len(targets) == 1
    assert targets[0].endswith("improv-collective-srzaf")


# ---------------------------------------------------------------------------
# JetBookEvent.to_show unit tests
# ---------------------------------------------------------------------------


def _make_event(
    title: str = "Tan Sedan",
    slug: str = "tan-sedan-abc1",
    start_ms: int = FAR_FUTURE_MS,
    description: str = "",
) -> JetBookEvent:
    return JetBookEvent(
        title=title,
        start_time_ms=start_ms,
        slug=slug,
        description=description,
    )


def test_to_show_returns_show_with_correct_name():
    show = _make_event(title="Tan Sedan").to_show(_club())
    assert show is not None
    assert show.name == "Tan Sedan"


def test_to_show_builds_ticket_url_from_slug():
    show = _make_event(slug="my-event-xy").to_show(_club())
    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://jetbook.co/e/my-event-xy"


def test_to_show_parses_start_time_in_club_timezone():
    """Unix ms → localized datetime. Compare via UTC to avoid DST ambiguity
    (pytz lacks far-future DST rules, so LA may be interpreted as PST/PDT
    depending on the year's tzdata)."""
    start_utc = datetime(2099, 7, 4, 22, 0, tzinfo=timezone.utc)
    show = _make_event(
        start_ms=int(start_utc.timestamp() * 1000)
    ).to_show(_club())

    assert show is not None
    assert show.date.tzinfo is not None
    # Round-tripping back to UTC must match the original instant exactly.
    assert show.date.astimezone(timezone.utc) == start_utc
    # Timezone name should reflect the club's configured timezone.
    assert "Los_Angeles" in str(show.date.tzinfo)


def test_to_show_returns_none_when_title_missing():
    assert _make_event(title="").to_show(_club()) is None


def test_to_show_returns_none_when_slug_missing():
    assert _make_event(slug="").to_show(_club()) is None


def test_to_show_returns_none_when_start_ms_zero():
    assert _make_event(start_ms=0).to_show(_club()) is None


def test_to_show_passes_description_through():
    show = _make_event(description="A hilarious improv show.").to_show(_club())
    assert show is not None
    # The factory may reformat description, but our non-empty input should survive
    assert show.description
    assert "improv" in show.description.lower()


# ---------------------------------------------------------------------------
# Transformation pipeline smoke test (required by CONTRIBUTING.md)
# ---------------------------------------------------------------------------


def test_transformation_pipeline_produces_shows():
    """Regression: transformation_pipeline.transform() must return Shows."""
    scraper = JetBookScraper(_club())
    events = [
        _make_event(title="Event A", slug="event-a"),
        _make_event(title="Event B", slug="event-b", start_ms=FAR_FUTURE_MS + 86_400_000),
    ]
    page_data = JetBookPageData(event_list=events)

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) == 2, (
        "transformation_pipeline.transform() returned the wrong count from "
        "JetBookPageData — check JetBookEventTransformer.can_transform() and "
        "that the transformer is registered with the correct generic type."
    )
    assert all(isinstance(s, Show) for s in shows)


# ---------------------------------------------------------------------------
# Scraper key registration smoke test
# ---------------------------------------------------------------------------


def test_scraper_registers_jetbook_key():
    """The resolver must pick up the `jetbook` key via auto-discovery."""
    from laughtrack.app.scraper_resolver import ScraperResolver

    resolver = ScraperResolver()
    assert resolver.get("jetbook") is JetBookScraper
