from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import psycopg2

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
        elif normalized.startswith("SELECT COUNT(*) FROM podcasts"):
            self._last_result = [(self.conn.unreachable_count,)]
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
    def __init__(self, podcast_rows: list[tuple[Any, ...]] | None = None) -> None:
        self.podcast_rows = podcast_rows or [
            (42, "itunes", "12345", "https://feeds.example.com/show.xml", "Comedy Talk", {"raw": True})
        ]
        self.episode_count = 7
        self.unreachable_count = 0
        self.executed: list[tuple[str, Any]] = []
        self.last_synced_updates: list[Any] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        if self.closed:
            raise psycopg2.InterfaceError("connection already closed")
        return _FakeCursor(self)

    def commit(self) -> None:
        if self.closed:
            raise psycopg2.InterfaceError("connection already closed")
        self.commits += 1

    def rollback(self) -> None:
        if self.closed:
            raise psycopg2.InterfaceError("connection already closed")
        self.rollbacks += 1


def test_driver_dry_run_prints_audit_blocks_and_writes_nothing(monkeypatch, capsys):
    conn = _FakeConn()
    sync_calls: list[tuple[int, bool]] = []

    def fake_get_connection(*, autocommit: bool = True) -> _FakeConn:
        return conn

    def fake_fetch(podcast: Any) -> mod.reader.RssFetchResult:
        return mod.reader.RssFetchResult()

    def fake_persist(
        sync_conn: Any, podcast: Any, _fetched: mod.reader.RssFetchResult, *, dry_run: bool
    ) -> mod.reader.RssSyncSummary:
        assert sync_conn is conn
        sync_calls.append((podcast.podcast_id, dry_run))
        return mod.reader.RssSyncSummary(episodes_seen=3, episodes_skipped=0)

    monkeypatch.setattr(mod, "get_connection", fake_get_connection)
    monkeypatch.setattr(mod.reader, "fetch_rss_episodes", fake_fetch)
    monkeypatch.setattr(mod.reader, "persist_rss_fetch_result", fake_persist)

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
    monkeypatch.setattr(mod.reader, "fetch_rss_episodes", lambda _podcast: mod.reader.RssFetchResult())
    monkeypatch.setattr(
        mod.reader,
        "persist_rss_fetch_result",
        lambda _conn, _podcast, _fetched, *, dry_run: mod.reader.RssSyncSummary(
            episodes_seen=2,
            episodes_inserted=1,
        ),
    )

    summary = mod.sync_podcasts_from_rss(dry_run=False, limit=1, source=None)

    assert summary.podcasts_scanned == 1
    assert summary.podcasts_selected == 1
    assert summary.completed is True
    assert summary.budget_exhausted is False
    assert summary.episodes_inserted == 1
    assert conn.last_synced_updates == [(42,)]
    assert conn.commits == 1
    assert conn.rollbacks == 0


def test_driver_continues_after_closed_connection_during_podcast_sync(monkeypatch):
    podcast_rows = [
        (42, "itunes", "12345", "https://feeds.example.com/broken.xml", "Broken Talk", {"raw": True}),
        (43, "itunes", "67890", "https://feeds.example.com/healthy.xml", "Healthy Talk", {"raw": True}),
    ]
    loader_conn = _FakeConn(podcast_rows)
    first_sync_conn = _FakeConn()
    second_sync_conn = _FakeConn()
    after_count_conn = _FakeConn()
    # A persist/DB error must NOT bench the feed, so no extra record connection is
    # opened on this path (only genuine fetch failures record unreachable state).
    connections = [loader_conn, first_sync_conn, second_sync_conn, after_count_conn]
    autocommit_modes: list[bool] = []
    events: list[str] = []
    sync_calls: list[int] = []

    def fake_get_connection(*, autocommit: bool = True) -> _FakeConn:
        autocommit_modes.append(autocommit)
        events.append(f"connect:{autocommit}")
        return connections.pop(0)

    def fake_fetch(podcast: Any) -> mod.reader.RssFetchResult:
        events.append(f"fetch:{podcast.podcast_id}")
        return mod.reader.RssFetchResult()

    def fake_persist(
        sync_conn: _FakeConn, podcast: Any, _fetched: mod.reader.RssFetchResult, *, dry_run: bool
    ) -> mod.reader.RssSyncSummary:
        sync_calls.append(podcast.podcast_id)
        if podcast.podcast_id == 42:
            sync_conn.closed = True
            raise psycopg2.InterfaceError("connection already closed")
        return mod.reader.RssSyncSummary(episodes_seen=2, episodes_inserted=1)

    monkeypatch.setattr(mod, "get_connection", fake_get_connection)
    monkeypatch.setattr(mod.reader, "fetch_rss_episodes", fake_fetch)
    monkeypatch.setattr(mod.reader, "persist_rss_fetch_result", fake_persist)

    summary = mod.sync_podcasts_from_rss(dry_run=False, limit=2, source=None)

    assert summary.podcasts_scanned == 2
    assert summary.podcasts_failed == 1
    assert summary.episodes_inserted == 1
    assert autocommit_modes == [True, False, False, True]
    assert events == ["connect:True", "fetch:42", "connect:False", "fetch:43", "connect:False", "connect:True"]
    assert sync_calls == [42, 43]
    assert second_sync_conn.last_synced_updates == [(43,)]
    assert second_sync_conn.commits == 1


def test_load_podcasts_query_skips_feeds_in_reachability_cooldown():
    conn = _FakeConn()

    mod.load_podcasts(conn, source=None, podcast_ids=None, limit=500)

    select_sql, select_params = next(
        (sql, params) for sql, params in conn.executed if "SELECT" in sql and "source_podcast_id" in sql
    )
    # The reachability predicate is ANDed into the load query and its bind params follow the filters.
    assert "consecutive_failures" in select_sql
    assert "last_failure_at" in select_sql
    assert mod.reader.UNREACHABLE_FAILURE_THRESHOLD in select_params
    assert mod.reader.UNREACHABLE_COOLDOWN_DAYS in select_params
    assert "ORDER BY last_synced_at ASC NULLS FIRST, id ASC" in " ".join(select_sql.split())
    # LIMIT is still the final bind param so the rotating batch is preserved.
    assert select_params[-1] == 500


def test_load_podcasts_query_limits_to_canonical_non_denylisted_podcasts():
    conn = _FakeConn()

    mod.load_podcasts(conn, source=None, podcast_ids=None, limit=500)

    select_sql, _select_params = next(
        (sql, params) for sql, params in conn.executed if "SELECT" in sql and "source_podcast_id" in sql
    )
    normalized = " ".join(select_sql.split())
    assert "FROM podcast_deny_list" in select_sql
    assert "restored_at IS NULL" in select_sql
    assert "pdl.podcast_id = podcasts.id" in normalized
    assert "FROM comedian_podcasts cp" in select_sql
    assert "JOIN comedians c ON c.id = cp.comedian_id" in select_sql
    assert "cp.review_status = 'accepted'" in select_sql
    assert "cp.association_type IN ('host', 'cohost', 'owner')" in select_sql
    assert "c.parent_comedian_id IS NULL" in select_sql


def test_driver_records_failure_and_reports_skipped_unreachable(monkeypatch):
    conn = _FakeConn()
    conn.unreachable_count = 12
    recorded: list[int] = []

    monkeypatch.setattr(mod, "get_connection", lambda *, autocommit=False: conn)

    def fake_fetch(_podcast: Any) -> mod.reader.RssFetchResult:
        raise RuntimeError("Could not resolve host")

    monkeypatch.setattr(mod.reader, "fetch_rss_episodes", fake_fetch)
    monkeypatch.setattr(mod.reader, "record_fetch_failure", lambda _conn, p: recorded.append(p.podcast_id) or 1)

    summary = mod.sync_podcasts_from_rss(dry_run=False, limit=1, source=None)

    assert summary.podcasts_failed == 1
    assert summary.podcasts_skipped_unreachable == 12
    assert recorded == [42]


def test_dry_run_does_not_record_unreachable_on_fetch_failure(monkeypatch):
    conn = _FakeConn()
    recorded: list[int] = []

    monkeypatch.setattr(mod, "get_connection", lambda *, autocommit=True: conn)
    monkeypatch.setattr(
        mod.reader,
        "fetch_rss_episodes",
        lambda _podcast: (_ for _ in ()).throw(RuntimeError("SSL alert")),
    )
    monkeypatch.setattr(mod.reader, "record_fetch_failure", lambda _conn, p: recorded.append(p.podcast_id) or 1)

    summary = mod.sync_podcasts_from_rss(dry_run=True, limit=1, source=None)

    assert summary.podcasts_failed == 1
    assert recorded == []


def test_persist_error_does_not_bench_reachable_feed(monkeypatch):
    # A successful fetch followed by a downstream persist/DB error must count as a
    # failure but must NOT increment the feed's reachability backoff counter.
    conn = _FakeConn()
    recorded: list[int] = []

    monkeypatch.setattr(mod, "get_connection", lambda *, autocommit=False: conn)
    monkeypatch.setattr(mod.reader, "fetch_rss_episodes", lambda _podcast: mod.reader.RssFetchResult())

    def fake_persist(_conn: Any, _podcast: Any, _fetched: Any, *, dry_run: bool) -> Any:
        raise psycopg2.OperationalError("transient DB error")

    monkeypatch.setattr(mod.reader, "persist_rss_fetch_result", fake_persist)
    monkeypatch.setattr(mod.reader, "record_fetch_failure", lambda _conn, p: recorded.append(p.podcast_id) or 1)

    summary = mod.sync_podcasts_from_rss(dry_run=False, limit=1, source=None)

    assert summary.podcasts_failed == 1
    assert recorded == []


def test_runtime_budget_stops_cleanly_and_next_run_resumes_with_unfinished_feed(monkeypatch):
    podcasts = [
        mod.reader.PodcastRssFeed(42, "itunes", "42", "https://example.com/42.xml", "First"),
        mod.reader.PodcastRssFeed(43, "itunes", "43", "https://example.com/43.xml", "Second"),
        mod.reader.PodcastRssFeed(44, "itunes", "44", "https://example.com/44.xml", "Third"),
    ]
    last_synced: dict[int, float | None] = {podcast.podcast_id: None for podcast in podcasts}
    clock = {"now": 100.0}
    exhaust_on_second = {"enabled": True}
    recorded_unreachable: list[int] = []
    run_orders: list[list[int]] = []

    monkeypatch.setattr(mod.time, "monotonic", lambda: clock["now"])

    def fake_load_sync_inputs(*, source: Any, podcast_ids: Any, limit: Any) -> Any:
        del source, podcast_ids
        ordered = sorted(
            podcasts,
            key=lambda podcast: (
                last_synced[podcast.podcast_id] is not None,
                last_synced[podcast.podcast_id] or 0,
                podcast.podcast_id,
            ),
        )
        selected = ordered[:limit]
        run_orders.append([podcast.podcast_id for podcast in selected])
        return 7, selected, 0

    def fake_sync_one(podcast: Any, *, dry_run: bool, deadline: float | None = None) -> Any:
        assert dry_run is False
        assert deadline is not None
        if podcast.podcast_id == 43 and exhaust_on_second["enabled"]:
            exhaust_on_second["enabled"] = False
            clock["now"] = deadline
            raise mod.reader.RssSyncBudgetExceeded("test deadline reached")
        last_synced[podcast.podcast_id] = clock["now"]
        clock["now"] += 1
        return mod.reader.RssSyncSummary(episodes_seen=1, episodes_unchanged=1)

    monkeypatch.setattr(mod, "_load_sync_inputs", fake_load_sync_inputs)
    monkeypatch.setattr(mod, "_sync_one_podcast", fake_sync_one)
    monkeypatch.setattr(mod, "_record_unreachable", lambda podcast: recorded_unreachable.append(podcast.podcast_id))
    monkeypatch.setattr(mod, "get_connection", lambda **_kwargs: _FakeConn())

    first = mod.sync_podcasts_from_rss(
        dry_run=False,
        limit=2,
        source=None,
        max_runtime_seconds=5,
    )

    assert run_orders[0] == [42, 43]
    assert first.podcasts_selected == 2
    assert first.podcasts_scanned == 1
    assert first.completed is False
    assert first.budget_exhausted is True
    assert first.podcasts_failed == 0
    assert recorded_unreachable == []

    clock["now"] = 200.0
    second = mod.sync_podcasts_from_rss(
        dry_run=False,
        limit=2,
        source=None,
        max_runtime_seconds=20,
    )

    assert run_orders[1] == [43, 44]
    assert second.podcasts_selected == 2
    assert second.podcasts_scanned == 2
    assert second.completed is True
    assert second.budget_exhausted is False
    assert recorded_unreachable == []


def test_main_appends_partial_completion_to_github_output(monkeypatch, tmp_path):
    output_path = tmp_path / "github-output"
    captured: dict[str, Any] = {}

    def fake_sync(**kwargs: Any) -> mod.DriverSummary:
        captured.update(kwargs)
        return mod.DriverSummary(podcasts_selected=10, podcasts_scanned=4, completed=False, budget_exhausted=True)

    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setattr(mod, "sync_podcasts_from_rss", fake_sync)

    assert mod.main(["--confirm", "--max-runtime-seconds", "123.5"]) == 0

    assert captured["max_runtime_seconds"] == 123.5
    assert output_path.read_text(encoding="utf-8") == "completed=false\n"
