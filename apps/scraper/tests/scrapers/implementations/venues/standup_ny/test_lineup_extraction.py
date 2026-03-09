"""
Unit tests for StandupNY comedian lineup extraction.

Covers get_lineup_names() on StandupNYEvent and the transformer's lineup path.
"""

from unittest.mock import patch

from laughtrack.core.entities.event.standup_ny import StandupNYEvent
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.standup_ny.transformer import StandupNYEventTransformer


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

    def test_venue_pilot_artists_dict(self):
        # Live VenuePilot data uses "artists" key with {"name": str, "links": [...]} entries
        event = _make_event(
            promoter="GraphQL Name",
            venue_pilot_event={"artists": [{"name": "VP Comedian", "links": []}, {"name": "VP Comic 2", "links": []}]},
        )
        # VenuePilot takes priority
        assert event.get_lineup_names() == ["VP Comedian", "VP Comic 2"]

    def test_venue_pilot_artists_non_dict(self):
        event = _make_event(
            venue_pilot_event={"artists": ["Non-Dict Comic"]},
        )
        assert event.get_lineup_names() == ["Non-Dict Comic"]

    def test_venue_pilot_empty_artists_falls_through_to_graphql(self):
        # Empty artists array is common in live data → fall through to GraphQL fields
        event = _make_event(
            promoter="GraphQL Comic",
            venue_pilot_event={"artists": []},
        )
        assert event.get_lineup_names() == ["GraphQL Comic"]

    def test_venue_pilot_blank_name_entries_fall_through_to_graphql(self):
        event = _make_event(
            promoter="GraphQL Comic",
            venue_pilot_event={"artists": [{"name": "  "}, {"name": ""}]},
        )
        # All VenuePilot entries produce blank names → fall through
        assert event.get_lineup_names() == ["GraphQL Comic"]

    def test_venue_pilot_no_artists_key_falls_through_to_graphql(self):
        event = _make_event(
            promoter="GraphQL Comic",
            venue_pilot_event={"startTime": "20:00:00"},
        )
        assert event.get_lineup_names() == ["GraphQL Comic"]

    def test_venue_pilot_artist_dict_missing_name_key_falls_through_to_graphql(self):
        # Artist dicts without a 'name' key produce empty strings → filtered
        event = _make_event(
            promoter="GraphQL Comic",
            venue_pilot_event={"artists": [{"links": []}, {"links": []}]},
        )
        assert event.get_lineup_names() == ["GraphQL Comic"]


class TestGetLineupNamesWarning:
    """Logger.warn is emitted when venue_pilot_event is present but artists yield no names."""

    def test_warn_on_empty_artists_array(self):
        event = _make_event(
            id="evt-42",
            promoter="GraphQL Comic",
            venue_pilot_event={"artists": []},
        )
        with patch("laughtrack.core.entities.event.standup_ny.Logger") as mock_logger:
            result = event.get_lineup_names()
        mock_logger.warn.assert_called_once()
        assert "evt-42" in mock_logger.warn.call_args[0][0]
        assert result == ["GraphQL Comic"]

    def test_warn_on_blank_name_entries(self):
        event = _make_event(
            id="evt-99",
            promoter="GraphQL Comic",
            venue_pilot_event={"artists": [{"name": "  "}, {"name": ""}]},
        )
        with patch("laughtrack.core.entities.event.standup_ny.Logger") as mock_logger:
            result = event.get_lineup_names()
        mock_logger.warn.assert_called_once()
        assert "evt-99" in mock_logger.warn.call_args[0][0]
        assert result == ["GraphQL Comic"]

    def test_warn_on_no_artists_key(self):
        event = _make_event(
            id="evt-7",
            promoter="GraphQL Comic",
            venue_pilot_event={"startTime": "20:00:00"},
        )
        with patch("laughtrack.core.entities.event.standup_ny.Logger") as mock_logger:
            result = event.get_lineup_names()
        mock_logger.warn.assert_called_once()
        assert "evt-7" in mock_logger.warn.call_args[0][0]
        assert result == ["GraphQL Comic"]

    def test_no_warn_when_artists_return_names(self):
        event = _make_event(
            id="evt-1",
            venue_pilot_event={"artists": [{"name": "VP Comedian"}]},
        )
        with patch("laughtrack.core.entities.event.standup_ny.Logger") as mock_logger:
            event.get_lineup_names()
        mock_logger.warn.assert_not_called()

    def test_no_warn_when_no_venue_pilot_event(self):
        event = _make_event(id="evt-2", promoter="GraphQL Comic")
        with patch("laughtrack.core.entities.event.standup_ny.Logger") as mock_logger:
            event.get_lineup_names()
        mock_logger.warn.assert_not_called()


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
