"""Unit tests for ProductionCompanyHandler.get_all_production_companies."""

import sys
from unittest.mock import MagicMock, patch

from _entities_test_helpers import _load_module, _stub

from typing import TypeVar as _TypeVar

_T = _TypeVar("T")
_stub("laughtrack.foundation.models.types", T=_T, JSONDict=dict)
_stub("laughtrack.foundation.models", as_package=True, T=_T)

# Load model
_model_mod = _load_module(
    "src/laughtrack/core/entities/production_company/model.py",
    "laughtrack.core.entities.production_company.model_handler_test",
)
ProductionCompany = _model_mod.ProductionCompany
sys.modules["laughtrack.core.entities.production_company.model"] = _model_mod

# Load queries
_queries_mod = _load_module(
    "sql/production_company_queries.py",
    "sql.production_company_queries_handler_test",
)
sys.modules["sql.production_company_queries"] = _queries_mod

# Load handler
_handler_mod = _load_module(
    "src/laughtrack/core/entities/production_company/handler.py",
    "laughtrack.core.entities.production_company.handler_test",
)
ProductionCompanyHandler = _handler_mod.ProductionCompanyHandler


def _make_row(**kwargs):
    defaults = {
        "id": 1,
        "name": "Laff House",
        "slug": "laff-house",
        "scraping_url": "https://laffhouse.com/events",
        "website": "https://laffhouse.com",
        "visible": True,
    }
    defaults.update(kwargs)
    return defaults


def _make_venue_row(production_company_id, club_id):
    return {"production_company_id": production_company_id, "club_id": club_id}


class TestGetAllProductionCompanies:
    def _make_handler(self):
        handler = ProductionCompanyHandler.__new__(ProductionCompanyHandler)
        return handler

    def test_returns_companies_with_venue_mappings(self):
        handler = self._make_handler()
        company_rows = [_make_row(id=1), _make_row(id=2, name="Second Co", slug="second-co")]
        venue_rows = [
            _make_venue_row(1, 10),
            _make_venue_row(1, 20),
            _make_venue_row(2, 30),
        ]

        call_count = 0
        def fake_execute(query, return_results=False, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return company_rows
            return venue_rows

        with patch.object(handler, "execute_with_cursor", side_effect=fake_execute):
            result = handler.get_all_production_companies()

        assert len(result) == 2
        assert result[0].name == "Laff House"
        assert result[0].venue_club_ids == [10, 20]
        assert result[1].name == "Second Co"
        assert result[1].venue_club_ids == [30]

    def test_returns_empty_list_when_no_companies(self):
        handler = self._make_handler()

        with patch.object(handler, "execute_with_cursor", return_value=None):
            result = handler.get_all_production_companies()

        assert result == []

    def test_empty_venue_mappings(self):
        handler = self._make_handler()
        company_rows = [_make_row(id=1)]

        call_count = 0
        def fake_execute(query, return_results=False, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return company_rows
            return None  # no venue mappings

        with patch.object(handler, "execute_with_cursor", side_effect=fake_execute):
            result = handler.get_all_production_companies()

        assert len(result) == 1
        assert result[0].venue_club_ids == []

    def test_raises_on_db_error(self):
        handler = self._make_handler()

        with patch.object(handler, "execute_with_cursor", side_effect=RuntimeError("DB down")):
            try:
                handler.get_all_production_companies()
                assert False, "Expected RuntimeError"
            except RuntimeError as e:
                assert "DB down" in str(e)

    def test_company_without_venue_mapping_gets_empty_list(self):
        handler = self._make_handler()
        company_rows = [_make_row(id=1), _make_row(id=2, name="No Venues", slug="no-venues")]
        venue_rows = [_make_venue_row(1, 10)]  # only company 1 has a mapping

        call_count = 0
        def fake_execute(query, return_results=False, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return company_rows
            return venue_rows

        with patch.object(handler, "execute_with_cursor", side_effect=fake_execute):
            result = handler.get_all_production_companies()

        assert result[0].venue_club_ids == [10]
        assert result[1].venue_club_ids == []
