from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from laughtrack.core import rss_episode_reader as reader  # noqa: E402
from scripts.core import backfill_ymh_episode_dates_from_wayback as wayback_mod  # noqa: E402
from scripts.core import sync_podcast_episodes_from_rss as sync_mod  # noqa: E402


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
        elif normalized.startswith("SELECT id FROM podcast_episodes") and "WHERE source = %s" in normalized:
            source, source_episode_id = params
            self._last_result = [
                (row["id"],)
                for row in self.conn.episode_rows
                if (row["source"], row["source_episode_id"]) == (source, source_episode_id)
            ][:1]
        elif normalized.startswith("SELECT id, title FROM podcast_episodes"):
            podcast_id, release_date, title, source, source_episode_id = params
            self._last_result = [
                (row["id"], row["title"])
                for row in self.conn.episode_rows
                if row["podcast_id"] == podcast_id
                and row["release_date"] == release_date
                and reader._normalize_title(row["title"]) == reader._normalize_title(title)
                and (row["source"], row["source_episode_id"]) != (source, source_episode_id)
            ]
        elif "INSERT INTO podcast_episodes" in normalized:
            self.conn.upserts.append(params)
            source, source_episode_id = params[1], params[2]
            existing = next(
                (
                    row
                    for row in self.conn.episode_rows
                    if (row["source"], row["source_episode_id"]) == (source, source_episode_id)
                ),
                None,
            )
            if existing is not None:
                existing.update(
                    {
                        "title": params[4],
                        "release_date": params[6],
                        "audio_url": params[9],
                    }
                )
                self._last_result = [(existing["id"], False, True)]
            else:
                new_id = 1000 + len(self.conn.episode_rows)
                self.conn.episode_rows.append(
                    {
                        "id": new_id,
                        "podcast_id": params[0],
                        "source": source,
                        "source_episode_id": source_episode_id,
                        "title": params[4],
                        "release_date": params[6],
                        "audio_url": params[9],
                    }
                )
                self._last_result = [(new_id, True, True)]
        elif normalized.startswith("UPDATE podcasts"):
            self.conn.podcast_updates.append(params)
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
            (
                5407,
                "podcast_index",
                "2560005",
                "https://feeds.feedburner.com/YourMomsHouseWithChristinaPazsitzkyAndTomSegura",
                "Your Mom's House with Christina P. and Tom Segura",
                {
                    "feed_url": "https://feeds.feedburner.com/YourMomsHouseWithChristinaPazsitzkyAndTomSegura",
                },
            )
        ]
        self.episode_rows = [
            {
                "id": 360277,
                "podcast_id": 5407,
                "source": "podcast_index",
                "source_episode_id": "ymh-104",
                "title": "104-Your Mom's House with Christina Pazsitzky and Tom Segura",
                "release_date": "2016-10-17T00:00:00+00:00",
                "audio_url": "https://cdn.example/YMH104.mp3",
            },
            {
                "id": 360270,
                "podcast_id": 5407,
                "source": "podcast_index",
                "source_episode_id": "ymh-106",
                "title": "106 - Your Mom's House with Christina Pazsitzky and Tom Segura",
                "release_date": "2016-10-17T00:00:00+00:00",
                "audio_url": "https://cdn.example/YMH106.mp3",
            },
        ]
        self.executed: list[tuple[str, Any]] = []
        self.upserts: list[Any] = []
        self.podcast_updates: list[Any] = []

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)


def _ymh_episode(source_episode_id: str, title: str, release_date: str, audio_url: str) -> reader.RssEpisodeRow:
    return reader.RssEpisodeRow(
        podcast_id=5407,
        source="podcast_index",
        source_episode_id=source_episode_id,
        guid=source_episode_id,
        title=title,
        description=None,
        release_date=release_date,
        duration_seconds=None,
        episode_url="https://ymhstudios.com",
        audio_url=audio_url,
        external_ids={"rss_guid": source_episode_id},
        evidence={"provider": "rss"},
        source_payload={"id": source_episode_id},
    )


def test_loader_uses_source_payload_feed_url_for_ymh_when_column_is_null():
    conn = _FakeConn()
    conn.podcast_rows[0] = (
        5407,
        "podcast_index",
        "2560005",
        "https://feeds.feedburner.com/YourMomsHouseWithChristinaPazsitzkyAndTomSegura",
        "Your Mom's House with Christina P. and Tom Segura",
        {
            "feed_url": "https://feeds.feedburner.com/YourMomsHouseWithChristinaPazsitzkyAndTomSegura",
        },
    )

    podcasts = sync_mod.load_podcasts(conn, source="podcast_index", podcast_ids=[5407], limit=None)

    assert podcasts == [
        reader.PodcastRssFeed(
            podcast_id=5407,
            source="podcast_index",
            source_podcast_id="2560005",
            feed_url="https://feeds.feedburner.com/YourMomsHouseWithChristinaPazsitzkyAndTomSegura",
            title="Your Mom's House with Christina P. and Tom Segura",
            source_payload={
                "feed_url": "https://feeds.feedburner.com/YourMomsHouseWithChristinaPazsitzkyAndTomSegura",
            },
        )
    ]
    select_sql = conn.executed[0][0]
    assert "COALESCE(feed_url, source_payload ->> 'feed_url')" in select_sql


def test_ymh_bad_date_rows_update_from_rss_without_collapsing_distinct_numbered_episodes():
    conn = _FakeConn()
    podcast = reader.PodcastRssFeed(
        podcast_id=5407,
        source="podcast_index",
        source_podcast_id="2560005",
        feed_url="https://feeds.feedburner.com/YourMomsHouseWithChristinaPazsitzkyAndTomSegura",
        title="Your Mom's House with Christina P. and Tom Segura",
        source_payload={},
    )
    fetched = reader.RssFetchResult(
        episodes=[
            _ymh_episode(
                "ymh-104",
                "104-Your Mom's House with Christina Pazsitzky and Tom Segura",
                "2013-02-20T20:02:00+00:00",
                "https://cdn.example/YMH104.mp3",
            ),
            _ymh_episode(
                "ymh-106",
                "106 - Your Mom's House with Christina Pazsitzky and Tom Segura",
                "2013-03-01T06:36:00+00:00",
                "https://cdn.example/YMH106.mp3",
            ),
        ]
    )

    summary = reader.persist_rss_fetch_result(conn, podcast, fetched, dry_run=False)

    assert summary.episodes_updated == 2
    assert len(conn.episode_rows) == 2
    assert {row["source_episode_id"] for row in conn.episode_rows} == {"ymh-104", "ymh-106"}
    assert {row["release_date"] for row in conn.episode_rows} == {
        "2013-02-20T20:02:00+00:00",
        "2013-03-01T06:36:00+00:00",
    }


def test_wayback_parser_recovers_historical_pubdates_for_affected_numbered_titles():
    archived_feed = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel>
      <item>
        <title>104-Your Mom's House with Christina Pazsitzky and Tom Segura</title>
        <pubDate>Wed, 20 Feb 2013 20:02:00 +0000</pubDate>
        <guid isPermaLink="false">ymh-104</guid>
      </item>
      <item>
        <title>106 - Your Mom's House with Christina Pazsitzky and Tom Segura</title>
        <pubDate>Fri, 01 Mar 2013 06:36:00 +0000</pubDate>
        <guid isPermaLink="false">ymh-106</guid>
      </item>
      <item>
        <title>104-Some Other Podcast</title>
        <pubDate>Fri, 01 Mar 2013 06:36:00 +0000</pubDate>
      </item>
    </channel></rss>
    """

    dates = wayback_mod._archive_dates_from_feed(archived_feed, "20130903202201", {104, 106})

    assert dates == {
        104: wayback_mod.ArchivedEpisodeDate(
            episode_number=104,
            title="104-Your Mom's House with Christina Pazsitzky and Tom Segura",
            release_date="2013-02-20T20:02:00+00:00",
            snapshot_timestamp="20130903202201",
        ),
        106: wayback_mod.ArchivedEpisodeDate(
            episode_number=106,
            title="106 - Your Mom's House with Christina Pazsitzky and Tom Segura",
            release_date="2013-03-01T06:36:00+00:00",
            snapshot_timestamp="20130903202201",
        ),
    }
