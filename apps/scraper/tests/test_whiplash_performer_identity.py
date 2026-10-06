"""Whiplash's reviewed event labels are not global comedian-name exclusions."""

from copy import deepcopy

import pytest

from laughtrack.core.clients.seatengine.client import SeatEngineClient
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.seatengine.transformer import SeatEngineEventTransformer


def transformer(club_id=1347, source_id=591, venue_id=650):
    club = Club(
        id=club_id,
        name="Whiplash Comedy",
        address="650 North Avenue",
        website="https://whiplashcomedy.com",
        popularity=0,
        zip_code="30308",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    club.active_scraping_source = ScrapingSource(
        id=source_id,
        club_id=club_id,
        platform="seatengine",
        scraper_key="seatengine",
        seatengine_id=venue_id,
        source_url="https://whiplashcomedy.com",
    )
    club.scraping_sources = [club.active_scraping_source]
    client = SeatEngineClient(club)
    client.venue_website = club.website
    return SeatEngineEventTransformer(club, client), client


def payload(title="Whiplash Comedy Night"):
    return dict(
        id=123,
        start_date_time="2027-05-15T20:00:00-04:00",
        sold_out=False,
        inventories=[dict(price=2500)],
        venue_id=650,
        event=dict(
            name=title,
            description="Public comedy performance",
            labels=[],
            talents=[
                dict(name="Grand Opening"),
                dict(name="Summer 2026"),
                dict(name="Heavy Hitters"),
                dict(name="Alice Smith"),
            ],
        ),
    )


def test_reviewed_whiplash_labels_are_removed_before_real_conversion():
    transform, _ = transformer()
    raw = payload()
    before = deepcopy(raw)
    show = transform.transform_to_show(raw)
    assert show and [c.name for c in show.lineup] == ["Alice Smith"]
    assert raw == before


@pytest.mark.parametrize("changes", [dict(club_id=9), dict(source_id=999), dict(venue_id=9)])
def test_other_source_identities_keep_the_same_named_performers(changes):
    transform, _ = transformer(**changes)
    show = transform.transform_to_show(payload())
    assert show and [c.name for c in show.lineup] == ["Grand Opening", "Summer 2026", "Heavy Hitters", "Alice Smith"]


def test_case_spacing_only_normalization_and_repeat_conversion_preserve_show():
    transform, client = transformer()
    raw = payload()
    raw["event"]["talents"] = [
        dict(name="  GRAND   Opening "),
        dict(name="summer\t2026"),
        dict(name="HEAVY Hitters"),
        dict(name="Alice Smith"),
        dict(name="Heavy Hitters Jr"),
    ]
    before = deepcopy(raw)
    baseline = client.create_show(raw)
    first = transform.transform_to_show(raw)
    second = transform.transform_to_show(raw)
    assert first and second and baseline
    assert [c.name for c in first.lineup] == ["Alice Smith", "Heavy Hitters Jr"]
    assert first.lineup == second.lineup
    for field in (
        "name",
        "date",
        "club_id",
        "room",
        "description",
        "show_page_url",
        "tickets",
        "timezone",
        "tickets_complete",
    ):
        assert getattr(first, field) == getattr(baseline, field) == getattr(second, field)
    assert raw == before


@pytest.mark.parametrize("title", ["Grand Opening", "Summer 2026", "Heavy Hitters"])
def test_label_only_lineup_does_not_fall_back_to_event_title(title):
    transform, _ = transformer()
    raw = payload(title)
    raw["event"]["talents"] = [dict(name=title)]
    show = transform.transform_to_show(raw)
    assert show and show.lineup == [] and show.name == title and show.tickets


@pytest.mark.parametrize("scope", ["root", "event", "venue_object"])
def test_explicit_api_venue_conflict_holds_show_and_prevents_clean_reconciliation(scope):
    transform, client = transformer()
    raw = payload()
    if scope == "root":
        raw["venue_id"] = 999
    elif scope == "event":
        raw["event"]["venue_id"] = 999
    else:
        raw["venue"] = {"id": 999}
    before = deepcopy(raw)
    assert transform.transform_to_show(raw) is None
    assert client.routing_errors and raw == before


def test_reviewed_hidden_identities_are_suppressed_across_sources_on_repeat():
    from unittest.mock import MagicMock

    from laughtrack.core.entities.comedian.handler import ComedianHandler
    from laughtrack.core.entities.comedian.model import Comedian
    from sql.comedian_queries import ComedianQueries

    names = ["Grand Opening", "Summer 2026", "Heavy Hitters", "Alice Smith"]
    candidates = [Comedian(name) for name in names]
    handler = ComedianHandler.__new__(ComedianHandler)

    def read(query, params, return_results=False):
        assert return_results is True
        assert params == ([name.lower() for name in names],)
        if query == ComedianQueries.GET_HIDDEN_COMEDIAN_NAMES:
            return [{"name": name} for name in names[:3]]
        assert query == ComedianQueries.GET_DENIED_NAMES
        return []  # Hiding existing identities requires no global deny entries.

    handler.execute_with_cursor = MagicMock(side_effect=read)
    for _ in range(2):
        assert handler._filter_denied_comedians(candidates) == [candidates[-1]]
    assert handler.execute_with_cursor.call_count == 4
    assert [candidate.name for candidate in candidates] == names
