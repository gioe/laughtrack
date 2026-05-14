from __future__ import annotations

import asyncio
import json
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
    payload: dict[str, Any] | str
    headers: dict[str, str] | None = None

    def json(self) -> dict[str, Any]:
        if not isinstance(self.payload, dict):
            raise ValueError("not JSON")
        return self.payload

    @property
    def text(self) -> str:
        if isinstance(self.payload, str):
            return self.payload
        return json.dumps(self.payload)


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]):
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    async def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.requests.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected extra request")
        return self.responses.pop(0)


def _person_search_payload() -> dict[str, Any]:
    return {
        "status": "true",
        "items": [
            {
                "id": 987,
                "feedId": 456,
                "guid": "rss-guid-1",
                "title": "Index Title For Ari Shaffir",
                "datePublished": 1704261600,
                "link": "https://podcast.example/index-link",
                "feedTitle": "Comedy Talk From Index",
                "feedUrl": "https://feeds.example/comedy-talk.xml",
                "enclosureUrl": "https://cdn.example/ari.mp3",
            },
            {
                "id": 654,
                "feedId": 456,
                "guid": "low-guid",
                "title": "Unrelated Episode",
                "datePublished": 1704348000,
                "link": "https://podcast.example/unrelated",
                "feedTitle": "Comedy Talk",
                "feedUrl": "https://feeds.example/comedy-talk.xml",
            },
            {
                "id": None,
                "feedId": 456,
                "title": "Missing ID Is Ignored",
                "feedTitle": "Comedy Talk",
                "feedUrl": "https://feeds.example/comedy-talk.xml",
            },
        ],
    }


def _rss_feed() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Comedy Talk RSS</title>
    <item>
      <guid>rss-guid-1</guid>
      <title>RSS Title: Ari Shaffir Returns</title>
      <link>https://podcast.example/rss-link</link>
      <pubDate>Wed, 03 Jan 2024 10:00:00 GMT</pubDate>
      <enclosure url="https://cdn.example/ari.mp3" type="audio/mpeg" />
    </item>
  </channel>
</rss>
"""


def test_build_podcast_index_headers_signs_key_secret_and_timestamp(monkeypatch):
    monkeypatch.setattr(mod.time, "time", lambda: 1700000000.4)

    headers = mod._build_podcast_index_headers(
        mod.PodcastIndexCredentials(
            api_key="key",
            api_secret="secret",
            user_agent="LaughTrackTest/1.0",
        )
    )

    assert headers == {
        "User-Agent": "LaughTrackTest/1.0",
        "X-Auth-Date": "1700000000",
        "X-Auth-Key": "key",
        "Authorization": "abaf71c02050c31e4d4e6b08c1625173af0445ba",
        "Accept": "application/json",
    }


def test_build_person_search_params_uses_podcast_index_person_endpoint():
    params = mod._build_person_search_params("Ari Shaffir", max_episodes=25)

    assert params == {"q": "Ari Shaffir", "max": 25, "fulltext": ""}


def test_parse_candidate_rows_prefers_matching_rss_metadata():
    rows = mod._parse_candidate_rows(
        comedian_id=12,
        comedian_name="Ari Shaffir",
        payload=_person_search_payload(),
        rss_by_feed_url={"https://feeds.example/comedy-talk.xml": _rss_feed()},
    )

    assert rows[0] == mod.PodcastAppearanceRow(
        comedian_id=12,
        source="podcast_index",
        source_episode_id="987",
        podcast_name="Comedy Talk RSS",
        episode_title="RSS Title: Ari Shaffir Returns",
        release_date="2024-01-03T10:00:00+00:00",
        episode_url="https://podcast.example/rss-link",
        match_confidence=1.0,
        match_evidence={
            "search_term": "Ari Shaffir",
            "matched_terms": ["ari", "shaffir"],
            "episode_title": "RSS Title: Ari Shaffir Returns",
            "podcast_name": "Comedy Talk RSS",
            "podcast_index_episode_id": 987,
            "podcast_index_guid": "rss-guid-1",
            "source_feed_id": "456",
            "source_feed_url": "https://feeds.example/comedy-talk.xml",
            "feed_url": "https://feeds.example/comedy-talk.xml",
            "metadata_source": "rss",
        },
    )
    assert rows[1].source_episode_id == "654"
    assert rows[1].episode_title == "Unrelated Episode"
    assert rows[1].match_confidence == 0.0
    assert rows[1].match_evidence["metadata_source"] == "podcast_index"


def test_fetch_podcast_index_episode_result_fetches_rss_for_candidates(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    session = _FakeSession(
        [
            _FakeResponse(429, {"error": "rate limited"}, {"Retry-After": "7"}),
            _FakeResponse(200, _person_search_payload(), {}),
            _FakeResponse(200, _rss_feed(), {}),
        ]
    )
    monkeypatch.setattr(mod.asyncio, "sleep", fake_sleep)

    result = asyncio.run(
        mod._fetch_podcast_index_episode_result(
            session=session,
            comedian_id=12,
            comedian_name="Ari Shaffir",
            credentials=mod.PodcastIndexCredentials("key", "secret", "ua"),
            max_episodes=25,
        )
    )

    assert result.succeeded is True
    assert [request["url"] for request in session.requests] == [
        "https://api.podcastindex.org/api/1.0/search/byperson",
        "https://api.podcastindex.org/api/1.0/search/byperson",
        "https://feeds.example/comedy-talk.xml",
    ]
    assert session.requests[1]["params"] == {"q": "Ari Shaffir", "max": 25, "fulltext": ""}
    assert sleeps == [7.0]
    assert result.rows[0].episode_title == "RSS Title: Ari Shaffir Returns"


def test_populate_writes_low_confidence_matches_to_audit_path_not_database(monkeypatch, tmp_path):
    session = _FakeSession(
        [
            _FakeResponse(200, _person_search_payload(), {}),
            _FakeResponse(200, _rss_feed(), {}),
        ]
    )
    replace_calls: list[tuple[list[int], list[mod.PodcastAppearanceRow]]] = []
    audit_path = tmp_path / "podcast-audit.jsonl"

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
            credentials=mod.PodcastIndexCredentials("key", "secret", "ua"),
            max_episodes=25,
            dry_run=False,
            batch_size=10,
            request_delay=0.0,
            audit_path=audit_path,
            min_confidence=0.75,
        )
    )

    assert summary == {
        "processed": 1,
        "failed": 0,
        "matched_episodes": 2,
        "written": 1,
        "audit_rows": 1,
        "suppressed_rows": 0,
    }
    assert replace_calls[0][0] == [12]
    assert [row.source_episode_id for row in replace_calls[0][1]] == ["987"]
    audit_rows = [json.loads(line) for line in audit_path.read_text().splitlines()]
    assert audit_rows[0]["source_episode_id"] == "654"
    assert audit_rows[0]["match_confidence"] == 0.0


def test_populate_preserves_existing_rows_for_failed_lookups(monkeypatch, tmp_path):
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
            credentials=mod.PodcastIndexCredentials("key", "secret", "ua"),
            max_episodes=25,
            dry_run=False,
            batch_size=10,
            request_delay=0.0,
            audit_path=tmp_path / "audit.jsonl",
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
            source_episode_id="987",
            podcast_name="Comedy Talk",
            episode_title="Ari Shaffir Returns",
            release_date="2024-01-03T10:00:00+00:00",
            episode_url="https://podcast.example/ep-1",
            match_confidence=1.0,
            match_evidence={
                "search_term": "Ari Shaffir",
                "matched_terms": ["ari", "shaffir"],
                "episode_title": "Ari Shaffir Returns",
                "podcast_name": "Comedy Talk",
            },
        )
    ]

    written = mod._replace_appearances(_Conn(), comedian_ids=[12, 13], rows=rows)

    assert written == 1
    assert calls[0][0].strip().startswith("DELETE FROM comedian_podcast_appearances")
    assert calls[0][1] == ([12, 13], "podcast_index")
    assert values_calls[0][1][0][:8] == (
        12,
        "podcast_index",
        "987",
        "Comedy Talk",
        "Ari Shaffir Returns",
        "2024-01-03T10:00:00+00:00",
        "https://podcast.example/ep-1",
        1.0,
    )
    assert "source_episode_id" in values_calls[0][0]
    assert "ON CONFLICT (comedian_id, source, source_episode_id)" in values_calls[0][0]


def test_reviewed_identity_links_promote_verified_feed_candidates(monkeypatch, tmp_path):
    session = _FakeSession(
        [
            _FakeResponse(200, _person_search_payload(), {}),
            _FakeResponse(200, _rss_feed(), {}),
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
            credentials=mod.PodcastIndexCredentials("key", "secret", "ua"),
            max_episodes=25,
            dry_run=False,
            batch_size=10,
            request_delay=0.0,
            audit_path=tmp_path / "audit.jsonl",
            min_confidence=0.75,
            identity_links={
                (12, "456"): mod.PodcastIdentityLink(
                    comedian_id=12,
                    source_feed_id="456",
                    review_status="verified",
                )
            },
        )
    )

    assert summary["written"] == 2
    assert summary["matched_episodes"] == 2
    assert summary["audit_rows"] == 0
    assert summary["suppressed_rows"] == 0
    assert [row.source_episode_id for row in replace_calls[0][1]] == ["987", "654"]


def test_reviewed_identity_links_suppress_rejected_feed_candidates(monkeypatch, tmp_path):
    session = _FakeSession(
        [
            _FakeResponse(200, _person_search_payload(), {}),
            _FakeResponse(200, _rss_feed(), {}),
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
            credentials=mod.PodcastIndexCredentials("key", "secret", "ua"),
            max_episodes=25,
            dry_run=False,
            batch_size=10,
            request_delay=0.0,
            audit_path=tmp_path / "audit.jsonl",
            min_confidence=0.75,
            identity_links={
                (12, "456"): mod.PodcastIdentityLink(
                    comedian_id=12,
                    source_feed_id="456",
                    review_status="rejected",
                )
            },
        )
    )

    assert summary["written"] == 0
    assert summary["matched_episodes"] == 2
    assert summary["audit_rows"] == 0
    assert summary["suppressed_rows"] == 2
    assert replace_calls[0] == ([12], [])
