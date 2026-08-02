import sys
from contextlib import contextmanager

from scripts.core import audit_comedian_images


class _Cursor:
    def __init__(self, rows=()):
        self.rows = rows
        self.executions = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        self.executions.append((query, params))
        self.rowcount = len(params or ())

    def fetchall(self):
        return self.rows


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


@contextmanager
def _connection(cursor):
    yield _Connection(cursor)


def test_update_preserves_managed_avatar_when_legacy_cdn_image_is_missing(
    monkeypatch,
):
    read_cursor = _Cursor(
        rows=[
            (302966, "Joe Rogan", False, True),
            (2, "Legacy Missing", True, False),
        ]
    )
    write_cursor = _Cursor()
    monkeypatch.setattr(
        audit_comedian_images, "get_connection", lambda: _connection(read_cursor)
    )
    monkeypatch.setattr(
        audit_comedian_images, "get_transaction", lambda: _connection(write_cursor)
    )
    monkeypatch.setattr(
        audit_comedian_images, "check_image", lambda name: (name, False)
    )
    monkeypatch.setattr(sys, "argv", ["audit_comedian_images.py", "--update"])

    audit_comedian_images.main()

    assert "comedian_image_assets" in read_cursor.executions[0][0]
    assert "a.is_active = true" in read_cursor.executions[0][0]
    assert "a.avatar_path IS NOT NULL" in read_cursor.executions[0][0]
    assert len(write_cursor.executions) == 2
    assert "has_image = true" in write_cursor.executions[0][0]
    assert "EXISTS" in write_cursor.executions[0][0]
    assert write_cursor.executions[0][1] == (302966,)
    assert "has_image = false" in write_cursor.executions[1][0]
    assert "NOT EXISTS" in write_cursor.executions[1][0]
    assert "a.is_active = true" in write_cursor.executions[1][0]
    assert "a.avatar_path IS NOT NULL" in write_cursor.executions[1][0]
    assert write_cursor.executions[1][1] == (2,)


def test_update_does_not_treat_inactive_managed_avatar_as_renderable(monkeypatch):
    read_cursor = _Cursor(rows=[(3, "Inactive Asset", True, False)])
    write_cursor = _Cursor()
    monkeypatch.setattr(
        audit_comedian_images, "get_connection", lambda: _connection(read_cursor)
    )
    monkeypatch.setattr(
        audit_comedian_images, "get_transaction", lambda: _connection(write_cursor)
    )
    monkeypatch.setattr(
        audit_comedian_images, "check_image", lambda name: (name, False)
    )
    monkeypatch.setattr(sys, "argv", ["audit_comedian_images.py", "--update"])

    audit_comedian_images.main()

    assert len(write_cursor.executions) == 1
    assert "has_image = false" in write_cursor.executions[0][0]
    assert write_cursor.executions[0][1] == (3,)


def test_update_tracks_duplicate_names_by_comedian_id(monkeypatch):
    read_cursor = _Cursor(
        rows=[
            (10, "Duplicate Name", False, True),
            (11, "Duplicate Name", True, False),
        ]
    )
    write_cursor = _Cursor()
    monkeypatch.setattr(
        audit_comedian_images, "get_connection", lambda: _connection(read_cursor)
    )
    monkeypatch.setattr(
        audit_comedian_images, "get_transaction", lambda: _connection(write_cursor)
    )
    monkeypatch.setattr(
        audit_comedian_images, "check_image", lambda name: (name, False)
    )
    monkeypatch.setattr(sys, "argv", ["audit_comedian_images.py", "--update"])

    audit_comedian_images.main()

    assert len(write_cursor.executions) == 2
    assert write_cursor.executions[0][1] == (10,)
    assert write_cursor.executions[1][1] == (11,)
