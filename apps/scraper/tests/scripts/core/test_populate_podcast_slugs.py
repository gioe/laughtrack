from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import populate_podcast_slugs as mod  # noqa: E402


class _FakeCursor:
    def __init__(self, conn: "_FakeConn") -> None:
        self._conn = conn
        self._last_result: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def execute(self, sql: str, params: Any = None) -> None:
        self._conn.executed.append((sql, params))
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT id, title, source, source_podcast_id, slug"):
            self._last_result = self._conn.rows
        elif normalized.startswith("UPDATE podcasts"):
            self._conn.updates.append(params)
            self._last_result = []
        elif normalized.startswith("SELECT COUNT(*) FROM podcasts"):
            self._last_result = [(0,)]
        else:
            self._last_result = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last_result

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._last_result[0] if self._last_result else None


class _FakeConn:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows
        self.executed: list[tuple[str, Any]] = []
        self.updates: list[Any] = []

    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)


def test_build_podcast_slug_uses_title_and_source_id():
    assert (
        mod.build_podcast_slug("Steve-O's Wild Ride!", "podcast_index", "101")
        == "steve-o-s-wild-ride-podcast-index-101"
    )
    assert mod.build_podcast_slug("!!!", "", "") == "podcast"


def test_populate_podcast_slugs_dry_run_does_not_write(monkeypatch):
    conn = _FakeConn([(1, "The Pod", "podcast_index", "feed-1", None)])
    monkeypatch.setattr(mod, "get_transaction", lambda: conn)

    planned = mod.populate_podcast_slugs(dry_run=True)

    assert planned == 1
    assert conn.updates == []


def test_populate_podcast_slugs_writes_slug_and_task_metadata(monkeypatch):
    conn = _FakeConn([(1, "The Pod", "podcast_index", "feed-1", None)])
    monkeypatch.setattr(mod, "get_transaction", lambda: conn)

    written = mod.populate_podcast_slugs(dry_run=False)

    assert written == 1
    assert len(conn.updates) == 1
    assert conn.updates[0][0] == "the-pod-podcast-index-feed-1"
    assert "task_2259_slug" in conn.updates[0][1]
