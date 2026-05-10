from unittest.mock import MagicMock, patch

from laughtrack.utilities.domain.club.coordinates import ClubGeocodingResult, geocode_missing_clubs


class _Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        if sql.strip().startswith("UPDATE"):
            self.rowcount = 1

    def fetchall(self):
        return self.rows


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self._cursor


def test_geocode_missing_clubs_resolves_coords_and_updates_only_null_rows():
    rows = [
        {
            "id": 10,
            "name": "Mapped Club",
            "address": "1 Main St",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
        },
        {
            "id": 11,
            "name": "Unmapped Club",
            "address": "2 Main St",
            "city": "Nowhere",
            "state": "ZZ",
            "zip_code": "",
        },
    ]
    cursor = _Cursor(rows)
    resolver = MagicMock(side_effect=[(40.75, -73.99), None])

    with patch(
        "laughtrack.utilities.domain.club.coordinates.get_connection",
        return_value=_Connection(cursor),
    ):
        result = geocode_missing_clubs(limit=30, resolver=resolver, sleep=lambda _: None)

    assert result == ClubGeocodingResult(attempted=2, resolved=1, unresolved=1)
    assert resolver.call_count == 2
    select_sql, select_params = cursor.statements[0]
    assert "WHERE latitude IS NULL OR longitude IS NULL" in select_sql
    assert select_params == (30,)

    updates = [stmt for stmt in cursor.statements if stmt[0].strip().startswith("UPDATE")]
    assert len(updates) == 1
    update_sql, update_params = updates[0]
    assert "SET latitude = %s, longitude = %s" in update_sql
    assert "AND (latitude IS NULL OR longitude IS NULL)" in update_sql
    assert update_params == (40.75, -73.99, 10)
