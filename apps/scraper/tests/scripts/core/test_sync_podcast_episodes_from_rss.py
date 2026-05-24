from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import sync_podcast_episodes_from_rss as mod  # noqa: E402


class _FakeCursor:
    def __init__(self, conn: "_FakeConn") -> None:
        self.conn = conn
        self._last_result: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def execute(self, sql: str, params: Any = None) -> None:
        self.conn.executed.append((sql, params))
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT id, source, source_podcast_id"):
            self._last_result = self.conn.podcast_rows
        elif normalized.startswith("SELECT COUNT(*) FROM podcast_episodes"):
            self._last_result = [(self.conn.episode_count,)]
        elif normalized.startswith("UPDATE podcasts SET last_synced_at"):
            self.conn.last_synced_updates.append(params)
            self._last_result = []
        else:
            self._last_result = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last_result

    def fetchone(self) -> Any:
        return self._last_result[0] if self._last_result else None


class _FakeConn:
    def __init__(self) -> None:
        self.podcast_rows = [
            (42, "itunes", "12345", "https://feeds.example.com/show.xml", "Comedy Talk", {"raw": True})
        ]
        self.episode_count = 7
        self.executed: list[tuple[str, Any]] = []
        self.last_synced_updates: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_driver_dry_run_prints_audit_blocks_and_writes_nothing(monkeypatch, capsys):
    conn = _FakeConn()
    sync_calls: list[tuple[int, bool]] = []

    def fake_get_connection(*, autocommit: bool = True) -> _FakeConn:
        assert autocommit is False
        return conn

    def fake_sync(sync_conn: Any, podcast: Any, *, dry_run: bool) -> mod.reader.RssSyncSummary:
        assert sync_conn is conn
        sync_calls.append((podcast.podcast_id, dry_run))
        return mod.reader.RssSyncSummary(episodes_seen=3, episodes_skipped=0)

    monkeypatch.setattr(mod, "get_connection", fake_get_connection)
    monkeypatch.setattr(mod.reader, "sync_podcast_episodes_from_rss", fake_sync)

    assert mod.main(["--dry-run", "--limit", "1"]) == 0

    out = capsys.readouterr().out
    assert "BEFORE" in out
    assert "AFTER" in out
    assert "DRY RUN" in out
    assert sync_calls == [(42, True)]
    assert conn.last_synced_updates == []
    assert conn.commits == 0
    assert conn.rollbacks == 1


def test_driver_confirm_bumps_last_synced_after_success(monkeypatch):
    conn = _FakeConn()

    monkeypatch.setattr(mod, "get_connection", lambda *, autocommit=False: conn)
    monkeypatch.setattr(
        mod.reader,
        "sync_podcast_episodes_from_rss",
        lambda _conn, _podcast, *, dry_run: mod.reader.RssSyncSummary(
            episodes_seen=2,
            episodes_inserted=1,
        ),
    )

    summary = mod.sync_podcasts_from_rss(dry_run=False, limit=1, source=None)

    assert summary.podcasts_scanned == 1
    assert summary.episodes_inserted == 1
    assert conn.last_synced_updates == [(42,)]
    assert conn.commits == 1
    assert conn.rollbacks == 0
