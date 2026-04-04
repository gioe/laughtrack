"""
Tests for club timezone enrichment.

Covers:
1. timezone_from_address() — parses state and returns correct IANA zone
2. ClubHandler.enrich_timezones() — fetches null-timezone clubs, resolves, updates
3. Idempotency — clubs already having a timezone are not passed to UPDATE
"""

import sys

import pytest
from unittest.mock import MagicMock, patch

from _entities_test_helpers import _load_module, _stub


_stub("laughtrack.foundation.protocols.database_entity", DatabaseEntity=object)
_stub("laughtrack.foundation.protocols", as_package=True, DatabaseEntity=object)
_stub("laughtrack.foundation.infrastructure.logger.logger", Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure.logger", as_package=True, Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure.database.operation", DatabaseOperationLogger=MagicMock())
_stub("laughtrack.foundation.infrastructure.database", as_package=True, DatabaseOperationLogger=MagicMock())
_stub("laughtrack.foundation.infrastructure", as_package=True, Logger=MagicMock())
from typing import TypeVar as _TypeVar
_T = _TypeVar("T")
_stub("laughtrack.foundation.models.types", T=_T, JSONDict=dict)
_stub("laughtrack.foundation.models", as_package=True, T=_T)
_stub("laughtrack.foundation", as_package=True, DatabaseEntity=object)
_stub("laughtrack.adapters.db", create_connection=MagicMock())
_stub("laughtrack.adapters", as_package=True, create_connection=MagicMock())

_club_model_mod = _load_module(
    "src/laughtrack/core/entities/club/model.py",
    "laughtrack.core.entities.club.model_direct",
)
Club = _club_model_mod.Club

_club_queries_mod = _load_module("sql/club_queries.py", "sql.club_queries_direct")
ClubQueries = _club_queries_mod.ClubQueries

_base_handler_mod = _load_module(
    "src/laughtrack/core/data/base_handler.py",
    "laughtrack.core.data.base_handler_direct",
)
BaseDatabaseHandler = _base_handler_mod.BaseDatabaseHandler

sys.modules["laughtrack.core.entities.club.model"] = _club_model_mod
sys.modules["laughtrack.core.data.base_handler"] = _base_handler_mod
sys.modules["sql.club_queries"] = _club_queries_mod

# Load timezone_lookup before ClubHandler (ClubHandler imports it at module level)
_tz_lookup_mod = _load_module(
    "src/laughtrack/utilities/domain/club/timezone_lookup.py",
    "laughtrack.utilities.domain.club.timezone_lookup",
)
timezone_from_address = _tz_lookup_mod.timezone_from_address
timezone_from_state = _tz_lookup_mod.timezone_from_state
parse_city_state_from_address = _tz_lookup_mod.parse_city_state_from_address

sys.modules["laughtrack.utilities.domain.club.timezone_lookup"] = _tz_lookup_mod

_club_handler_mod = _load_module(
    "src/laughtrack/core/entities/club/handler.py",
    "laughtrack.core.entities.club.handler_direct",
)
ClubHandler = _club_handler_mod.ClubHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_club_row(**overrides):
    defaults = {
        "id": 10,
        "name": "Comedy Cellar",
        "address": "117 MacDougal St, New York, NY",
        "website": "",
        "scraping_url": "www.eventbrite.com",
        "popularity": 0,
        "zip_code": "10012",
        "city": None,
        "state": None,
        "phone_number": "",
        "timezone": None,
        "visible": True,
        "scraper": "eventbrite",
        "eventbrite_id": "eb-001",
        "ticketmaster_id": None,
        "seatengine_id": None,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Tests: timezone_from_address
# ---------------------------------------------------------------------------

class TestTimezoneFromAddress:
    def test_ny_address_returns_eastern(self):
        assert timezone_from_address("117 MacDougal St, New York, NY") == "America/New_York"

    def test_ca_address_returns_pacific(self):
        assert timezone_from_address("8001 Sunset Blvd, Los Angeles, CA") == "America/Los_Angeles"

    def test_il_address_returns_central(self):
        assert timezone_from_address("230 W North Ave, Chicago, IL") == "America/Chicago"

    def test_co_address_returns_mountain(self):
        assert timezone_from_address("1301 Glenarm Pl, Denver, CO") == "America/Denver"

    def test_state_with_zip_suffix(self):
        # "NY 10001" as the last segment
        assert timezone_from_address("123 Main St, New York, NY 10001") == "America/New_York"

    def test_unknown_state_returns_none(self):
        assert timezone_from_address("Some Place, Abroad, XX") is None

    def test_empty_string_returns_none(self):
        assert timezone_from_address("") is None

    def test_none_returns_none(self):
        assert timezone_from_address(None) is None

    def test_single_segment_no_state_returns_none(self):
        assert timezone_from_address("No State Here") is None


# ---------------------------------------------------------------------------
# Tests: ClubHandler.enrich_timezones
# ---------------------------------------------------------------------------

class TestEnrichTimezones:
    def test_updates_club_with_resolved_timezone(self):
        """A club whose address resolves to a timezone is batch-updated in the DB."""
        row = _make_club_row(id=10, name="Comedy Cellar", address="117 MacDougal St, New York, NY")
        handler = ClubHandler()

        with patch.object(handler, "execute_with_cursor", return_value=[row]), \
             patch.object(handler, "execute_batch_operation", return_value=[{"id": 10}]) as mock_batch:
            count = handler.enrich_timezones(scraper="eventbrite")

        assert count == 1
        mock_batch.assert_called_once_with(
            ClubQueries.BATCH_UPDATE_CLUB_TIMEZONES,
            [(10, "America/New_York")],
            return_results=True,
        )

    def test_skips_club_with_unresolvable_timezone(self):
        """A club whose address has no recognisable state skips the batch UPDATE entirely."""
        row = _make_club_row(id=20, name="Mystery Club", address="Somewhere, Abroad, XX")
        handler = ClubHandler()

        with patch.object(handler, "execute_with_cursor", return_value=[row]), \
             patch.object(handler, "execute_batch_operation") as mock_batch:
            count = handler.enrich_timezones(scraper="eventbrite")

        assert count == 0
        mock_batch.assert_not_called()

    def test_returns_zero_when_no_clubs_found(self):
        """Returns 0 and does not call batch UPDATE when the SELECT returns nothing."""
        handler = ClubHandler()

        with patch.object(handler, "execute_with_cursor", return_value=[]), \
             patch.object(handler, "execute_batch_operation") as mock_batch:
            count = handler.enrich_timezones(scraper="eventbrite")

        assert count == 0
        mock_batch.assert_not_called()

    def test_select_query_uses_scraper_param(self):
        """GET_CLUBS_WITH_NULL_TIMEZONE is called with the scraper argument."""
        handler = ClubHandler()

        with patch.object(handler, "execute_with_cursor", return_value=[]) as mock_exec:
            handler.enrich_timezones(scraper="seatengine")

        select_call = mock_exec.call_args_list[0]
        assert select_call[0][0] == ClubQueries.GET_CLUBS_WITH_NULL_TIMEZONE
        assert select_call[0][1] == ("seatengine",)

    def test_idempotent_update_uses_null_guard(self):
        """BATCH UPDATE query includes 'AND c.timezone IS NULL' so it won't touch set values."""
        assert "timezone IS NULL" in ClubQueries.BATCH_UPDATE_CLUB_TIMEZONES

    def test_does_not_count_club_when_update_null_guard_fires(self):
        """If batch UPDATE returns empty (another process already set timezone), count is 0."""
        row = _make_club_row(id=10, address="117 MacDougal St, New York, NY")
        handler = ClubHandler()

        with patch.object(handler, "execute_with_cursor", return_value=[row]), \
             patch.object(handler, "execute_batch_operation", return_value=[]):
            count = handler.enrich_timezones(scraper="eventbrite")

        assert count == 0

    def test_multiple_clubs_all_updated(self):
        """All clubs with resolvable addresses are updated in a single batch call."""
        rows = [
            _make_club_row(id=1, address="117 MacDougal St, New York, NY"),
            _make_club_row(id=2, address="8001 Sunset Blvd, Los Angeles, CA"),
        ]
        handler = ClubHandler()

        with patch.object(handler, "execute_with_cursor", return_value=rows), \
             patch.object(handler, "execute_batch_operation", return_value=[{"id": 1}, {"id": 2}]) as mock_batch:
            count = handler.enrich_timezones(scraper="eventbrite")

        assert count == 2
        # Single batch call — not one per club
        mock_batch.assert_called_once()
        items = mock_batch.call_args[0][1]
        assert set(items) == {(1, "America/New_York"), (2, "America/Los_Angeles")}


# ---------------------------------------------------------------------------
# Tests: parse_city_state_from_address
# ---------------------------------------------------------------------------

class TestParseCityStateFromAddress:
    def test_standard_address_returns_city_and_state(self):
        city, state = parse_city_state_from_address("117 MacDougal St, New York, NY")
        assert city == "New York"
        assert state == "NY"

    def test_address_with_zip_returns_city_and_state(self):
        city, state = parse_city_state_from_address("123 Main St, New York, NY 10001")
        assert city == "New York"
        assert state == "NY"

    def test_ca_address(self):
        city, state = parse_city_state_from_address("8001 Sunset Blvd, Los Angeles, CA")
        assert city == "Los Angeles"
        assert state == "CA"

    def test_unknown_state_returns_none_state(self):
        city, state = parse_city_state_from_address("Some Place, Springfield, XX")
        assert city == "Springfield"
        assert state is None

    def test_single_segment_returns_none_both(self):
        city, state = parse_city_state_from_address("No commas here")
        assert city is None
        assert state is None

    def test_empty_string_returns_none_both(self):
        city, state = parse_city_state_from_address("")
        assert city is None
        assert state is None

    def test_none_returns_none_both(self):
        city, state = parse_city_state_from_address(None)
        assert city is None
        assert state is None

    @pytest.mark.parametrize("code,city_name,expected_tz", [
        ("PR", "San Juan", "America/Puerto_Rico"),
        ("VI", "Charlotte Amalie", "America/St_Thomas"),
        ("GU", "Hagåtña", "Pacific/Guam"),
        ("AS", "Pago Pago", "Pacific/Pago_Pago"),
        ("MP", "Saipan", "Pacific/Saipan"),
    ])
    def test_us_territory_returns_state_code(self, code, city_name, expected_tz):
        address = f"123 Main St, {city_name}, {code}"
        city, state = parse_city_state_from_address(address)
        assert city == city_name
        assert state == code
        assert timezone_from_state(state) == expected_tz
