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

    def json(self) -> dict[str, Any]:
        return self.payload


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]):
        self.responses = responses
        self.posts: list[dict[str, Any]] = []

    async def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.posts.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected extra Podchaser request")
        return self.responses.pop(0)


def _episode_payload() -> dict[str, Any]:
    return {
        "data": {
            "episodes": {
                "data": [
                    {
                        "id": "ep-1",
                        "title": "Ari Shaffir Returns",
                        "airDate": "2024-01-03T10:00:00Z",
                        "url": "https://www.podchaser.com/podcasts/example/episodes/ari-shaffir-returns-1",
                        "webUrl": "https://feeds.example/ari-shaffir-returns",
                        "podcast": {"title": "Comedy Talk"},
                    },
                    {
                        "id": "ep-2",
                        "title": "Unrelated Episode",
                        "airDate": None,
                        "url": "https://www.podchaser.com/podcasts/example/episodes/unrelated-2",
                        "webUrl": None,
                        "podcast": {"title": "Comedy Talk"},
                    },
                    {
                        "id": None,
                        "title": "Missing ID Is Ignored",
                        "airDate": "2024-02-01T00:00:00Z",
                        "url": "https://example.invalid/missing-id",
                        "podcast": {"title": "Comedy Talk"},
                    },
                ]
            }
        }
    }


def test_build_episode_search_payload_requests_minimal_episode_fields():
    payload = mod._build_episode_search_payload("Ari Shaffir", first=25)

    assert payload["variables"] == {"searchTerm": "Ari Shaffir", "first": 25}
    query = payload["query"]
    assert "episodes(searchTerm: $searchTerm" in query
    assert "id" in query
    assert "title" in query
    assert "airDate" in query
    assert "url" in query
    assert "webUrl" in query
    assert "podcast" in query


def test_parse_episode_rows_skips_incomplete_episodes_and_prefers_podchaser_url():
    rows = mod._parse_episode_rows(comedian_id=12, payload=_episode_payload())

    assert rows == [
        mod.PodcastAppearanceRow(
            comedian_id=12,
            podchaser_episode_id="ep-1",
            podcast_name="Comedy Talk",
            episode_title="Ari Shaffir Returns",
            release_date="2024-01-03T10:00:00Z",
            episode_url="https://www.podchaser.com/podcasts/example/episodes/ari-shaffir-returns-1",
        ),
        mod.PodcastAppearanceRow(
            comedian_id=12,
            podchaser_episode_id="ep-2",
            podcast_name="Comedy Talk",
            episode_title="Unrelated Episode",
            release_date=None,
            episode_url="https://www.podchaser.com/podcasts/example/episodes/unrelated-2",
        ),
    ]


def test_fetch_podchaser_episodes_retries_429_retry_after(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    session = _FakeSession(
        [
            _FakeResponse(429, {"errors": [{"message": "rate limited"}]}, {"Retry-After": "7"}),
            _FakeResponse(
                200,
                _episode_payload(),
                {
                    "X-Podchaser-Points-Remaining": "1000",
                    "X-Podchaser-Query-Cost": "12",
                },
            ),
        ]
    )
    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)

    rows = asyncio.run(
        mod._fetch_podchaser_episodes(
            session,
            comedian_id=12,
            comedian_name="Ari Shaffir",
            token="token",
            first=25,
        )
    )

    assert sleeps == [7.0]
    assert len(rows) == 2
    assert len(session.posts) == 2
    assert session.posts[0]["headers"]["Authorization"] == "Bearer token"


def test_fetch_podchaser_episodes_returns_empty_on_graphql_errors():
    session = _FakeSession(
        [_FakeResponse(200, {"errors": [{"message": "no permission"}]}, {})]
    )

    rows = asyncio.run(
        mod._fetch_podchaser_episodes(
            session,
            comedian_id=12,
            comedian_name="Ari Shaffir",
            token="token",
            first=25,
        )
    )

    assert rows == []


def test_populate_continues_after_transient_failure(monkeypatch):
    session = _FakeSession(
        [
            _FakeResponse(503, {"errors": [{"message": "temporarily unavailable"}]}, {}),
            _FakeResponse(503, {"errors": [{"message": "temporarily unavailable"}]}, {}),
            _FakeResponse(503, {"errors": [{"message": "temporarily unavailable"}]}, {}),
            _FakeResponse(200, _episode_payload(), {}),
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
            token="token",
            first=25,
            dry_run=True,
        )
    )

    assert summary["processed"] == 2
    assert summary["matched_episodes"] == 2
    assert len(session.posts) == 4


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
            podchaser_episode_id="ep-1",
            podcast_name="Comedy Talk",
            episode_title="Ari Shaffir Returns",
            release_date="2024-01-03T10:00:00Z",
            episode_url="https://podchaser.example/ep-1",
        )
    ]

    written = mod._replace_appearances(_Conn(), comedian_ids=[12, 13], rows=rows)

    assert written == 1
    assert calls[0][0].strip().startswith("DELETE FROM comedian_podcast_appearances")
    assert calls[0][1] == ([12, 13],)
    assert values_calls[0][1] == [
        (
            12,
            "ep-1",
            "Comedy Talk",
            "Ari Shaffir Returns",
            "2024-01-03T10:00:00Z",
            "https://podchaser.example/ep-1",
        )
    ]
