from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from laughtrack.core.clients.google.custom_search import SearchResult  # noqa: E402
from scripts.core import discover_comedian_tour_sources as mod  # noqa: E402


class _FakeCursor:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


class _FakeConnection:
    def __init__(self, rows: list[dict[str, Any]]):
        self.cursor_obj = _FakeCursor(rows)
        self.commits = 0

    def cursor(self, *_args, **_kwargs):
        return self.cursor_obj

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        pass


class _FakeBraveClient:
    is_configured = True
    queries_remaining = 20
    source_name = "brave_search"

    def __init__(self):
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, num_results: int = 10) -> list[SearchResult]:
        self.calls.append((query, num_results))
        if "Bandsintown" in query:
            return [
                SearchResult(
                    title="Jane Example Tour Dates",
                    link="https://www.bandsintown.com/a/123-jane-example",
                    snippet="Jane Example tickets and upcoming shows",
                    display_link="https://www.bandsintown.com/a/123-jane-example",
                )
            ]
        if "Songkick" in query:
            return [
                SearchResult(
                    title="Jane Example Tickets",
                    link="https://www.songkick.com/artists/456-jane-example",
                    snippet="Concerts and tour dates",
                    display_link="https://www.songkick.com/artists/456-jane-example",
                )
            ]
        return [
            SearchResult(
                title="Jane Example Official Tour",
                link="https://jane.example/tour",
                snippet="Jane Example tour dates and tickets",
                display_link="https://jane.example/tour",
            )
        ]


def test_candidate_query_limits_to_canonical_non_denied_comedians_with_history():
    query = mod._GET_TOUR_DISCOVERY_CANDIDATES

    assert "parent_comedian_id IS NULL" in query
    assert "total_shows > 0" in query
    assert "NOT EXISTS" in query
    assert "comedian_deny_list" in query
    assert "NULLIF(BTRIM(c.name), '') IS NOT NULL" in query


def test_tour_queries_include_general_ticketing_bandsintown_and_songkick_intent():
    queries = mod.build_tour_search_queries("Jane Example")

    assert queries == [
        "Jane Example tour dates",
        "Jane Example tickets upcoming shows",
        "Jane Example upcoming shows",
        "Jane Example Bandsintown",
        "Jane Example Songkick",
    ]


def test_dry_run_reports_candidate_urls_without_database_writes(monkeypatch, capsys):
    conn = _FakeConnection([
        {"uuid": "comic-1", "name": "Jane Example", "total_shows": 12},
    ])
    client = _FakeBraveClient()

    monkeypatch.setattr(mod, "create_connection", lambda autocommit: conn)
    monkeypatch.setattr(mod, "BraveSearchClient", lambda: client)

    results = mod.discover_tour_sources(limit=1, comedian_name=None, dry_run=True)

    captured = capsys.readouterr()
    assert conn.commits == 0
    assert [call[0] for call in client.calls] == mod.build_tour_search_queries("Jane Example")
    assert len(results) == 3
    assert results[0].url == "https://jane.example/tour"
    assert results[0].query == "Jane Example tour dates"
    assert results[0].rank == 1
    assert results[0].source_type == "official"
    assert results[0].confidence == "high"
    assert "DRY RUN" in captured.out
    assert "Jane Example" in captured.out
    assert "https://jane.example/tour" in captured.out
    assert "query=Jane Example tour dates" in captured.out
    assert "rank=1" in captured.out
    assert "source_type=official" in captured.out
    assert "confidence=high" in captured.out


def test_name_filter_and_limit_are_passed_to_candidate_query(monkeypatch):
    conn = _FakeConnection([])

    monkeypatch.setattr(mod, "create_connection", lambda autocommit: conn)

    candidates = mod.load_candidate_comedians(limit=7, comedian_name="Jane")

    query, params = conn.cursor_obj.executed[0]
    assert candidates == []
    assert "c.name ILIKE %s" in query
    assert "LIMIT %s" in query
    assert params == ("%Jane%", 7)


def test_cli_supports_limit_comedian_name_and_dry_run_flags(monkeypatch):
    calls: list[dict[str, Any]] = []

    def fake_discover_tour_sources(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(mod, "discover_tour_sources", fake_discover_tour_sources)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "discover_comedian_tour_sources.py",
            "--limit",
            "3",
            "--comedian-name",
            "Jane Example",
            "--dry-run",
        ],
    )

    assert mod.main() == 0
    assert calls == [{"limit": 3, "comedian_name": "Jane Example", "dry_run": True}]
