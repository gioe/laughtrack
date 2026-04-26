"""
Unit tests for ClubHandler.upsert_for_eventbrite_venue.

Verifies three contracts:
1. Happy path — valid venue upserts and returns a Club with the correct eventbrite_id.
2. Conflict path — existing club by name returns existing row with preserved
   scraper/eventbrite_id (COALESCE semantics).
3. Invalid input — None venue, missing id, or missing name returns None without raising.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from _entities_test_helpers import _load_module, _stub


# Non-foundation stubs (foundation modules are registered by conftest.py)
from typing import TypeVar as _TypeVar
_T = _TypeVar("T")
_stub("laughtrack.foundation.models.types", T=_T, JSONDict=dict)
_stub("laughtrack.foundation.models", as_package=True, T=_T)
_stub("laughtrack.adapters.db", create_connection=MagicMock())
_stub("laughtrack.adapters", as_package=True, create_connection=MagicMock())

# Load Club model directly (bypasses club __init__.py which may pull in handler)
_club_model_mod = _load_module(
    "src/laughtrack/core/entities/club/model.py",
    "laughtrack.core.entities.club.model_direct",
)
Club = _club_model_mod.Club

# Load ClubQueries directly
_club_queries_mod = _load_module("sql/club_queries.py", "sql.club_queries_direct")
ClubQueries = _club_queries_mod.ClubQueries

# Load BaseDatabaseHandler
_base_handler_mod = _load_module(
    "src/laughtrack/core/data/base_handler.py",
    "laughtrack.core.data.base_handler_direct",
)
BaseDatabaseHandler = _base_handler_mod.BaseDatabaseHandler

# Patch the club model module name so ClubHandler can import it
sys.modules["laughtrack.core.entities.club.model"] = _club_model_mod
sys.modules["laughtrack.core.data.base_handler"] = _base_handler_mod
sys.modules["sql.club_queries"] = _club_queries_mod

# Load timezone_lookup (used via lazy import in handler methods)
_tz_lookup_mod = _load_module(
    "src/laughtrack/utilities/domain/club/timezone_lookup.py",
    "laughtrack.utilities.domain.club.timezone_lookup",
)
parse_city_state_from_address = _tz_lookup_mod.parse_city_state_from_address
sys.modules["laughtrack.utilities.domain.club.timezone_lookup"] = _tz_lookup_mod

# Load ClubHandler
_club_handler_mod = _load_module(
    "src/laughtrack/core/entities/club/handler.py",
    "laughtrack.core.entities.club.handler_direct",
)
ClubHandler = _club_handler_mod.ClubHandler


# ---------------------------------------------------------------------------
# Default: treat every venue as non-junk so happy-path tests see a Club result.
# Junk-filter test classes override this with return_value=True inside each method.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_is_junk_venue():
    with patch("laughtrack.utilities.domain.club.quality_filter.is_junk_venue", return_value=False):
        yield


# ---------------------------------------------------------------------------
# Minimal venue/address stand-ins (no imports from Eventbrite models needed)
# ---------------------------------------------------------------------------

class _FakeAddress:
    def __init__(self, address_1=None, city=None, region=None, postal_code=None):
        self.address_1 = address_1
        self.city = city
        self.region = region
        self.postal_code = postal_code


class _FakeVenue:
    def __init__(self, id=None, name=None, address=None):
        self.id = id
        self.name = name
        self.address = address


def _scraping_sources_entry(*, platform, scraper_key="", source_url="",
                             external_id=None, club_id=None, source_id=1):
    """Build one element of the scraping_sources list as produced by the
    json_agg LATERAL in ClubQueries — the shape Club.from_db_row consumes."""
    return {
        "id": source_id,
        "club_id": club_id,
        "platform": platform,
        "scraper_key": scraper_key or "",
        "external_id": external_id,
        "source_url": source_url or "",
        "priority": 0,
        "enabled": True,
        "metadata": {},
    }


def _row_with_source(defaults, *, platform, legacy):
    """Take a defaults dict for a club row plus the platform + legacy field
    overrides, and attach the scraping_sources list that Club.from_db_row
    will read."""
    defaults["scraping_sources"] = [
        _scraping_sources_entry(
            platform=platform,
            scraper_key=legacy.get("scraper", "") or "",
            source_url=legacy.get("scraping_url", "") or "",
            external_id=legacy.get("external_id"),
            club_id=defaults.get("id"),
        )
    ]
    return defaults


_LEGACY_KEYS = ("scraper", "scraping_url", "eventbrite_id",
                "ticketmaster_id", "seatengine_id",
                "ovationtix_client_id", "wix_comp_id", "squadup_user_id")


def _split_legacy(overrides, defaults_legacy):
    """Pop legacy fields out of overrides; merge with helper-level defaults."""
    legacy = dict(defaults_legacy)
    for key in _LEGACY_KEYS:
        if key in overrides:
            legacy[key] = overrides.pop(key)
    return legacy


def _make_club_row(**overrides):
    """Return a dict that Club.from_db_row() can consume."""
    defaults = {
        "id": 99,
        "name": "Test Club",
        "address": "123 Main St, New York, NY",
        "website": "",
        "popularity": 0,
        "zip_code": "10001",
        "city": "New York",
        "state": "NY",
        "phone_number": "",
        "timezone": "America/New_York",
        "visible": True,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    legacy = _split_legacy(overrides, {
        "scraper": "eventbrite",
        "scraping_url": "www.eventbrite.com",
        "eventbrite_id": "venue-abc",
    })
    defaults.update(overrides)
    return _row_with_source(defaults, platform="eventbrite", legacy={
        "scraper": legacy["scraper"],
        "scraping_url": legacy["scraping_url"],
        "external_id": legacy["eventbrite_id"],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestUpsertForEventbriteVenueHappyPath:
    """Criterion 668: valid venue inserts new club and returns Club with correct eventbrite_id."""

    def test_returns_club_with_matching_eventbrite_id(self):
        venue = _FakeVenue(
            id="venue-abc",
            name="Comedy Cellar",
            address=_FakeAddress(
                address_1="117 MacDougal St",
                city="New York",
                region="NY",
                postal_code="10012",
            ),
        )
        row = _make_club_row(name="Comedy Cellar", eventbrite_id="venue-abc", zip_code="10012")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert isinstance(result, Club)
        assert result.eventbrite_id == "venue-abc"
        assert result.name == "Comedy Cellar"

    def test_passes_correct_params_to_execute(self):
        """execute_with_cursor receives (name, address, eventbrite_id, zip_code)."""
        venue = _FakeVenue(
            id="venue-xyz",
            name="Gotham Comedy Club",
            address=_FakeAddress(
                address_1="208 W 23rd St",
                city="New York",
                region="NY",
                postal_code="10011",
            ),
        )
        row = _make_club_row(name="Gotham Comedy Club", eventbrite_id="venue-xyz", zip_code="10011")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_eventbrite_venue(venue)

        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        params = call_args[0][1]  # second positional arg is the params tuple
        # New CTE shape: (name, address, zip_code, city, state, venue_id)
        assert params[0] == "Gotham Comedy Club"   # name
        assert params[2] == "10011"                # zip_code
        assert params[5] == "venue-xyz"            # venue_id (scraping_sources.external_id)

    def test_address_concatenated_from_parts(self):
        """Address is joined from address_1, city, region with ', '."""
        venue = _FakeVenue(
            id="v1",
            name="Laugh Factory",
            address=_FakeAddress(address_1="8001 Sunset Blvd", city="Los Angeles", region="CA"),
        )
        row = _make_club_row(name="Laugh Factory", eventbrite_id="v1",
                             address="8001 Sunset Blvd, Los Angeles, CA")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_eventbrite_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[1] == "8001 Sunset Blvd, Los Angeles, CA"

    def test_zip_code_empty_when_no_address(self):
        """zip_code defaults to '' when venue.address is None."""
        venue = _FakeVenue(id="v2", name="Club No Address", address=None)
        row = _make_club_row(name="Club No Address", eventbrite_id="v2", zip_code="")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_eventbrite_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[2] == ""   # zip_code (new CTE shape)
        assert params[1] == ""   # address


class TestUpsertForEventbriteVenueConflict:
    """Criterion 669: conflict on name preserves existing scraper and eventbrite_id via COALESCE."""

    def test_existing_club_retains_original_scraper(self):
        """When a club already exists with scraper='broadway', it stays 'broadway', not 'eventbrite'."""
        venue = _FakeVenue(id="new-venue-id", name="Broadway Comedy Club")
        # DB returns the existing row — COALESCE kept the original scraper
        existing_row = _make_club_row(
            name="Broadway Comedy Club",
            scraper="broadway",
            eventbrite_id="original-eb-id",
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is not None
        assert result.scraper == "broadway"

    def test_existing_club_retains_original_eventbrite_id(self):
        """When a club already has an eventbrite_id, it stays unchanged."""
        venue = _FakeVenue(id="different-id", name="Broadway Comedy Club")
        existing_row = _make_club_row(
            name="Broadway Comedy Club",
            eventbrite_id="original-eb-id",
            scraper="broadway",
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result.eventbrite_id == "original-eb-id"

    def test_sql_uses_coalesce_for_scraper(self):
        """SQL contract: UPSERT_CLUB_BY_EVENTBRITE_VENUE must use COALESCE for scraper."""
        sql = ClubQueries.UPSERT_CLUB_BY_EVENTBRITE_VENUE.upper()
        assert "COALESCE" in sql
        assert "SCRAPER" in sql

    def test_sql_uses_coalesce_for_eventbrite_id(self):
        """SQL contract: UPSERT_CLUB_BY_EVENTBRITE_VENUE must COALESCE the
        scraping_sources.external_id (the Eventbrite venue id) so existing
        rows are preserved on conflict."""
        sql = ClubQueries.UPSERT_CLUB_BY_EVENTBRITE_VENUE.upper()
        assert "SCRAPING_SOURCES" in sql
        assert "EXTERNAL_ID" in sql


class TestUpsertForEventbriteVenueInvalidInput:
    """Criterion 670: None/missing venue fields returns None without raising."""

    def test_none_venue_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_eventbrite_venue(None)
        assert result is None

    def test_venue_missing_id_returns_none(self):
        venue = _FakeVenue(id=None, name="Some Club")
        handler = ClubHandler()
        result = handler.upsert_for_eventbrite_venue(venue)
        assert result is None

    def test_venue_missing_name_returns_none(self):
        venue = _FakeVenue(id="v999", name=None)
        handler = ClubHandler()
        result = handler.upsert_for_eventbrite_venue(venue)
        assert result is None

    def test_venue_empty_id_returns_none(self):
        venue = _FakeVenue(id="", name="Some Club")
        handler = ClubHandler()
        result = handler.upsert_for_eventbrite_venue(venue)
        assert result is None

    def test_venue_empty_name_returns_none(self):
        venue = _FakeVenue(id="v999", name="")
        handler = ClubHandler()
        result = handler.upsert_for_eventbrite_venue(venue)
        assert result is None

    def test_no_db_call_on_invalid_input(self):
        """execute_with_cursor must NOT be called when input is invalid."""
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor") as mock_exec:
            handler.upsert_for_eventbrite_venue(None)
            handler.upsert_for_eventbrite_venue(_FakeVenue(id=None, name="X"))
            handler.upsert_for_eventbrite_venue(_FakeVenue(id="v1", name=None))

        mock_exec.assert_not_called()

    def test_none_returned_when_db_returns_empty(self):
        """If execute_with_cursor returns [] (no row), the method returns None."""
        venue = _FakeVenue(id="v1", name="Valid Club")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[]):
            result = handler.upsert_for_eventbrite_venue(venue)
        assert result is None


# ---------------------------------------------------------------------------
# Tests for upsert_for_seatengine_venue
# ---------------------------------------------------------------------------

def _make_seatengine_club_row(**overrides):
    """Return a dict that Club.from_db_row() can consume for SeatEngine clubs."""
    defaults = {
        "id": 99,
        "name": "Test Club",
        "address": "123 Main St, New York, NY",
        "website": "https://testclub.com",
        "popularity": 0,
        "zip_code": "10001",
        "city": "New York",
        "state": "NY",
        "phone_number": "",
        "timezone": "America/New_York",
        "visible": True,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    legacy = _split_legacy(overrides, {
        "scraper": "seatengine",
        "scraping_url": "www.seatengine.com",
        "seatengine_id": "458",
    })
    defaults.update(overrides)
    return _row_with_source(defaults, platform="seatengine", legacy={
        "scraper": legacy["scraper"],
        "scraping_url": legacy["scraping_url"],
        "external_id": legacy["seatengine_id"],
    })


class TestUpsertForSeatEngineVenueHappyPath:
    """Valid venue dict inserts new club and returns Club with correct seatengine_id."""

    def test_returns_club_with_matching_seatengine_id(self):
        venue = {"id": 458, "name": "McGuire's Comedy Club", "address": "123 Main St", "zip": "10001", "website": ""}
        row = _make_seatengine_club_row(name="McGuire's Comedy Club", seatengine_id="458")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]):
            result = handler.upsert_for_seatengine_venue(venue)

        assert result is not None
        assert isinstance(result, Club)
        assert result.seatengine_id == "458"
        assert result.name == "McGuire's Comedy Club"

    def test_passes_correct_params_to_execute(self):
        """execute_with_cursor receives (name, address, website, scraping_url, venue_id, zip_code)."""
        venue = {"id": 457, "name": "Brokerage Comedy Club", "address": "200 Elm St", "zip": "11795", "website": "https://brokerage.com"}
        row = _make_seatengine_club_row(name="Brokerage Comedy Club", seatengine_id="457")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_seatengine_venue(venue)

        mock_exec.assert_called_once()
        params = mock_exec.call_args[0][1]
        # New CTE shape:
        # (name, address, website, zip_code, city, state, venue_id, website-as-source_url)
        assert params[0] == "Brokerage Comedy Club"   # name
        assert params[1] == "200 Elm St"              # address
        assert params[2] == "https://brokerage.com"   # website
        assert params[3] == "11795"                   # zip_code
        assert params[6] == "457"                     # venue_id (external_id, stringified)
        assert params[7] == "https://brokerage.com"   # source_url (mirrors website)

    def test_venue_id_stringified(self):
        """Numeric id in the dict is converted to string for the DB param."""
        venue = {"id": 325, "name": "Stress Factory", "address": "", "zip": "", "website": ""}
        row = _make_seatengine_club_row(name="Stress Factory", seatengine_id="325")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_seatengine_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[6] == "325"

    def test_postal_code_fallback(self):
        """zip_code is read from 'postal_code' key when 'zip' is absent."""
        venue = {"id": 456, "name": "Governors Comedy Club", "address": "", "postal_code": "11520", "website": ""}
        row = _make_seatengine_club_row(name="Governors Comedy Club", seatengine_id="456", zip_code="11520")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_seatengine_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[3] == "11520"  # zip_code (new CTE shape)


class TestUpsertForSeatEngineVenueConflict:
    """Conflict on name preserves existing scraper and seatengine_id via COALESCE."""

    def test_existing_club_retains_original_scraper(self):
        """When a club already exists with scraper='broadway', it stays 'broadway'."""
        venue = {"id": 999, "name": "Broadway Comedy Club", "address": "", "zip": "", "website": ""}
        existing_row = _make_seatengine_club_row(
            name="Broadway Comedy Club",
            scraper="broadway",
            seatengine_id="original-se-id",
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_seatengine_venue(venue)

        assert result is not None
        assert result.scraper == "broadway"

    def test_existing_club_retains_original_seatengine_id(self):
        """When a club already has a seatengine_id, it stays unchanged."""
        venue = {"id": 999, "name": "Broadway Comedy Club", "address": "", "zip": "", "website": ""}
        existing_row = _make_seatengine_club_row(
            name="Broadway Comedy Club",
            seatengine_id="original-se-id",
            scraper="broadway",
        )

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_seatengine_venue(venue)

        assert result.seatengine_id == "original-se-id"

    def test_sql_uses_coalesce_for_seatengine_id(self):
        """SQL contract: UPSERT_CLUB_BY_SEATENGINE_VENUE must COALESCE the
        scraping_sources.external_id (the SeatEngine venue id)."""
        sql = ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE.upper()
        assert "COALESCE" in sql
        assert "SCRAPING_SOURCES" in sql
        assert "EXTERNAL_ID" in sql

    def test_sql_uses_coalesce_for_scraper(self):
        """SQL contract: UPSERT_CLUB_BY_SEATENGINE_VENUE must use COALESCE for scraper."""
        sql = ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE.upper()
        assert "COALESCE" in sql
        assert "SCRAPER" in sql


class TestUpsertForSeatEngineVenueInvalidInput:
    """Missing/empty id or name returns None without raising."""

    def test_missing_id_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_venue({"name": "Some Club"})
        assert result is None

    def test_empty_id_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_venue({"id": "", "name": "Some Club"})
        assert result is None

    def test_missing_name_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_venue({"id": 123})
        assert result is None

    def test_empty_name_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_venue({"id": 123, "name": ""})
        assert result is None

    def test_no_db_call_on_invalid_input(self):
        """execute_with_cursor must NOT be called when input is invalid."""
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor") as mock_exec:
            handler.upsert_for_seatengine_venue({"name": "No Id"})
            handler.upsert_for_seatengine_venue({"id": "", "name": "Empty Id"})
            handler.upsert_for_seatengine_venue({"id": 123, "name": None})

        mock_exec.assert_not_called()

    def test_none_returned_when_db_returns_empty(self):
        """If execute_with_cursor returns [], the method returns None."""
        venue = {"id": 458, "name": "Valid Club"}
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[]):
            result = handler.upsert_for_seatengine_venue(venue)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: city/state extraction in Eventbrite upsert
# ---------------------------------------------------------------------------

class TestEventbriteVenueCityStateExtraction:
    """City and state are passed to execute_with_cursor from venue.address fields."""

    def test_city_and_state_extracted_from_address(self):
        venue = _FakeVenue(
            id="v1",
            name="Comedy Cellar",
            address=_FakeAddress(
                address_1="117 MacDougal St",
                city="New York",
                region="NY",
                postal_code="10012",
            ),
        )
        row = _make_club_row(name="Comedy Cellar", city="New York", state="NY")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_eventbrite_venue(venue)

        params = mock_exec.call_args[0][1]
        # New CTE shape: (name, address, zip_code, city, state, venue_id)
        assert params[3] == "New York"  # city
        assert params[4] == "NY"        # state

    def test_city_state_none_when_no_address(self):
        venue = _FakeVenue(id="v2", name="Club No Address", address=None)
        row = _make_club_row(name="Club No Address", city=None, state=None)
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_eventbrite_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[3] is None  # city
        assert params[4] is None  # state


# ---------------------------------------------------------------------------
# Tests: city/state extraction in SeatEngine upsert
# ---------------------------------------------------------------------------

class TestSeatEngineVenueCityStateExtraction:
    """City and state are parsed from the address string for SeatEngine venues."""

    def test_city_and_state_parsed_from_address(self):
        venue = {"id": 100, "name": "Stress Factory", "address": "90 New St, Newark, NJ", "zip": "07102", "website": ""}
        row = _make_seatengine_club_row(name="Stress Factory", city="Newark", state="NJ")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_seatengine_venue(venue)

        params = mock_exec.call_args[0][1]
        # New CTE shape: (name, address, website, zip_code, city, state, venue_id, source_url)
        assert params[4] == "Newark"  # city
        assert params[5] == "NJ"      # state

    def test_city_state_none_when_address_unparseable(self):
        """No city/state when address has only one segment."""
        venue = {"id": 101, "name": "Mystery Club", "address": "NoCommasHere", "zip": "", "website": ""}
        row = _make_seatengine_club_row(name="Mystery Club", city=None, state=None)
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_seatengine_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[4] is None  # city
        assert params[5] is None  # state


# ---------------------------------------------------------------------------
# Tests: city/state extraction in Ticketmaster upsert
# ---------------------------------------------------------------------------

def _make_ticketmaster_club_row(**overrides):
    """Return a dict that Club.from_db_row() can consume for Ticketmaster clubs."""
    defaults = {
        "id": 99,
        "name": "Test Club",
        "address": "123 Main St, New York, NY",
        "website": "",
        "popularity": 0,
        "zip_code": "10001",
        "city": "New York",
        "state": "NY",
        "phone_number": "",
        "timezone": "America/New_York",
        "visible": True,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    legacy = _split_legacy(overrides, {
        "scraper": "live_nation",
        "scraping_url": "www.ticketmaster.com",
        "ticketmaster_id": "tm-001",
    })
    defaults.update(overrides)
    return _row_with_source(defaults, platform="ticketmaster", legacy={
        "scraper": legacy["scraper"],
        "scraping_url": legacy["scraping_url"],
        "external_id": legacy["ticketmaster_id"],
    })


class TestTicketmasterVenueCityStateExtraction:
    """City and state are read from structured API fields for Ticketmaster venues."""

    def test_city_and_state_extracted_from_structured_fields(self):
        venue = {
            "id": "tm-001",
            "name": "Radio City Music Hall",
            "address": {"line1": "1260 Avenue of the Americas"},
            "city": {"name": "New York"},
            "state": {"stateCode": "NY"},
            "postalCode": "10020",
            "timezone": "America/New_York",
        }
        row = _make_ticketmaster_club_row(name="Radio City Music Hall", city="New York", state="NY")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_ticketmaster_venue(venue)

        params = mock_exec.call_args[0][1]
        # New CTE shape: (name, address, zip_code, city, state, timezone, venue_id)
        assert params[3] == "New York"  # city
        assert params[4] == "NY"        # state

    def test_city_state_none_when_absent_from_venue(self):
        """City and state default to None when not present in venue dict."""
        venue = {"id": "tm-002", "name": "Unknown Hall", "postalCode": ""}
        row = _make_ticketmaster_club_row(name="Unknown Hall", city=None, state=None)
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]) as mock_exec:
            handler.upsert_for_ticketmaster_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[3] is None  # city
        assert params[4] is None  # state


# ---------------------------------------------------------------------------
# Tests: ClubHandler.backfill_city_state
# ---------------------------------------------------------------------------

def _make_backfill_club_row(**overrides):
    """Row for a club with city/state NULL."""
    defaults = {
        "id": 10,
        "name": "Test Club",
        "address": "117 MacDougal St, New York, NY",
        "website": "",
        "popularity": 0,
        "zip_code": "10012",
        "city": None,
        "state": None,
        "phone_number": "",
        "timezone": "America/New_York",
        "visible": True,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    legacy = _split_legacy(overrides, {
        "scraper": "eventbrite",
        "scraping_url": "www.test.com",
    })
    defaults.update(overrides)
    return _row_with_source(defaults, platform="eventbrite", legacy={
        "scraper": legacy["scraper"],
        "scraping_url": legacy["scraping_url"],
        "external_id": None,
    })


class TestBackfillCityState:
    """ClubHandler.backfill_city_state populates city/state from address."""

    def test_updates_club_with_parseable_address(self):
        """A club whose address yields city/state is batch-updated."""
        row = _make_backfill_club_row(id=10, address="117 MacDougal St, New York, NY")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]), \
             patch.object(handler, "execute_batch_operation", return_value=[{"id": 10}]) as mock_batch:
            result = handler.backfill_city_state()

        assert result == 1
        mock_batch.assert_called_once()
        updates = mock_batch.call_args[0][1]
        assert len(updates) == 1
        assert updates[0] == (10, "New York", "NY")

    def test_skips_club_with_unparseable_address(self):
        """A club with a single-segment address (no commas) is skipped."""
        row = _make_backfill_club_row(id=11, address="NoCommasHere")
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]), \
             patch.object(handler, "execute_batch_operation") as mock_batch:
            result = handler.backfill_city_state()

        assert result == 0
        mock_batch.assert_not_called()

    def test_returns_zero_when_no_clubs_need_update(self):
        """If no clubs have NULL city/state, returns 0 without calling batch op."""
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[]), \
             patch.object(handler, "execute_batch_operation") as mock_batch:
            result = handler.backfill_city_state()

        assert result == 0
        mock_batch.assert_not_called()

    def test_multiple_clubs_batched_in_single_update(self):
        """All resolvable clubs are sent in one batch."""
        rows = [
            _make_backfill_club_row(id=1, address="208 W 23rd St, New York, NY"),
            _make_backfill_club_row(id=2, address="8001 Sunset Blvd, Los Angeles, CA"),
        ]
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=rows), \
             patch.object(handler, "execute_batch_operation", return_value=[{"id": 1}, {"id": 2}]) as mock_batch:
            result = handler.backfill_city_state()

        assert result == 2
        mock_batch.assert_called_once()
        updates = mock_batch.call_args[0][1]
        assert len(updates) == 2
        assert updates[0] == (1, "New York", "NY")
        assert updates[1] == (2, "Los Angeles", "CA")


# ---------------------------------------------------------------------------
# Tests: ClubHandler.refresh_club_total_shows
# ---------------------------------------------------------------------------

class TestRefreshClubTotalShows:
    """ClubHandler.refresh_club_total_shows executes the UPDATE_CLUB_TOTAL_SHOWS query."""

    def test_calls_execute_with_cursor_with_correct_query(self):
        """execute_with_cursor is called with UPDATE_CLUB_TOTAL_SHOWS and no extra params."""
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor") as mock_exec:
            handler.refresh_club_total_shows()

        mock_exec.assert_called_once_with(ClubQueries.UPDATE_CLUB_TOTAL_SHOWS)

    def test_sql_updates_total_shows_column(self):
        """SQL contract: UPDATE_CLUB_TOTAL_SHOWS must reference total_shows and shows table."""
        sql = ClubQueries.UPDATE_CLUB_TOTAL_SHOWS.upper()
        assert "TOTAL_SHOWS" in sql
        assert "FROM SHOWS" in sql

    def test_reraises_on_db_error(self):
        """DB exceptions propagate out of refresh_club_total_shows."""
        import pytest
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", side_effect=RuntimeError("db error")):
            with pytest.raises(RuntimeError, match="db error"):
                handler.refresh_club_total_shows()


# ---------------------------------------------------------------------------
# Tests for upsert_for_seatengine_v3_venue
# ---------------------------------------------------------------------------

_V3_UUID = "cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3"


def _make_seatengine_v3_club_row(**overrides):
    """Return a dict that Club.from_db_row() can consume for SeatEngine v3 clubs."""
    defaults = {
        "id": 99,
        "name": "Test Club",
        "address": "123 Main St, Cambridge, MA",
        "website": "https://testclub.com",
        "popularity": 0,
        "zip_code": "02139",
        "city": "Cambridge",
        "state": "MA",
        "phone_number": "",
        "timezone": None,
        "visible": True,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    legacy = _split_legacy(overrides, {
        "scraper": "seatengine_v3",
        "scraping_url": f"https://v-{_V3_UUID}.seatengine.net",
        "seatengine_id": _V3_UUID,
    })
    defaults.update(overrides)
    return _row_with_source(defaults, platform="seatengine_v3", legacy={
        "scraper": legacy["scraper"],
        "scraping_url": legacy["scraping_url"],
        "external_id": legacy["seatengine_id"],
    })


class TestUpsertForSeatEngineV3VenueHappyPath:
    """Valid venue dict inserts new club and returns Club with correct UUID."""

    def test_returns_club_with_matching_seatengine_id(self):
        venue = {"uuid": _V3_UUID, "name": "The Comedy Studio", "address": "1236 Mass Ave, Cambridge, MA", "website": "https://thecomedystudio.com", "zipCode": "02139"}
        row = _make_seatengine_v3_club_row(name="The Comedy Studio")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[row]):
            result = handler.upsert_for_seatengine_v3_venue(venue)

        assert result is not None
        assert isinstance(result, Club)
        assert result.seatengine_id == _V3_UUID
        assert result.name == "The Comedy Studio"

    def test_scraping_url_constructed_from_uuid(self):
        """source_url param must be https://v-{uuid}.seatengine.net."""
        venue = {"uuid": _V3_UUID, "name": "The Comedy Studio", "address": ""}

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[_make_seatengine_v3_club_row()]) as mock_exec:
            handler.upsert_for_seatengine_v3_venue(venue)

        params = mock_exec.call_args[0][1]
        # New CTE shape: (name, address, website, zip_code, city, state, venue_uuid, source_url)
        assert params[7] == f"https://v-{_V3_UUID}.seatengine.net"

    def test_venue_uuid_stored_as_seatengine_id(self):
        """UUID is passed as the scraping_sources.external_id column value."""
        venue = {"uuid": _V3_UUID, "name": "The Comedy Studio", "address": ""}

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[_make_seatengine_v3_club_row()]) as mock_exec:
            handler.upsert_for_seatengine_v3_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[6] == _V3_UUID

    def test_zip_code_from_zipCode_key(self):
        """zipCode (camelCase) is the primary zip_code source."""
        venue = {"uuid": _V3_UUID, "name": "Club", "address": "", "zipCode": "02139"}

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[_make_seatengine_v3_club_row()]) as mock_exec:
            handler.upsert_for_seatengine_v3_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[3] == "02139"  # zip_code (new CTE shape)

    def test_zip_code_fallback_to_zip_key(self):
        """Falls back to 'zip' key when 'zipCode' is absent."""
        venue = {"uuid": _V3_UUID, "name": "Club", "address": "", "zip": "02139"}

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[_make_seatengine_v3_club_row()]) as mock_exec:
            handler.upsert_for_seatengine_v3_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[3] == "02139"  # zip_code (new CTE shape)

    def test_explicit_city_state_from_api_take_priority(self):
        """city/state from the venue dict are used before address parsing."""
        venue = {
            "uuid": _V3_UUID,
            "name": "Club",
            "address": "1 Broadway, New York, NY",
            "city": "Cambridge",
            "state": "MA",
        }

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[_make_seatengine_v3_club_row()]) as mock_exec:
            handler.upsert_for_seatengine_v3_venue(venue)

        params = mock_exec.call_args[0][1]
        assert params[4] == "Cambridge"  # city (new CTE shape)
        assert params[5] == "MA"         # state


class TestUpsertForSeatEngineV3VenueConflict:
    """Conflict on name preserves existing values via COALESCE."""

    def test_existing_club_retains_original_scraper(self):
        venue = {"uuid": _V3_UUID, "name": "Broadway Comedy Club", "address": ""}
        existing_row = _make_seatengine_v3_club_row(name="Broadway Comedy Club", scraper="broadway")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_seatengine_v3_venue(venue)

        assert result is not None
        assert result.scraper == "broadway"

    def test_existing_club_retains_original_seatengine_id(self):
        venue = {"uuid": _V3_UUID, "name": "Broadway Comedy Club", "address": ""}
        existing_row = _make_seatengine_v3_club_row(seatengine_id="original-uuid")

        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[existing_row]):
            result = handler.upsert_for_seatengine_v3_venue(venue)

        assert result.seatengine_id == "original-uuid"

    def test_sql_uses_coalesce_for_seatengine_id(self):
        sql = ClubQueries.UPSERT_CLUB_BY_SEATENGINE_V3_VENUE.upper()
        assert "COALESCE" in sql
        assert "SCRAPING_SOURCES" in sql
        assert "EXTERNAL_ID" in sql

    def test_sql_uses_coalesce_for_scraper(self):
        sql = ClubQueries.UPSERT_CLUB_BY_SEATENGINE_V3_VENUE.upper()
        assert "COALESCE" in sql
        assert "SCRAPER_KEY" in sql

    def test_sql_uses_coalesce_for_scraping_url(self):
        """source_url (the v-{uuid}.seatengine.net URL) must be preserved for
        existing clubs via COALESCE."""
        sql = ClubQueries.UPSERT_CLUB_BY_SEATENGINE_V3_VENUE.upper()
        assert "SOURCE_URL" in sql


class TestUpsertForSeatEngineV3VenueInvalidInput:
    """Missing/empty uuid or name returns None without raising."""

    def test_missing_uuid_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_v3_venue({"name": "Some Club"})
        assert result is None

    def test_empty_uuid_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_v3_venue({"uuid": "", "name": "Some Club"})
        assert result is None

    def test_missing_name_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_v3_venue({"uuid": _V3_UUID})
        assert result is None

    def test_empty_name_returns_none(self):
        handler = ClubHandler()
        result = handler.upsert_for_seatengine_v3_venue({"uuid": _V3_UUID, "name": ""})
        assert result is None

    def test_no_db_call_on_invalid_input(self):
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor") as mock_exec:
            handler.upsert_for_seatengine_v3_venue({"name": "No UUID"})
            handler.upsert_for_seatengine_v3_venue({"uuid": "", "name": "Empty UUID"})
            handler.upsert_for_seatengine_v3_venue({"uuid": _V3_UUID, "name": None})
        mock_exec.assert_not_called()

    def test_none_returned_when_db_returns_empty(self):
        venue = {"uuid": _V3_UUID, "name": "Valid Club"}
        handler = ClubHandler()
        with patch.object(handler, "execute_with_cursor", return_value=[]):
            result = handler.upsert_for_seatengine_v3_venue(venue)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: is_junk_venue filter across upsert paths (TASK-885)
# ---------------------------------------------------------------------------

_JUNK_FILTER = "laughtrack.utilities.domain.club.quality_filter.is_junk_venue"


class TestUpsertForEventbriteVenueJunkFilter:
    """is_junk_venue returning True causes upsert_for_eventbrite_venue to return None."""

    def test_junk_name_returns_none(self):
        venue = _FakeVenue(id="v-junk", name="Demo Comedy Club")
        handler = ClubHandler()
        with patch(_JUNK_FILTER, return_value=True) as mock_filter, \
             patch.object(handler, "execute_with_cursor") as mock_exec:
            result = handler.upsert_for_eventbrite_venue(venue)

        assert result is None
        mock_filter.assert_called_once_with("Demo Comedy Club")
        mock_exec.assert_not_called()


class TestUpsertForTicketmasterVenueJunkFilter:
    """is_junk_venue returning True causes upsert_for_ticketmaster_venue to return None."""

    def test_junk_name_returns_none(self):
        venue = {"id": "tm-junk", "name": "Demo Comedy Club"}
        handler = ClubHandler()
        with patch(_JUNK_FILTER, return_value=True) as mock_filter, \
             patch.object(handler, "execute_with_cursor") as mock_exec:
            result = handler.upsert_for_ticketmaster_venue(venue)

        assert result is None
        mock_filter.assert_called_once_with("Demo Comedy Club")
        mock_exec.assert_not_called()


class TestUpsertForTourDateVenueJunkFilter:
    """is_junk_venue returning True causes upsert_for_tour_date_venue to return None."""

    def test_junk_name_returns_none(self):
        venue = {"name": "Demo Comedy Club"}
        handler = ClubHandler()
        with patch(_JUNK_FILTER, return_value=True) as mock_filter, \
             patch.object(handler, "execute_with_cursor") as mock_exec:
            result = handler.upsert_for_tour_date_venue(venue)

        assert result is None
        mock_filter.assert_called_once_with("Demo Comedy Club")
        mock_exec.assert_not_called()
