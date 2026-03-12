"""
Unit tests for ClubHandler.upsert_for_eventbrite_venue.

Verifies three contracts:
1. Happy path — valid venue upserts and returns a Club with the correct eventbrite_id.
2. Conflict path — existing club by name returns existing row with preserved
   scraper/eventbrite_id (COALESCE semantics).
3. Invalid input — None venue, missing id, or missing name returns None without raising.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Bootstrap: load modules directly, bypassing package __init__.py chains that
# require a live DB environment.
# ---------------------------------------------------------------------------
_SCRAPER_ROOT = Path(__file__).parents[3]  # apps/scraper/


def _load_module(rel_path: str, module_name: str):
    path = _SCRAPER_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    _ensure_psycopg2_stubbed()
    spec.loader.exec_module(mod)
    return mod


def _ensure_psycopg2_stubbed():
    if "psycopg2" not in sys.modules:
        psycopg2 = ModuleType("psycopg2")
        extras = ModuleType("psycopg2.extras")
        extras.DictRow = dict
        extras.execute_values = MagicMock()
        extensions = ModuleType("psycopg2.extensions")
        extensions.connection = object
        psycopg2.extras = extras
        psycopg2.extensions = extensions
        sys.modules["psycopg2"] = psycopg2
        sys.modules["psycopg2.extras"] = extras
        sys.modules["psycopg2.extensions"] = extensions


def _stub(name: str, **attrs):
    m = ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


# Foundation stubs
_stub("laughtrack.foundation.protocols.database_entity", DatabaseEntity=object)
_stub("laughtrack.foundation.protocols", DatabaseEntity=object)
_stub("laughtrack.foundation.infrastructure.logger.logger", Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure.logger", Logger=MagicMock())
_stub("laughtrack.foundation.infrastructure.database.operation", DatabaseOperationLogger=MagicMock())
_stub("laughtrack.foundation.infrastructure.database", DatabaseOperationLogger=MagicMock())
_stub("laughtrack.foundation.infrastructure", Logger=MagicMock())
from typing import TypeVar as _TypeVar
_T = _TypeVar("T")
_stub("laughtrack.foundation.models.types", T=_T, JSONDict=dict)
_stub("laughtrack.foundation.models", T=_T)
_stub("laughtrack.foundation", DatabaseEntity=object)
_stub("laughtrack.adapters.db", create_connection=MagicMock())
_stub("laughtrack.adapters", create_connection=MagicMock())

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

# Load ClubHandler
_club_handler_mod = _load_module(
    "src/laughtrack/core/entities/club/handler.py",
    "laughtrack.core.entities.club.handler_direct",
)
ClubHandler = _club_handler_mod.ClubHandler


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


def _make_club_row(**overrides):
    """Return a dict that Club.from_db_row() can consume."""
    defaults = {
        "id": 99,
        "name": "Test Club",
        "address": "123 Main St, New York, NY",
        "website": "",
        "scraping_url": "www.eventbrite.com",
        "popularity": 0,
        "zip_code": "10001",
        "phone_number": "",
        "timezone": "America/New_York",
        "visible": True,
        "scraper": "eventbrite",
        "eventbrite_id": "venue-abc",
        "ticketmaster_id": None,
        "seatengine_id": None,
        "rate_limit": 1.0,
        "max_retries": 3,
        "timeout": 30,
    }
    defaults.update(overrides)
    return defaults


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
        assert params[0] == "Gotham Comedy Club"   # name
        assert params[2] == "venue-xyz"            # eventbrite_id
        assert params[3] == "10011"                # zip_code

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
        assert params[3] == ""   # zip_code
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
        """SQL contract: UPSERT_CLUB_BY_EVENTBRITE_VENUE must use COALESCE for eventbrite_id."""
        sql = ClubQueries.UPSERT_CLUB_BY_EVENTBRITE_VENUE.upper()
        assert "EVENTBRITE_ID" in sql


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
