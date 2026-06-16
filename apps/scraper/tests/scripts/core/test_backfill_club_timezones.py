"""Unit tests for backfill_club_timezones.derive_timezone waterfall.

Exercises the pure resolution logic with a fake Places client so no DB or
network is touched: state -> address -> place_id geocode -> name/website
geocode -> unresolved, plus the --geocode gate.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

# Match the path setup the script does at runtime so imports resolve in tests.
_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for p in (str(_src_path), str(_repo_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

from laughtrack.core.clients.google.places import PlaceDetails  # noqa: E402
from scripts.core import backfill_club_timezones as mod  # noqa: E402


class _FakeClient:
    """Stand-in for GooglePlacesClient recording calls and returning canned data."""

    def __init__(
        self,
        details_by_place_id: Optional[dict] = None,
        find_result: Optional[str] = None,
    ) -> None:
        self.details_by_place_id = details_by_place_id or {}
        self.find_result = find_result
        self.find_calls: List[str] = []
        self.details_calls: List[str] = []

    def fetch_place_details(self, place_id: str) -> Optional[PlaceDetails]:
        self.details_calls.append(place_id)
        return self.details_by_place_id.get(place_id)

    def find_place_id(self, query: str) -> Optional[str]:
        self.find_calls.append(query)
        return self.find_result


def _row(**kwargs) -> mod.ClubRow:
    base = dict(id=1, name=None, state=None, address=None, google_place_id=None, website=None)
    base.update(kwargs)
    return mod.ClubRow(**base)


def test_state_wins_first_without_geocode():
    row = _row(state="CA", address="1 Main St, Somewhere, NY")
    res = mod.derive_timezone(row, client=None, geocode=False)
    assert res.source == mod.SOURCE_STATE
    assert res.timezone == "America/Los_Angeles"


def test_address_used_when_state_missing():
    row = _row(state=None, address="123 Main St, New York, NY")
    res = mod.derive_timezone(row, client=None, geocode=False)
    assert res.source == mod.SOURCE_ADDRESS
    assert res.timezone == "America/New_York"


def test_unresolved_when_no_signal_and_no_geocode():
    row = _row(state=None, address=None, google_place_id="ChIJabc")
    res = mod.derive_timezone(row, client=None, geocode=False)
    assert res.source == mod.SOURCE_UNRESOLVED
    assert res.timezone is None


def test_placeid_geocode_resolves_and_carries_details():
    details = PlaceDetails("ChIJabc", "1 St, SF, CA, USA", "CA", "San Francisco", 37.7, -122.4)
    client = _FakeClient(details_by_place_id={"ChIJabc": details})
    row = _row(state=None, address=None, google_place_id="ChIJabc")

    res = mod.derive_timezone(row, client=client, geocode=True)

    assert res.source == mod.SOURCE_PLACEID_GEOCODE
    assert res.timezone == "America/Los_Angeles"
    assert res.details is details
    assert client.details_calls == ["ChIJabc"]
    assert client.find_calls == []  # never fell through to text search


def test_name_geocode_resolves_and_records_place_id():
    details = PlaceDetails("ChIJfound", "9 Ave, Austin, TX, USA", "TX", "Austin", 30.2, -97.7)
    client = _FakeClient(details_by_place_id={"ChIJfound": details}, find_result="ChIJfound")
    row = _row(state=None, address=None, google_place_id=None, name="The Club", website="https://club.example.com")

    res = mod.derive_timezone(row, client=client, geocode=True)

    assert res.source == mod.SOURCE_NAME_GEOCODE
    assert res.timezone == "America/Chicago"
    assert res.resolved_place_id == "ChIJfound"
    # name preferred over website URL as the search query — Places resolves a
    # business name far more reliably than a bare URL string.
    assert client.find_calls == ["The Club"]


def test_name_geocode_falls_back_to_name_when_no_website():
    details = PlaceDetails("ChIJfound", None, "TX", None, None, None)
    client = _FakeClient(details_by_place_id={"ChIJfound": details}, find_result="ChIJfound")
    row = _row(state=None, address=None, name="The Club", website=None)

    res = mod.derive_timezone(row, client=client, geocode=True)

    assert res.source == mod.SOURCE_NAME_GEOCODE
    assert client.find_calls == ["The Club"]


def test_geocode_disabled_skips_places_calls_entirely():
    client = _FakeClient(find_result="ChIJfound")
    row = _row(state=None, address=None, google_place_id="ChIJabc", name="The Club")

    res = mod.derive_timezone(row, client=client, geocode=False)

    assert res.source == mod.SOURCE_UNRESOLVED
    assert client.details_calls == []
    assert client.find_calls == []


def test_unresolved_when_geocode_returns_no_state():
    details = PlaceDetails("ChIJabc", None, None, None, None, None)
    client = _FakeClient(details_by_place_id={"ChIJabc": details}, find_result=None)
    row = _row(state=None, address=None, google_place_id="ChIJabc", name="The Club")

    res = mod.derive_timezone(row, client=client, geocode=True)

    assert res.source == mod.SOURCE_UNRESOLVED
    # tried place_id, then fell through to name search (which found nothing).
    assert client.details_calls == ["ChIJabc"]
    assert client.find_calls == ["The Club"]
