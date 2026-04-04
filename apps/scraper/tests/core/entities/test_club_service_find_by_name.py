"""
Unit tests for ClubService.find_club_by_name.

Covers all 7 code paths:
1. Exact case-insensitive match returns the club
2. Multiple exact matches returns None with an error log
3. Single partial match returns the club with an info log
4. Multiple partial matches returns None with an error log
5. No match returns None with an error log
6. Empty/whitespace-only name returns None immediately
7. DB error from get_all_clubs() returns None with an error log
"""

import sys
from types import ModuleType
from typing import TypeVar as _TypeVar
from unittest.mock import MagicMock, patch

from _entities_test_helpers import _load_module, _stub, _ensure_psycopg2_stubbed


# Foundation stubs
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

# Load Club model directly
_club_model_mod = _load_module(
    "src/laughtrack/core/entities/club/model.py",
    "laughtrack.core.entities.club.model_direct",
)
Club = _club_model_mod.Club
sys.modules.setdefault("laughtrack.core.entities.club.model", _club_model_mod)

# Stub ClubHandler so service.py can import it without DB
_mock_club_handler_cls = MagicMock()
_club_handler_stub = ModuleType("laughtrack.core.entities.club.handler")
_club_handler_stub.ClubHandler = _mock_club_handler_cls
sys.modules.setdefault("laughtrack.core.entities.club.handler", _club_handler_stub)

# Load ClubService. The module is registered under a dotted name (required for
# its relative imports to resolve), but all Logger patching below uses
# patch.object(_club_service_mod, "Logger") rather than a string-based
# patch("laughtrack.core.entities.club.service_direct.Logger"). This avoids
# the _dot_lookup walk through the real laughtrack.core.entities package that
# would fail if a prior test file loaded that package into sys.modules first.
_club_service_mod = _load_module(
    "src/laughtrack/core/entities/club/service.py",
    "laughtrack.core.entities.club.service_direct",
)
ClubService = _club_service_mod.ClubService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_club(id: int, name: str) -> Club:
    return Club(
        id=id,
        name=name,
        address="123 Main St",
        website="",
        scraping_url="",
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
    )


def _make_service(clubs=None, db_error=None) -> ClubService:
    """Return a ClubService whose club_handler.get_all_clubs() is mocked."""
    service = ClubService.__new__(ClubService)
    mock_handler = MagicMock()
    if db_error is not None:
        mock_handler.get_all_clubs.side_effect = db_error
    else:
        mock_handler.get_all_clubs.return_value = clubs or []
    service.club_handler = mock_handler
    return service


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFindClubByNameExactMatch:
    """Path 1: single exact case-insensitive match returns the club."""

    def test_exact_match_returns_club(self):
        club = _make_club(1, "Comedy Cellar")
        service = _make_service([club])
        result = service.find_club_by_name("Comedy Cellar")
        assert result is club

    def test_exact_match_case_insensitive(self):
        club = _make_club(1, "Comedy Cellar")
        service = _make_service([club])
        result = service.find_club_by_name("comedy cellar")
        assert result is club

    def test_exact_match_with_leading_trailing_spaces(self):
        club = _make_club(1, "Comedy Cellar")
        service = _make_service([club])
        result = service.find_club_by_name("  Comedy Cellar  ")
        assert result is club

    def test_exact_match_preferred_over_partial(self):
        """When an exact match exists, it is returned even if partial matches also exist."""
        exact = _make_club(1, "Cellar")
        partial = _make_club(2, "Cellar Lounge")
        service = _make_service([exact, partial])
        result = service.find_club_by_name("Cellar")
        assert result is exact


class TestFindClubByNameMultipleExactMatches:
    """Path 2: multiple exact matches returns None with an error log."""

    def test_multiple_exact_matches_returns_none(self):
        c1 = _make_club(1, "Comedy Club")
        c2 = _make_club(2, "Comedy Club")
        service = _make_service([c1, c2])
        result = service.find_club_by_name("Comedy Club")
        assert result is None

    def test_multiple_exact_matches_logs_error(self):
        c1 = _make_club(1, "Comedy Club")
        c2 = _make_club(2, "Comedy Club")
        service = _make_service([c1, c2])
        with patch.object(_club_service_mod, "Logger") as mock_logger:
            service.find_club_by_name("Comedy Club")
        mock_logger.error.assert_called_once()
        msg = mock_logger.error.call_args[0][0]
        assert "Ambiguous" in msg
        assert "Comedy Club" in msg


class TestFindClubByNameSinglePartialMatch:
    """Path 3: single partial (substring) match returns club with info log."""

    def test_partial_match_returns_club(self):
        club = _make_club(1, "Comedy Cellar NYC")
        service = _make_service([club])
        result = service.find_club_by_name("Cellar")
        assert result is club

    def test_partial_match_case_insensitive(self):
        club = _make_club(1, "Comedy Cellar NYC")
        service = _make_service([club])
        result = service.find_club_by_name("cellar")
        assert result is club

    def test_partial_match_logs_info(self):
        club = _make_club(1, "Comedy Cellar NYC")
        service = _make_service([club])
        with patch.object(_club_service_mod, "Logger") as mock_logger:
            service.find_club_by_name("Cellar")
        mock_logger.info.assert_called_once()
        msg = mock_logger.info.call_args[0][0]
        assert "Cellar" in msg
        assert "Comedy Cellar NYC" in msg


class TestFindClubByNameMultiplePartialMatches:
    """Path 4: multiple partial matches returns None with an error log."""

    def test_multiple_partial_matches_returns_none(self):
        c1 = _make_club(1, "Comedy Cellar NYC")
        c2 = _make_club(2, "Comedy Cellar LA")
        service = _make_service([c1, c2])
        result = service.find_club_by_name("Comedy Cellar")
        assert result is None

    def test_multiple_partial_matches_logs_error(self):
        c1 = _make_club(1, "Comedy Cellar NYC")
        c2 = _make_club(2, "Comedy Cellar LA")
        service = _make_service([c1, c2])
        with patch.object(_club_service_mod, "Logger") as mock_logger:
            service.find_club_by_name("Comedy Cellar")
        mock_logger.error.assert_called_once()
        msg = mock_logger.error.call_args[0][0]
        assert "Ambiguous" in msg
        assert "2 partial" in msg

    def test_error_message_lists_matching_clubs(self):
        c1 = _make_club(10, "Comedy Cellar NYC")
        c2 = _make_club(20, "Comedy Cellar LA")
        service = _make_service([c1, c2])
        with patch.object(_club_service_mod, "Logger") as mock_logger:
            service.find_club_by_name("Comedy Cellar")
        msg = mock_logger.error.call_args[0][0]
        assert "10" in msg
        assert "20" in msg


class TestFindClubByNameNoMatch:
    """Path 5: no match returns None with an error log."""

    def test_no_match_returns_none(self):
        club = _make_club(1, "Comedy Cellar")
        service = _make_service([club])
        result = service.find_club_by_name("Laugh Factory")
        assert result is None

    def test_no_match_logs_error(self):
        club = _make_club(1, "Comedy Cellar")
        service = _make_service([club])
        with patch.object(_club_service_mod, "Logger") as mock_logger:
            service.find_club_by_name("Laugh Factory")
        mock_logger.error.assert_called_once()
        msg = mock_logger.error.call_args[0][0]
        assert "Laugh Factory" in msg

    def test_empty_club_list_returns_none(self):
        service = _make_service([])
        result = service.find_club_by_name("Any Club")
        assert result is None


class TestFindClubByNameEmptyInput:
    """Path 6: empty or whitespace-only name returns None immediately."""

    def test_empty_string_returns_none(self):
        service = _make_service([_make_club(1, "Comedy Cellar")])
        result = service.find_club_by_name("")
        assert result is None

    def test_whitespace_only_returns_none(self):
        service = _make_service([_make_club(1, "Comedy Cellar")])
        result = service.find_club_by_name("   ")
        assert result is None

    def test_empty_input_logs_error(self):
        service = _make_service([])
        with patch.object(_club_service_mod, "Logger") as mock_logger:
            service.find_club_by_name("")
        mock_logger.error.assert_called_once()

    def test_empty_input_does_not_call_get_all_clubs(self):
        """DB should not be queried for empty input."""
        service = _make_service([])
        service.club_handler.get_all_clubs.reset_mock()
        service.find_club_by_name("  ")
        service.club_handler.get_all_clubs.assert_not_called()


class TestFindClubByNameDbError:
    """Path 7: DB error from get_all_clubs() returns None with an error log."""

    def test_db_error_returns_none(self):
        service = _make_service(db_error=RuntimeError("connection refused"))
        result = service.find_club_by_name("Comedy Cellar")
        assert result is None

    def test_db_error_logs_error(self):
        service = _make_service(db_error=RuntimeError("connection refused"))
        with patch.object(_club_service_mod, "Logger") as mock_logger:
            service.find_club_by_name("Comedy Cellar")
        mock_logger.error.assert_called_once()
        msg = mock_logger.error.call_args[0][0]
        assert "connection refused" in msg

    def test_db_error_does_not_raise(self):
        """Exception must be caught; find_club_by_name should never raise."""
        service = _make_service(db_error=Exception("unexpected"))
        result = service.find_club_by_name("Comedy Cellar")  # should not raise
        assert result is None
