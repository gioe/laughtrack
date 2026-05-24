from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from laughtrack.core.itunes_podcast_discovery import (  # noqa: E402
    ItunesPodcastCandidate,
    PodcastDiscoveryComedian,
    UpsertResult,
    upsert_candidate_with_conn,
)
from scripts.core import search_itunes_podcasts as mod  # noqa: E402


class _FakeCursor:
    def __init__(self, conn: "_FakeConn") -> None:
        self.conn = conn
        self._last: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.conn.executed.append((sql, params))
        normalized = " ".join(sql.split())
        if "COUNT(*) FILTER" in normalized:
            self._last = [(2, 3)]
        elif "FROM comedians c" in normalized:
            self._last = self.conn.comedian_rows
        else:
            self._last = []

    def fetchone(self) -> Any:
        return self._last[0] if self._last else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last


class _FakeConn:
    def __init__(self) -> None:
        self.comedian_rows = [(12, "Taylor Comic", ["Taylor C"])]
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []
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


class _PodcastDedupeCursor:
    def __init__(self, conn: "_PodcastDedupeConn") -> None:
        self.conn = conn
        self._last: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_PodcastDedupeCursor":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT id, external_ids FROM podcasts"):
            self._last = [(77, {"podcast_index_feed_id": 998})]
        elif normalized.startswith("UPDATE podcasts"):
            self.conn.podcast_updates.append(params)
            self._last = [(77,)]
        elif normalized.startswith("INSERT INTO podcasts"):
            self.conn.podcast_inserts.append(params)
            self._last = [(88,)]
        elif normalized.startswith("INSERT INTO podcast_candidate_reviews"):
            self.conn.review_upserts.append(params)
            self._last = []
        else:
            self._last = []

    def fetchone(self) -> Any:
        return self._last[0] if self._last else None


class _PodcastDedupeConn:
    def __init__(self) -> None:
        self.podcast_updates: list[tuple[Any, ...] | None] = []
        self.podcast_inserts: list[tuple[Any, ...] | None] = []
        self.review_upserts: list[tuple[Any, ...] | None] = []

    def cursor(self) -> _PodcastDedupeCursor:
        return _PodcastDedupeCursor(self)


def _candidate(comedian_id: int = 12) -> ItunesPodcastCandidate:
    return ItunesPodcastCandidate(
        comedian_id=comedian_id,
        source_podcast_id="12345",
        matched_name="Taylor Comic",
        normalized_match="taylor comic",
        confidence=0.99,
        title="Taylor Comic Podcast",
        author_name="Taylor Comic",
        feed_url="https://feeds.example.com/taylor.xml",
        website_url="https://podcasts.apple.com/us/podcast/taylor/id12345",
        image_url=None,
        description=None,
        evidence={"confidence_band": "title_exact", "source_fields": {"collection_id": 12345}},
    )


def test_feed_url_dedupe_merges_itunes_collection_id_into_existing_podcast() -> None:
    conn = _PodcastDedupeConn()

    result = upsert_candidate_with_conn(conn, _candidate())

    assert result == UpsertResult(77, "merged_feed_url")
    assert conn.podcast_inserts == []
    assert len(conn.podcast_updates) == 1
    assert conn.podcast_updates[0] is not None
    assert '"itunes_collection_id": "12345"' in conn.podcast_updates[0][0]
    assert len(conn.review_upserts) == 1
    assert conn.review_upserts[0][:4] == (12, 77, "itunes", "12345")


def test_load_target_comedians_defaults_to_missing_accepted_links_and_review_history(monkeypatch) -> None:
    conn = _FakeConn()
    monkeypatch.setattr(mod, "get_connection", lambda *_, **__: conn)

    rows = mod.load_target_comedians(
        comedian_ids=[12],
        comedian_names=None,
        limit=5,
        include_reviewed=False,
    )

    query, params = conn.executed[0]
    assert "NOT EXISTS" in query
    assert "FROM comedian_podcasts cp" in query
    assert "cp.review_status = 'accepted'" in query
    assert "FROM podcast_candidate_reviews r" in query
    assert rows == [PodcastDiscoveryComedian(12, "Taylor Comic", ["Taylor C"])]
    assert params == ([12], 5)


def test_load_target_comedians_can_include_previous_review_history(monkeypatch) -> None:
    conn = _FakeConn()
    monkeypatch.setattr(mod, "get_connection", lambda *_, **__: conn)

    mod.load_target_comedians(
        comedian_ids=None,
        comedian_names=["Taylor Comic"],
        limit=None,
        include_reviewed=True,
    )

    query, params = conn.executed[0]
    assert "FROM podcast_candidate_reviews r" not in query
    assert "FROM comedian_podcasts cp" not in query
    assert params == (["Taylor Comic"],)


def test_backfill_dry_run_prints_before_after_and_writes_nothing(monkeypatch, capsys) -> None:
    conn = _FakeConn()
    upserts: list[Any] = []

    monkeypatch.setattr(mod, "get_connection", lambda *_, **__: conn)
    monkeypatch.setattr(mod, "discover_candidates_for_comedians", lambda *_, **__: ([_candidate()], 0))
    monkeypatch.setattr(
        mod,
        "upsert_candidate_with_conn",
        lambda *_args, **_kwargs: upserts.append(_args) or UpsertResult(42, "upserted_source"),
    )

    summary = mod.search_itunes_podcasts(
        dry_run=True,
        confirm=False,
        limit=1,
        comedian_ids=None,
        comedian_names=None,
        max_results=5,
        country="US",
        request_delay=0,
        include_reviewed=False,
        min_confidence=0.8,
    )

    output = capsys.readouterr().out
    assert "=== BEFORE ===" in output
    assert "=== AFTER ===" in output
    assert "--dry-run: 1 writes planned (none applied)." in output
    assert "candidate comedian_id=12 podcast='Taylor Comic Podcast'" in output
    assert summary == mod.SearchSummary(processed=1, candidates=1, written=0, failed=0)
    assert upserts == []
    assert conn.commits == 0
    assert conn.rollbacks == 0


def test_backfill_confirm_upserts_candidate_reviews(monkeypatch) -> None:
    conn = _FakeConn()
    upserts: list[ItunesPodcastCandidate] = []

    monkeypatch.setattr(mod, "get_connection", lambda *_, **__: conn)
    monkeypatch.setattr(mod, "discover_candidates_for_comedians", lambda *_, **__: ([_candidate()], 0))

    def fake_upsert(_conn: Any, candidate: ItunesPodcastCandidate) -> UpsertResult:
        upserts.append(candidate)
        return UpsertResult(42, "upserted_source")

    monkeypatch.setattr(mod, "upsert_candidate_with_conn", fake_upsert)

    summary = mod.search_itunes_podcasts(
        dry_run=False,
        confirm=True,
        limit=1,
        comedian_ids=None,
        comedian_names=None,
        max_results=5,
        country="US",
        request_delay=0,
        include_reviewed=False,
        min_confidence=0.8,
    )

    assert summary.written == 1
    assert upserts == [_candidate()]
    assert conn.commits == 1
    assert conn.rollbacks == 0


def test_cli_requires_exactly_one_mode(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["search_itunes_podcasts.py"])

    try:
        mod.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("main should exit for missing mode")

    assert "choose exactly one of --dry-run or --confirm" in capsys.readouterr().err


def test_cli_passes_filters(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_search(**kwargs: Any) -> mod.SearchSummary:
        calls.append(kwargs)
        return mod.SearchSummary(processed=0, candidates=0, written=0, failed=0)

    monkeypatch.setattr(mod, "search_itunes_podcasts", fake_search)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "search_itunes_podcasts.py",
            "--dry-run",
            "--limit",
            "3",
            "--comedian-ids",
            "12",
            "13",
            "--comedian-names",
            "Taylor Comic",
            "--max-results",
            "9",
            "--country",
            "CA",
            "--request-delay",
            "0.2",
            "--min-confidence",
            "0.7",
            "--include-reviewed",
        ],
    )

    assert mod.main() == 0
    assert calls == [
        {
            "dry_run": True,
            "confirm": False,
            "limit": 3,
            "comedian_ids": [12, 13],
            "comedian_names": ["Taylor Comic"],
            "max_results": 9,
            "country": "CA",
            "request_delay": 0.2,
            "include_reviewed": True,
            "min_confidence": 0.7,
        }
    ]
