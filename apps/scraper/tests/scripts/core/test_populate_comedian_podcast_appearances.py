from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import populate_comedian_podcast_appearances as mod  # noqa: E402


@dataclass
class _FakeResponse:
    status_code: int
    payload: dict[str, Any]
    headers: dict[str, str] | None = None
    text: str = ""

    def json(self) -> dict[str, Any]:
        return self.payload


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]):
        self.responses = responses
        self.gets: list[dict[str, Any]] = []

    async def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.gets.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected extra Podcast Index request")
        return self.responses.pop(0)


def _podcast_index_payload() -> dict[str, Any]:
    return {
        "status": True,
        "items": [
            {
                "id": 101,
                "feedId": 2001,
                "feedTitle": "Comedy Talk",
                "title": "Ari Shaffir Returns",
                "datePublished": 1704276000,
                "link": "https://podcast.example/ari-shaffir-returns",
            },
            {
                "id": 102,
                "feedId": 2001,
                "feedTitle": "Comedy Talk",
                "title": "Unrelated Episode",
                "datePublished": None,
                "link": "https://podcast.example/unrelated",
            },
            {
                "id": None,
                "feedTitle": "Comedy Talk",
                "title": "Missing ID Is Ignored",
            },
        ],
    }


def test_build_person_search_params_requests_expected_episode_count():
    params = mod._build_person_search_params("Ari Shaffir", max_episodes=25)

    assert params == {"q": "Ari Shaffir", "max": 25, "fulltext": ""}


def test_parse_candidate_rows_skips_incomplete_episodes_and_records_podcast_index_evidence():
    rows = mod._parse_candidate_rows(
        comedian_id=12,
        comedian_name="Ari Shaffir",
        payload=_podcast_index_payload(),
        rss_by_feed_url={},
    )

    assert rows == [
        mod.PodcastAppearanceRow(
            comedian_id=12,
            source="podcast_index",
            source_episode_id="101",
            podcast_name="Comedy Talk",
            episode_title="Ari Shaffir Returns",
            release_date="2024-01-03T10:00:00+00:00",
            episode_url="https://podcast.example/ari-shaffir-returns",
            match_confidence=1.0,
            match_evidence={
                "search_term": "Ari Shaffir",
                "matched_terms": ["ari", "shaffir"],
                "episode_title": "Ari Shaffir Returns",
                "podcast_name": "Comedy Talk",
                "podcast_index_episode_id": 101,
                "podcast_index_guid": None,
                "source_feed_id": "2001",
                "source_feed_url": None,
                "feed_url": None,
                "metadata_source": "podcast_index",
            },
        ),
        mod.PodcastAppearanceRow(
            comedian_id=12,
            source="podcast_index",
            source_episode_id="102",
            podcast_name="Comedy Talk",
            episode_title="Unrelated Episode",
            release_date=None,
            episode_url="https://podcast.example/unrelated",
            match_confidence=0.0,
            match_evidence={
                "search_term": "Ari Shaffir",
                "matched_terms": [],
                "episode_title": "Unrelated Episode",
                "podcast_name": "Comedy Talk",
                "podcast_index_episode_id": 102,
                "podcast_index_guid": None,
                "source_feed_id": "2001",
                "source_feed_url": None,
                "feed_url": None,
                "metadata_source": "podcast_index",
            },
        ),
    ]


def test_fetch_podcast_index_episode_result_retries_429_retry_after(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    session = _FakeSession(
        [
            _FakeResponse(429, {"errors": [{"message": "rate limited"}]}, {"Retry-After": "7"}),
            _FakeResponse(
                200,
                _podcast_index_payload(),
            ),
        ]
    )
    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)

    result = asyncio.run(
        mod._fetch_podcast_index_episode_result(
            session=session,
            comedian_id=12,
            comedian_name="Ari Shaffir",
            credentials=mod.PodcastIndexCredentials(api_key="key", api_secret="secret"),
            max_episodes=25,
        )
    )

    assert sleeps == [7.0]
    assert result.succeeded is True
    assert len(result.rows) == 2
    assert len(session.gets) == 2
    assert session.gets[0]["params"] == {"q": "Ari Shaffir", "max": 25, "fulltext": ""}
    assert session.gets[0]["headers"]["X-Auth-Key"] == "key"


def test_fetch_podcast_index_episode_result_returns_empty_on_unsuccessful_response():
    session = _FakeSession([_FakeResponse(200, {"status": False, "description": "no permission"}, {})])

    result = asyncio.run(
        mod._fetch_podcast_index_episode_result(
            session=session,
            comedian_id=12,
            comedian_name="Ari Shaffir",
            credentials=mod.PodcastIndexCredentials(api_key="key", api_secret="secret"),
            max_episodes=25,
        )
    )

    assert result == mod.PodcastAppearanceFetchResult(succeeded=False, rows=[])


def test_load_target_comedians_excludes_deny_listed_names(monkeypatch):
    calls: list[tuple[str, Any]] = []

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_exc: Any) -> bool:
            return False

        def execute(self, sql: str, params: Any = None) -> None:
            calls.append((sql, params))

        def fetchall(self) -> list[tuple[int, str]]:
            return [(12, "Ari Shaffir")]

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *_exc: Any) -> bool:
            return False

        def cursor(self) -> _Cursor:
            return _Cursor()

    monkeypatch.setattr(mod, "get_connection", lambda: _Conn())

    comedians = mod._load_target_comedians(
        comedian_ids=None,
        comedian_name=None,
        limit=10,
    )

    assert comedians == [(12, "Ari Shaffir")]
    sql, params = calls[0]
    assert "comedian_deny_list" in sql
    assert "LOWER(BTRIM(d.name)) = LOWER(BTRIM(comedians.name))" in sql
    assert params is None


def test_populate_continues_after_transient_failure(monkeypatch):
    session = _FakeSession(
        [
            _FakeResponse(503, {"errors": [{"message": "temporarily unavailable"}]}, {}),
            _FakeResponse(503, {"errors": [{"message": "temporarily unavailable"}]}, {}),
            _FakeResponse(503, {"errors": [{"message": "temporarily unavailable"}]}, {}),
            _FakeResponse(200, _podcast_index_payload(), {}),
        ]
    )

    async def fake_sleep(_seconds: float) -> None:
        return None

    class _FakeAsyncSessionCtx:
        def __init__(self, *_args: Any, **_kwargs: Any):
            pass

        async def __aenter__(self) -> _FakeSession:
            return session

        async def __aexit__(self, *_exc: Any) -> bool:
            return False

    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(mod, "AsyncSession", _FakeAsyncSessionCtx)

    summary = asyncio.run(
        mod._populate(
            comedians=[(12, "Ari Shaffir"), (13, "Maria Bamford")],
            credentials=mod.PodcastIndexCredentials(api_key="key", api_secret="secret"),
            max_episodes=25,
            dry_run=True,
            batch_size=10,
            request_delay=0,
            audit_path=Path("tmp/audit.jsonl"),
            min_confidence=0.75,
        )
    )

    assert summary["processed"] == 2
    assert summary["matched_episodes"] == 2
    assert len(session.gets) == 4


def test_populate_preserves_existing_rows_for_failed_lookups(monkeypatch):
    session = _FakeSession(
        [
            _FakeResponse(503, {"errors": [{"message": "temporarily unavailable"}]}, {}),
            _FakeResponse(503, {"errors": [{"message": "temporarily unavailable"}]}, {}),
            _FakeResponse(503, {"errors": [{"message": "temporarily unavailable"}]}, {}),
        ]
    )
    replace_calls: list[tuple[list[int], list[mod.PodcastAppearanceRow]]] = []

    async def fake_sleep(_seconds: float) -> None:
        return None

    class _FakeAsyncSessionCtx:
        def __init__(self, *_args: Any, **_kwargs: Any):
            pass

        async def __aenter__(self) -> _FakeSession:
            return session

        async def __aexit__(self, *_exc: Any) -> bool:
            return False

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *_exc: Any) -> bool:
            return False

        def commit(self) -> None:
            pass

    def fake_replace(_conn: Any, comedian_ids: list[int], rows: list[mod.PodcastAppearanceRow]) -> int:
        replace_calls.append((comedian_ids, rows))
        return len(rows)

    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(mod, "AsyncSession", _FakeAsyncSessionCtx)
    monkeypatch.setattr(mod, "get_connection", lambda: _Conn())
    monkeypatch.setattr(mod, "_replace_appearances", fake_replace)

    summary = asyncio.run(
        mod._populate(
            comedians=[(12, "Ari Shaffir")],
            credentials=mod.PodcastIndexCredentials(api_key="key", api_secret="secret"),
            max_episodes=25,
            dry_run=False,
            batch_size=10,
            request_delay=0,
            audit_path=Path("tmp/audit.jsonl"),
            min_confidence=0.75,
        )
    )

    assert summary["processed"] == 1
    assert summary["failed"] == 1
    assert summary["written"] == 0
    assert replace_calls == []


def test_write_rows_replaces_only_processed_comedians(monkeypatch):
    calls: list[tuple[str, Any]] = []
    values_calls: list[tuple[str, list[tuple[Any, ...]], str]] = []

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def execute(self, sql: str, params: Any = None) -> None:
            calls.append((sql, params))

    class _Conn:
        def cursor(self):
            return _Cursor()

    def fake_execute_values(cur: Any, sql: str, values: list[tuple[Any, ...]], template: str) -> None:
        values_calls.append((sql, values, template))

    monkeypatch.setattr(mod, "execute_values", fake_execute_values)

    rows = [
        mod.PodcastAppearanceRow(
            comedian_id=12,
            source="podcast_index",
            source_episode_id="ep-1",
            podcast_name="Comedy Talk",
            episode_title="Ari Shaffir Returns",
            release_date="2024-01-03T10:00:00Z",
            episode_url="https://podchaser.example/ep-1",
            match_confidence=0.95,
            match_evidence={"metadata_source": "podcast_index"},
        )
    ]

    written = mod._replace_appearances(_Conn(), comedian_ids=[12, 13], rows=rows)

    assert written == 1
    assert calls[0][0].strip().startswith("DELETE FROM comedian_podcast_appearances")
    assert calls[0][1] == ([12, 13], "podcast_index")
    assert values_calls[0][1] == [
        (
            12,
            "podcast_index",
            "ep-1",
            "Comedy Talk",
            "Ari Shaffir Returns",
            "2024-01-03T10:00:00Z",
            "https://podchaser.example/ep-1",
            0.95,
            '{"metadata_source": "podcast_index"}',
        )
    ]
