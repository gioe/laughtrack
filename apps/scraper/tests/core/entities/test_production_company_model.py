"""Unit tests for ProductionCompany model methods."""

from _entities_test_helpers import _load_module, _stub

from typing import TypeVar as _TypeVar
from unittest.mock import MagicMock

_T = _TypeVar("T")
_stub("laughtrack.foundation.models.types", T=_T, JSONDict=dict)
_stub("laughtrack.foundation.models", as_package=True, T=_T)

_model_mod = _load_module(
    "src/laughtrack/core/entities/production_company/model.py",
    "laughtrack.core.entities.production_company.model_test",
)
ProductionCompany = _model_mod.ProductionCompany


def _make_company(**kwargs) -> ProductionCompany:
    defaults = dict(
        id=1,
        name="Laff House",
        slug="laff-house",
        scraping_url="https://laffhouse.com/events",
        website="https://laffhouse.com",
        visible=True,
        venue_club_ids=[10, 20, 30],
    )
    defaults.update(kwargs)
    return ProductionCompany(**defaults)


class TestFromDbRow:
    def _base_row(self, **kwargs):
        row = {
            "id": 1,
            "name": "Laff House",
            "slug": "laff-house",
            "scraping_url": "https://laffhouse.com/events",
            "website": "https://laffhouse.com",
            "visible": True,
        }
        row.update(kwargs)
        return row

    def test_creates_from_full_row(self):
        row = self._base_row()
        company = ProductionCompany.from_db_row(row)
        assert company.id == 1
        assert company.name == "Laff House"
        assert company.slug == "laff-house"
        assert company.scraping_url == "https://laffhouse.com/events"
        assert company.website == "https://laffhouse.com"
        assert company.visible is True

    def test_defaults_missing_optional_fields(self):
        row = {"id": 2, "name": "Test Co"}
        company = ProductionCompany.from_db_row(row)
        assert company.slug == ""
        assert company.scraping_url is None
        assert company.website is None
        assert company.visible is True

    def test_venue_club_ids_empty_after_from_db_row(self):
        row = self._base_row()
        company = ProductionCompany.from_db_row(row)
        assert company.venue_club_ids == []

    def test_invisible_company(self):
        row = self._base_row(visible=False)
        company = ProductionCompany.from_db_row(row)
        assert company.visible is False


class TestKeyFromDbRow:
    def test_returns_name_tuple(self):
        row = {"name": "Laff House", "id": 1}
        assert ProductionCompany.key_from_db_row(row) == ("Laff House",)

    def test_returns_none_when_name_absent(self):
        row = {"id": 1}
        assert ProductionCompany.key_from_db_row(row) == (None,)


class TestToTuple:
    def test_returns_correct_fields_in_order(self):
        company = _make_company()
        t = company.to_tuple()
        assert t == (
            "Laff House",
            "laff-house",
            "https://laffhouse.com/events",
            "https://laffhouse.com",
            True,
        )

    def test_none_optional_fields(self):
        company = _make_company(scraping_url=None, website=None)
        t = company.to_tuple()
        assert t == ("Laff House", "laff-house", None, None, True)


class TestToUniqueKey:
    def test_returns_name_tuple(self):
        company = _make_company()
        assert company.to_unique_key() == ("Laff House",)


class TestAsContext:
    def test_returns_expected_keys(self):
        company = _make_company()
        ctx = company.as_context()
        assert ctx == {
            "production_company_id": 1,
            "production_company_name": "Laff House",
            "scraping_url": "https://laffhouse.com/events",
        }

    def test_none_scraping_url(self):
        company = _make_company(scraping_url=None)
        ctx = company.as_context()
        assert ctx["scraping_url"] is None


class TestGetClubIdForVenue:
    def test_returns_first_matching_club_id(self):
        company = _make_company(venue_club_ids=[10, 20, 30])
        assert company.get_club_id_for_venue({20, 30}) == 20

    def test_returns_none_when_no_match(self):
        company = _make_company(venue_club_ids=[10, 20, 30])
        assert company.get_club_id_for_venue({99, 100}) is None

    def test_returns_none_when_venue_club_ids_empty(self):
        company = _make_company(venue_club_ids=[])
        assert company.get_club_id_for_venue({10, 20}) is None

    def test_returns_none_when_scope_empty(self):
        company = _make_company(venue_club_ids=[10, 20])
        assert company.get_club_id_for_venue(set()) is None

    def test_respects_order_of_venue_club_ids(self):
        company = _make_company(venue_club_ids=[30, 10, 20])
        # Both 10 and 30 are in scope; should return 30 (first in list)
        assert company.get_club_id_for_venue({10, 30}) == 30
