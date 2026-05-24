from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

import sys

_repo_root = Path(__file__).resolve().parents[2]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from laughtrack.core import rss_episode_reader as mod  # noqa: E402


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = headers or {}


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
        if normalized.startswith("INSERT INTO podcast_episodes"):
            self.conn.upserts.append(params)
            self._last_result = [(1000 + len(self.conn.upserts), len(self.conn.upserts) == 1)]
        elif normalized.startswith("UPDATE podcasts"):
            self.conn.podcast_updates.append(params)
            self._last_result = []
        else:
            self._last_result = []

    def fetchone(self) -> Any:
        return self._last_result[0] if self._last_result else None


class _FakeConn:
    def __init__(self) -> None:
        self.executed: list[tuple[str, Any]] = []
        self.upserts: list[Any] = []
        self.podcast_updates: list[Any] = []

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)


def _podcast(**overrides: Any) -> mod.PodcastRssFeed:
    values = {
        "podcast_id": 42,
        "source": "itunes",
        "source_podcast_id": "12345",
        "feed_url": "https://feeds.example.com/show.xml",
        "title": "Comedy Talk",
        "source_payload": {
            "collectionId": 12345,
            "rss_episode_reader": {
                "etag": '"cached-etag"',
                "last_modified": "Wed, 01 May 2024 00:00:00 GMT",
            },
        },
    }
    values.update(overrides)
    return mod.PodcastRssFeed(**values)


def test_fetches_rss_with_conditional_cache_headers_and_parses_entries(monkeypatch):
    calls: list[dict[str, Any]] = []
    rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel><title>Comedy Talk</title>
      <item>
        <guid isPermaLink="false">episode-guid-1</guid>
        <title>Taylor Comic Returns</title>
        <description>A long interview</description>
        <pubDate>Wed, 01 May 2024 08:00:00 GMT</pubDate>
        <link>https://podcast.example/episodes/1</link>
        <enclosure url="https://cdn.example/audio.mp3" length="123" type="audio/mpeg" />
        <itunes:duration xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">01:01:01</itunes:duration>
      </item>
    </channel></rss>
    """

    def fake_get(url: str, **kwargs: Any) -> _FakeResponse:
        calls.append({"url": url, **kwargs})
        return _FakeResponse(
            text=rss,
            headers={"ETag": '"fresh-etag"', "Last-Modified": "Thu, 02 May 2024 00:00:00 GMT"},
        )

    monkeypatch.setattr(mod.requests, "get", fake_get)

    result = mod.fetch_rss_episodes(_podcast())

    assert calls[0]["url"] == "https://feeds.example.com/show.xml"
    assert calls[0]["headers"]["If-None-Match"] == '"cached-etag"'
    assert calls[0]["headers"]["If-Modified-Since"] == "Wed, 01 May 2024 00:00:00 GMT"
    assert result.not_modified is False
    assert result.etag == '"fresh-etag"'
    assert result.last_modified == "Thu, 02 May 2024 00:00:00 GMT"
    assert result.episodes == [
        mod.RssEpisodeRow(
            podcast_id=42,
            source="itunes",
            source_episode_id="episode-guid-1",
            guid="episode-guid-1",
            title="Taylor Comic Returns",
            description="A long interview",
            release_date="2024-05-01T08:00:00+00:00",
            duration_seconds=3661,
            episode_url="https://podcast.example/episodes/1",
            audio_url="https://cdn.example/audio.mp3",
            external_ids={"rss_guid": "episode-guid-1"},
            evidence={
                "provider": "rss",
                "source_podcast_id": "12345",
                "feed_url": "https://feeds.example.com/show.xml",
                "episode_url": "https://podcast.example/episodes/1",
                "audio_url": "https://cdn.example/audio.mp3",
            },
            source_payload=result.episodes[0].source_payload,
        )
    ]


def test_not_modified_response_skips_feed_parsing(monkeypatch):
    monkeypatch.setattr(
        mod.requests,
        "get",
        lambda *_args, **_kwargs: _FakeResponse(status_code=304, headers={"ETag": '"same"'}),
    )

    result = mod.fetch_rss_episodes(_podcast())

    assert result.not_modified is True
    assert result.episodes == []


def test_malformed_feed_raises_parse_error(monkeypatch):
    monkeypatch.setattr(mod.requests, "get", lambda *_args, **_kwargs: _FakeResponse(text="not xml"))

    with pytest.raises(mod.RssFeedParseError, match="malformed RSS feed"):
        mod.fetch_rss_episodes(_podcast())


def test_sync_upserts_deduped_guid_rows_with_parent_source(monkeypatch):
    conn = _FakeConn()
    fetched = mod.RssFetchResult(
        episodes=[
            mod.RssEpisodeRow(
                podcast_id=42,
                source="itunes",
                source_episode_id="rss-guid-1",
                guid="rss-guid-1",
                title="Stored",
                description=None,
                release_date=datetime(2024, 5, 1, tzinfo=timezone.utc).isoformat(),
                duration_seconds=None,
                episode_url="https://podcast.example/1",
                audio_url=None,
                external_ids={"rss_guid": "rss-guid-1"},
                evidence={"provider": "rss"},
                source_payload={"id": "rss-guid-1"},
            ),
            mod.RssEpisodeRow(
                podcast_id=42,
                source="itunes",
                source_episode_id="rss-guid-1",
                guid="rss-guid-1",
                title="Duplicate",
                description=None,
                release_date=None,
                duration_seconds=None,
                episode_url=None,
                audio_url=None,
                external_ids={"rss_guid": "rss-guid-1"},
                evidence={"provider": "rss"},
                source_payload={"id": "rss-guid-1-duplicate"},
            ),
        ],
        etag='"fresh"',
        last_modified="Thu, 02 May 2024 00:00:00 GMT",
        not_modified=False,
    )
    monkeypatch.setattr(mod, "fetch_rss_episodes", lambda _podcast: fetched)

    summary = mod.sync_podcast_episodes_from_rss(conn, _podcast(), dry_run=False)

    assert summary.episodes_seen == 2
    assert summary.episodes_inserted == 1
    assert summary.episodes_skipped == 1
    assert len(conn.upserts) == 1
    upsert_sql = conn.executed[0][0]
    assert "ON CONFLICT (source, source_episode_id) DO UPDATE" in upsert_sql
    upsert_params = conn.upserts[0]
    assert upsert_params[0:5] == (42, "itunes", "rss-guid-1", "rss-guid-1", "Stored")
    assert json.loads(upsert_params[10]) == {"rss_guid": "rss-guid-1"}
    assert conn.podcast_updates
    assert json.loads(conn.podcast_updates[0][0])["rss_episode_reader"]["etag"] == '"fresh"'
