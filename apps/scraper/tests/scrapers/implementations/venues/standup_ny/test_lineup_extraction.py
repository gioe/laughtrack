"""
Unit tests for StandupNY comedian lineup extraction.

Covers get_lineup_names() on StandupNYEvent and the transformer's lineup path.
"""

from laughtrack.core.entities.event.standup_ny import StandupNYEvent
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.standup_ny.transformer import StandupNYEventTransformer
from laughtrack.scrapers.implementations.venues.standup_ny.data import StandupNYPageData


def _make_event(**kwargs) -> StandupNYEvent:
    defaults = dict(id="1", name="Test Show", date="2026-03-10", start_time="20:00:00", ticket_url="")
    defaults.update(kwargs)
    return StandupNYEvent(**defaults)


def _make_club() -> Club:
    return Club(
        id=1,
        name="StandUp NY",
        address="",
        zip_code="10023",
        website="https://standupny.com",
        timezone="America/New_York",
        scraping_url="https://standupny.com/events",
        popularity=0,
        phone_number="",
        visible=True,
    )


class TestGetLineupNames:
    def test_returns_empty_when_no_data(self):
        event = _make_event()
        assert event.get_lineup_names() == []

    def test_graphql_promoter_only(self):
        event = _make_event(promoter="John Mulaney")
        assert event.get_lineup_names() == ["John Mulaney"]

    def test_graphql_support_only(self):
        event = _make_event(support="Dave Attell")
        assert event.get_lineup_names() == ["Dave Attell"]

    def test_graphql_promoter_and_support(self):
        event = _make_event(promoter="John Mulaney", support="Dave Attell")
        assert event.get_lineup_names() == ["John Mulaney", "Dave Attell"]

    def test_graphql_comma_separated(self):
        event = _make_event(promoter="John Mulaney, Amy Schumer", support="Dave Attell")
        assert event.get_lineup_names() == ["John Mulaney", "Amy Schumer", "Dave Attell"]

    def test_graphql_none_promoter_and_support_returns_empty(self):
        event = _make_event(promoter=None, support=None)
        assert event.get_lineup_names() == []

    def test_graphql_empty_string_returns_empty(self):
        event = _make_event(promoter="", support="")
        assert event.get_lineup_names() == []

    def test_venue_pilot_performers_dict(self):
        event = _make_event(
            promoter="GraphQL Name",
            venue_pilot_event={"performers": [{"name": "VP Comedian"}, {"displayName": "VP Comic 2"}]},
        )
        # VenuePilot takes priority
        assert event.get_lineup_names() == ["VP Comedian", "VP Comic 2"]

    def test_venue_pilot_performers_non_dict(self):
        event = _make_event(
            venue_pilot_event={"performers": ["Non-Dict Comic"]},
        )
        assert event.get_lineup_names() == ["Non-Dict Comic"]

    def test_venue_pilot_empty_performers_falls_through_to_graphql(self):
        event = _make_event(
            promoter="GraphQL Comic",
            venue_pilot_event={"performers": []},
        )
        # Empty performers list → fall through to GraphQL fields
        assert event.get_lineup_names() == ["GraphQL Comic"]

    def test_venue_pilot_blank_name_entries_fall_through_to_graphql(self):
        event = _make_event(
            promoter="GraphQL Comic",
            venue_pilot_event={"performers": [{"name": "  "}, {"displayName": ""}]},
        )
        # All VenuePilot entries produce blank names → fall through
        assert event.get_lineup_names() == ["GraphQL Comic"]

    def test_venue_pilot_no_performers_key_falls_through_to_graphql(self):
        event = _make_event(
            promoter="GraphQL Comic",
            venue_pilot_event={"startTime": "20:00:00"},
        )
        assert event.get_lineup_names() == ["GraphQL Comic"]

    def test_venue_pilot_performer_dict_missing_both_name_keys_falls_through_to_graphql(self):
        # Performer dicts with neither 'name' nor 'displayName' produce empty strings → filtered
        event = _make_event(
            promoter="GraphQL Comic",
            venue_pilot_event={"performers": [{"role": "host"}, {"role": "opener"}]},
        )
        assert event.get_lineup_names() == ["GraphQL Comic"]


class TestExtractLineupTransformer:
    def test_transformer_lineup_populated_from_graphql(self):
        club = _make_club()
        transformer = StandupNYEventTransformer(club)
        event = _make_event(promoter="Test Comic", start_time="2026-03-10T20:00:00")
        lineup = transformer._extract_lineup(event)
        assert len(lineup) == 1
        assert isinstance(lineup[0], Comedian)
        assert lineup[0].name == "Test Comic"

    def test_transformer_lineup_empty_when_no_data(self):
        club = _make_club()
        transformer = StandupNYEventTransformer(club)
        event = _make_event()
        lineup = transformer._extract_lineup(event)
        assert lineup == []
