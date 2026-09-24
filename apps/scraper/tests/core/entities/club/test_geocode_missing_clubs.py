"""Exercise real selection/update SQL across runs and provider identity checks."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from laughtrack.utilities.domain.club import coordinates as mod


class SQLiteCursor:
    def __init__(self, db):
        self.db = db
        self.cursor = db.cursor()
        self.synthetic = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        if "pg_try_advisory_xact_lock" in sql:
            self.synthetic = (True,)
            return
        self.synthetic = None
        self.cursor.execute(sql.replace("%s", "?").replace("IS NOT DISTINCT FROM", "IS"), params)

    def fetchone(self):
        return self.synthetic if self.synthetic is not None else self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def rowcount(self):
        return self.cursor.rowcount


@pytest.fixture
def db(monkeypatch):
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE clubs (id INTEGER PRIMARY KEY, name TEXT, address TEXT,
        city TEXT, state TEXT, zip_code TEXT, country TEXT, latitude REAL, longitude REAL,
        visible BOOLEAN DEFAULT TRUE, status TEXT DEFAULT 'active', club_type TEXT DEFAULT 'club',
        geocode_attempted_at TEXT, geocode_attempt_count INTEGER DEFAULT 0, geocode_outcome TEXT);
        CREATE TABLE shows (club_id INTEGER, date TEXT);
    """)

    class Connection:
        def commit(self):
            db.commit()

        def cursor(self):
            return SQLiteCursor(db)

    @contextmanager
    def connection(**kwargs):
        yield Connection()
        db.commit()

    monkeypatch.setattr(mod, "get_connection", connection)
    yield db
    db.close()


def add(db, id, **fields):
    values = dict(
        id=id,
        name=f"Venue {id}",
        address="1 Main St, Boston, MA 02116, US",
        city="Boston",
        state="MA",
        zip_code="02116",
        country="US",
    )
    values.update(fields)
    db.execute(
        f"INSERT INTO clubs ({','.join(values)}) VALUES ({','.join('?' for _ in values)})", tuple(values.values())
    )


def test_unresolved_candidates_do_not_starve_later_clubs(db):
    add(db, 1)
    add(db, 2)
    add(db, 3, visible=False)
    resolver = MagicMock(side_effect=[None, (42.3, -71.1)])
    first = mod.geocode_missing_clubs(limit=1, resolver=resolver, sleep=lambda _: None)
    second = mod.geocode_missing_clubs(limit=1, resolver=resolver, sleep=lambda _: None)
    assert first.unresolved == 1
    assert second.resolved == 1
    assert [c.args[0].id for c in resolver.call_args_list] == [1, 2]
    assert db.execute("SELECT geocode_attempt_count, geocode_outcome FROM clubs WHERE id=1").fetchone() == (
        1,
        "unresolved",
    )
    assert db.execute("SELECT latitude FROM clubs WHERE id=2").fetchone() == (42.3,)


def candidate(**fields):
    values = dict(
        id=1,
        name="Generic Venue",
        address="1 Main St, Boston, MA 02116, US",
        city="Boston",
        state="MA",
        zip_code="02116",
    )
    values.update(fields)
    return mod.ClubCoordinateCandidate(**values)


def response(monkeypatch, address=None, **fields):
    item = dict(
        lat="42.3",
        lon="-71.1",
        address=address
        or dict(
            house_number="1",
            road="Main Street",
            city="Boston",
            state="Massachusetts",
            postcode="02116",
            country_code="us",
            **{"ISO3166-2-lvl4": "US-MA"},
        ),
    )
    item.update(fields)
    result = MagicMock()
    result.json.return_value = [item]
    request = MagicMock(return_value=result)
    monkeypatch.setattr("requests.get", request)
    return request


def test_ambiguous_location_is_not_accepted(monkeypatch):
    response(
        monkeypatch,
        address=dict(house_number="1", road="Main Street", city="London", postcode="02116", country_code="gb"),
    )
    assert mod.resolve_club_coordinates(candidate()) is None


def test_upcoming_priority_and_ineligible_rows(db):
    add(db, 1)
    add(db, 2)
    add(db, 3, visible=False)
    add(db, 4, status="closed")
    add(db, 5, club_type="producer")
    add(db, 6, latitude=42, longitude=-71)
    db.execute("INSERT INTO shows VALUES (2, ?)", ((datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),))
    assert [club.id for club in mod.preview_missing_clubs(limit=30)] == [2, 1]
    assert db.execute("SELECT SUM(geocode_attempt_count) FROM clubs").fetchone()[0] == 0


def test_oldest_attempt_rotates_and_failed_lookups_are_recorded(db):
    old = datetime.now(timezone.utc) - timedelta(days=8)
    add(db, 1, geocode_attempted_at=old, geocode_attempt_count=1, geocode_outcome="unresolved")
    add(db, 2)
    resolver = MagicMock(side_effect=[RuntimeError("timeout"), None])
    result = mod.geocode_missing_clubs(limit=2, resolver=resolver, sleep=lambda _: None)
    assert [call.args[0].id for call in resolver.call_args_list] == [2, 1]
    assert (result.failed, result.unresolved, result.retried) == (1, 1, 1)
    assert mod.preview_missing_clubs() == []
    db.execute("UPDATE clubs SET geocode_attempted_at=? WHERE id=2", (datetime.now(timezone.utc) - timedelta(days=2),))
    assert [club.id for club in mod.preview_missing_clubs()] == [2]


def test_provider_block_stops_batch_and_next_run(db):
    add(db, 1)
    add(db, 2)
    resolver = MagicMock(side_effect=mod.GeocodingProviderBlocked("429"))
    first = mod.geocode_missing_clubs(limit=2, resolver=resolver, sleep=lambda _: None)
    second = mod.geocode_missing_clubs(limit=2, resolver=resolver, sleep=lambda _: None)
    assert (first.attempted, first.failed, second.attempted) == (1, 1, 0)
    assert resolver.call_count == 1


def test_rate_limit_applies_between_separate_runs(db):
    add(db, 1)
    add(db, 2)
    sleep = MagicMock()
    mod.geocode_missing_clubs(limit=1, resolver=lambda _: None, sleep=sleep)
    mod.geocode_missing_clubs(limit=1, resolver=lambda _: None, sleep=sleep)
    assert sleep.call_count == 1
    assert 14 <= sleep.call_args.args[0] <= 15


@pytest.mark.parametrize(
    "lat,lon,coords,expected",
    [
        (42.3, None, (42.3, -71.1), (42.3, -71.1)),
        (42.3, None, (42.5, -71.1), (42.3, None)),
        (None, -71.1, (42.3, -71.1), (42.3, -71.1)),
        (None, -71.1, (42.3, -73.0), (None, -71.1)),
    ],
)
def test_existing_half_preserved_and_conflicting_pair_rejected(db, lat, lon, coords, expected):
    add(db, 1, latitude=lat, longitude=lon)
    mod.geocode_missing_clubs(limit=1, resolver=lambda _: coords, sleep=lambda _: None)
    assert db.execute("SELECT latitude,longitude FROM clubs").fetchone() == expected


def test_changed_identity_is_not_overwritten(db):
    add(db, 1)

    def relocate(club):
        db.execute("UPDATE clubs SET address='A new address' WHERE id=1")
        return (42.3, -71.1)

    result = mod.geocode_missing_clubs(limit=1, resolver=relocate, sleep=lambda _: None)
    assert (result.resolved, result.skipped) == (0, 1)
    assert db.execute("SELECT latitude, geocode_attempt_count FROM clubs").fetchone() == (None, 0)


@pytest.mark.parametrize("coords", [(float("inf"), 0), (0, float("nan")), (91, 0), (0, -181)])
def test_invalid_coordinates_never_written(db, coords):
    add(db, 1)
    result = mod.geocode_missing_clubs(limit=1, resolver=lambda _: coords, sleep=lambda _: None)
    assert result.unresolved == 1
    assert db.execute("SELECT latitude,longitude FROM clubs").fetchone() == (None, None)


def test_verified_address_match_and_deduplicated_query(monkeypatch):
    request = response(monkeypatch)
    assert mod.resolve_club_coordinates(candidate()) == (42.3, -71.1)
    assert request.call_args.kwargs["params"]["q"] == "1 Main St, Boston, MA 02116, US"
    assert request.call_args.kwargs["params"]["addressdetails"] == 1


@pytest.mark.parametrize(
    "key,value",
    [
        ("postcode", "10001"),
        ("house_number", "2"),
        ("road", "Other Street"),
        ("city", "Cambridge"),
        ("country_code", "ca"),
        ("ISO3166-2-lvl4", "US-NY"),
    ],
)
def test_conflicting_address_component_rejected(monkeypatch, key, value):
    addr = dict(
        house_number="1",
        road="Main Street",
        city="Boston",
        state="Massachusetts",
        postcode="02116",
        country_code="us",
        **{"ISO3166-2-lvl4": "US-MA"},
    )
    addr[key] = value
    response(monkeypatch, address=addr)
    assert mod.resolve_club_coordinates(candidate()) is None


def test_ambiguous_two_matching_locations_rejected(monkeypatch):
    request = response(monkeypatch)
    first = request.return_value.json.return_value[0]
    request.return_value.json.return_value = [first, dict(first, lat="42.4")]
    assert mod.resolve_club_coordinates(candidate()) is None


def test_foreign_postal_code_never_falls_back_to_us_centroid(monkeypatch):
    request = response(monkeypatch)
    request.return_value.json.return_value = []
    assert mod.resolve_club_coordinates(candidate(country="AU", zip_code="2000")) is None
    request.assert_not_called()  # conflicting address/country rejected before lookup


def test_postal_centroid_without_house_and_road_is_rejected(monkeypatch):
    response(monkeypatch, address=dict(postcode="02116", country_code="us"))
    assert mod.resolve_club_coordinates(candidate()) is None


def test_provider_errors_propagate_for_failure_accounting(monkeypatch):
    request = response(monkeypatch)
    request.return_value.status_code = 429
    with pytest.raises(mod.GeocodingProviderBlocked):
        mod.resolve_club_coordinates(candidate())


def test_endpoint_is_read_at_call_time(monkeypatch):
    request = response(monkeypatch)
    monkeypatch.setenv("NOMINATIM_SEARCH_URL", "https://geocoder.example/search")
    mod.resolve_club_coordinates(candidate())
    assert request.call_args.args[0] == "https://geocoder.example/search"


def test_empty_limit_does_not_open_connection(monkeypatch):
    connection = MagicMock()
    monkeypatch.setattr(mod, "get_connection", connection)
    assert mod.geocode_missing_clubs(limit=0).attempted == 0
    assert mod.preview_missing_clubs(limit=0) == []
    connection.assert_not_called()


def test_raw_address_locality_is_checked_without_city_fields(monkeypatch):
    addr = dict(
        house_number="1",
        road="Main Street",
        city="Cambridge",
        state="Massachusetts",
        postcode="02116",
        country_code="us",
        **{"ISO3166-2-lvl4": "US-MA"},
    )
    response(monkeypatch, address=addr)
    assert mod.resolve_club_coordinates(candidate(city=None, state=None)) is None


def test_raw_address_region_is_checked_against_conflicting_stored_state(monkeypatch):
    response(monkeypatch)
    assert mod.resolve_club_coordinates(candidate(state="NY")) is None


def test_separate_zip_and_state_address_establish_country(monkeypatch):
    response(monkeypatch)
    assert mod.resolve_club_coordinates(candidate(address="1 Main St, Boston, MA")) == (42.3, -71.1)


def test_query_does_not_confuse_state_with_street_substring():
    assert mod._query_text(candidate(address="1 Main St", city="Boston", state="MA")) == "1 Main St, Boston, MA, 02116"


def test_direction_and_street_suffix_abbreviations_match(monkeypatch):
    response(
        monkeypatch,
        address=dict(
            house_number="8406",
            road="West Central Avenue",
            city="Wichita",
            state="Kansas",
            postcode="67212",
            country_code="us",
            **{"ISO3166-2-lvl4": "US-KS"},
        ),
    )
    assert mod.resolve_club_coordinates(
        candidate(address="8406 W Central Ave, Wichita, KS 67212, US", city="Wichita", state="KS", zip_code="67212")
    ) == (42.3, -71.1)


def test_concurrent_worker_does_not_call_provider(db, monkeypatch):
    add(db, 1)
    original = SQLiteCursor.execute

    def busy(self, sql, params=()):
        original(self, sql, params)
        if "pg_try_advisory_xact_lock" in sql:
            self.synthetic = (False,)

    monkeypatch.setattr(SQLiteCursor, "execute", busy)
    resolver = MagicMock()
    assert mod.geocode_missing_clubs(resolver=resolver).attempted == 0
    resolver.assert_not_called()


def test_persistence_error_propagates_without_success_report(db, monkeypatch):
    add(db, 1)
    original = SQLiteCursor.execute

    def fail_write(self, sql, params=()):
        if sql.lstrip().startswith("UPDATE"):
            raise RuntimeError("database write failed")
        original(self, sql, params)

    monkeypatch.setattr(SQLiteCursor, "execute", fail_write)
    with pytest.raises(RuntimeError, match="database write failed"):
        mod.geocode_missing_clubs(resolver=lambda _: (42.3, -71.1), sleep=lambda _: None)


def test_dict_cursor_candidate_supported():
    row = dict(
        id=1,
        name="Name",
        address="Address",
        city=None,
        state=None,
        zip_code=None,
        country=None,
        latitude=None,
        longitude=None,
        geocode_attempt_count=0,
    )
    assert mod._candidate_from_row(row).name == "Name"
