from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import backfill_podcast_episodes as mod  # noqa: E402


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
        if normalized.startswith("SELECT DISTINCT"):
            rows = self._conn.feed_rows
            if params and params[1] is not None:
                wanted_feed_ids = {str(v) for v in params[1]}
                rows = [row for row in rows if row[1] in wanted_feed_ids]
            if params and params[3] is not None:
                wanted_comedian_ids = {int(v) for v in params[3]}
                rows = [row for row in rows if row[4] in wanted_comedian_ids]
            if params and params[5] is not None:
                wanted_names = {str(v) for v in params[5]}
                rows = [row for row in rows if row[5] in wanted_names]
            if params and len(params) > 7 and params[7] is not None:
                rows = rows[: int(params[7])]
            self._last_result = rows
        elif normalized.startswith("SELECT id FROM podcast_episodes") and "WHERE source = %s" in normalized:
            source, source_episode_id = params
            self._last_result = [
                (row["id"],)
                for row in self._conn.existing_episode_rows
                if (row["source"], row["source_episode_id"]) == (source, source_episode_id)
            ][:1]
        elif normalized.startswith("SELECT id FROM podcast_episodes"):
            podcast_id, release_date, source, source_episode_id = params
            self._last_result = [
                (row["id"],)
                for row in self._conn.existing_episode_rows
                if row["podcast_id"] == podcast_id
                and row["release_date"] == release_date
                and (row["source"], row["source_episode_id"]) != (source, source_episode_id)
            ][:1]
        elif normalized.startswith("SELECT id, title FROM podcast_episodes"):
            podcast_id, source, source_episode_id = params
            self._last_result = [
                (row["id"], row["title"])
                for row in self._conn.existing_episode_rows
                if row["podcast_id"] == podcast_id
                and row["release_date"] is None
                and (row["source"], row["source_episode_id"]) != (source, source_episode_id)
            ]
        elif "INSERT INTO podcast_episodes" in normalized:
            self._conn.upserts.append(params)
            new_id = 1000 + len(self._conn.upserts)
            self._last_result = [(new_id, len(self._conn.upserts) % 2 == 1, True)]
        else:
            self._last_result = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last_result

    def fetchone(self) -> Any:
        return self._last_result[0] if self._last_result else None


class _FakeConn:
    def __init__(
        self,
        feed_rows: list[tuple[Any, ...]] | None = None,
        existing_episode_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self.feed_rows = feed_rows or []
        self.existing_episode_rows = existing_episode_rows or []
        self.executed: list[tuple[str, Any]] = []
        self.upserts: list[Any] = []
        self.commits = 0
        self.rollbacks = 0
        self.autocommit_args: list[bool] = []

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


def test_load_accepted_feeds_reads_only_accepted_comedian_podcast_relationships(monkeypatch):
    conn = _FakeConn(
        [
            (
                42,
                "1001",
                "https://feeds.example.com/show.xml",
                "Comedy Talk",
                12,
                "Taylor Comic",
                "host",
            )
        ]
    )
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    rows = mod.load_accepted_feeds(
        feed_ids=["1001"],
        comedian_ids=[12],
        comedian_names=["Taylor Comic"],
        limit=5,
    )

    query, params = conn.executed[0]
    assert "FROM comedian_podcasts cp" in query
    assert "JOIN podcasts p ON p.id = cp.podcast_id" in query
    assert "cp.review_status = 'accepted'" in query
    assert "p.source = %s" in query
    assert params == (
        mod._SOURCE,
        ["1001"],
        ["1001"],
        [12],
        [12],
        ["Taylor Comic"],
        ["Taylor Comic"],
        5,
    )
    assert rows == [
        mod.AcceptedPodcastFeed(
            podcast_id=42,
            source_podcast_id="1001",
            feed_url="https://feeds.example.com/show.xml",
            title="Comedy Talk",
            comedian_ids=[12],
            comedian_names=["Taylor Comic"],
            association_types=["host"],
        )
    ]


def test_episode_from_payload_preserves_stable_ids_and_matching_metadata():
    episode = mod.episode_from_payload(
        podcast_id=42,
        source_podcast_id="1001",
        episode={
            "id": 987,
            "guid": "rss-guid-1",
            "title": "Taylor Comic Returns",
            "description": "A long interview",
            "datePublished": 1714550400,
            "duration": 3661,
            "link": "https://podcast.example/episodes/987",
            "enclosureUrl": "https://cdn.example/audio.mp3",
            "feedId": 1001,
            "feedTitle": "Comedy Talk",
        },
    )

    assert episode is not None
    assert episode.source_episode_id == "987"
    assert episode.guid == "rss-guid-1"
    assert episode.release_date == "2024-05-01T08:00:00+00:00"
    assert episode.duration_seconds == 3661
    assert episode.episode_url == "https://podcast.example/episodes/987"
    assert episode.audio_url == "https://cdn.example/audio.mp3"
    assert episode.external_ids == {
        "podcast_index_episode_id": 987,
        "podcast_index_feed_id": 1001,
        "rss_guid": "rss-guid-1",
    }
    assert episode.evidence["source_podcast_id"] == "1001"
    assert episode.source_payload["feedTitle"] == "Comedy Talk"


def test_backfill_dry_run_fetches_but_does_not_write(monkeypatch):
    conn = _FakeConn(
        [
            (
                42,
                "1001",
                "https://feeds.example.com/show.xml",
                "Comedy Talk",
                12,
                "Taylor Comic",
                "host",
            )
        ]
    )
    fetched_params: list[tuple[str, dict[str, Any]]] = []

    def fake_fetch(
        feed: mod.AcceptedPodcastFeed,
        credentials: mod.PodcastIndexCredentials,
        params: dict[str, Any],
    ):
        fetched_params.append((feed.source_podcast_id, params))
        return [
            {
                "id": 987,
                "guid": "rss-guid-1",
                "title": "Taylor Comic Returns",
                "datePublished": 1714550400,
                "link": "https://podcast.example/episodes/987",
            }
        ]

    monkeypatch.setattr(mod, "get_connection", lambda: conn)
    monkeypatch.setattr(
        mod,
        "_load_podcast_index_credentials",
        lambda: mod.PodcastIndexCredentials("key", "secret", "ua"),
    )
    monkeypatch.setattr(mod, "fetch_feed_episodes", fake_fetch)

    summary = mod.backfill_podcast_episodes(
        dry_run=True,
        confirm=False,
        feed_ids=None,
        comedian_ids=None,
        comedian_names=None,
        limit=1,
        max_episodes_per_feed=25,
        since="2024-01-01",
        until="2024-12-31",
    )

    assert fetched_params == [
        ("1001", {"id": "1001", "max": 25, "fulltext": "", "since": 1704067200})
    ]
    assert summary.feeds_scanned == 1
    assert summary.episodes_inserted == 0
    assert summary.episodes_updated == 0
    assert summary.episodes_skipped == 0
    assert conn.upserts == []
    assert conn.commits == 0


def test_backfill_confirm_upserts_rows_and_reports_insert_update_skip(monkeypatch):
    conn = _FakeConn([(42, "1001", None, "Comedy Talk", 12, "Taylor Comic", "host")])

    def fake_fetch(
        feed: mod.AcceptedPodcastFeed,
        credentials: mod.PodcastIndexCredentials,
        params: dict[str, Any],
    ):
        return [
            {
                "id": 987,
                "title": "Stored",
                "datePublished": 1714550400,
                "link": "https://podcast.example/987",
            },
            {
                "guid": "rss-guid-2",
                "title": "Updated",
                "datePublished": 1714464000,
                "link": "https://podcast.example/guid",
            },
            {"title": "Missing stable identifiers"},
        ]

    def fake_get_connection(autocommit: bool = True):
        conn.autocommit_args.append(autocommit)
        return conn

    monkeypatch.setattr(mod, "get_connection", fake_get_connection)
    monkeypatch.setattr(
        mod,
        "_load_podcast_index_credentials",
        lambda: mod.PodcastIndexCredentials("key", "secret", "ua"),
    )
    monkeypatch.setattr(mod, "fetch_feed_episodes", fake_fetch)

    summary = mod.backfill_podcast_episodes(
        dry_run=False,
        confirm=True,
        feed_ids=None,
        comedian_ids=None,
        comedian_names=None,
        limit=None,
        max_episodes_per_feed=100,
        since=None,
        until=None,
    )

    assert summary.feeds_scanned == 1
    assert summary.episodes_inserted == 1
    assert summary.episodes_updated == 1
    assert summary.episodes_skipped == 1
    assert summary.api_failures == 0
    assert conn.commits == 1
    assert conn.autocommit_args == [True, False]
    assert len(conn.upserts) == 2
    insert_params = conn.upserts[0]
    assert insert_params[0:5] == (42, mod._SOURCE, "987", None, "Stored")
    assert json.loads(insert_params[10])["podcast_index_episode_id"] == 987
    assert json.loads(insert_params[11])["source_podcast_id"] == "1001"
    assert json.loads(insert_params[12])["id"] == 987


def test_upsert_short_circuits_when_logical_duplicate_already_exists():
    """The backfill upsert path must collapse logical duplicates the same way
    rss_episode_reader does — same (podcast_id, release_date) under a different
    (source, source_episode_id) returns the existing id with no INSERT.

    Guards against future divergence between the two write paths now that they
    share find_logical_episode_id but each owns its own upsert wrapper.
    """
    conn = _FakeConn(
        existing_episode_rows=[
            {
                "id": 4242,
                "podcast_id": 42,
                "release_date": "2099-05-01T12:00:00+00:00",
                "source": "rss_itunes",
                "source_episode_id": "canonical-guid",
                "title": "Foo",
            }
        ]
    )
    episode = mod.PodcastEpisodeRow(
        podcast_id=42,
        source=mod._SOURCE,
        source_episode_id="podcastindex-987",
        guid="podcastindex-987",
        title="Foo",
        description=None,
        release_date="2099-05-01T12:00:00+00:00",
        duration_seconds=None,
        episode_url=None,
        audio_url=None,
        external_ids={},
        evidence={},
        source_payload={},
    )

    result = mod.upsert_episode_with_result(conn, episode)

    assert result.episode_id == 4242
    assert result.inserted is False
    assert result.changed is False
    assert conn.upserts == []
    assert any("SELECT id FROM podcast_episodes" in sql for sql, _ in conn.executed)


def test_upsert_falls_through_to_insert_when_no_logical_duplicate():
    """Sanity check: with no pre-existing row, the upsert path still runs INSERT."""
    conn = _FakeConn()
    episode = mod.PodcastEpisodeRow(
        podcast_id=42,
        source=mod._SOURCE,
        source_episode_id="podcastindex-987",
        guid="podcastindex-987",
        title="Foo",
        description=None,
        release_date="2099-05-01T12:00:00+00:00",
        duration_seconds=None,
        episode_url=None,
        audio_url=None,
        external_ids={},
        evidence={},
        source_payload={},
    )

    result = mod.upsert_episode_with_result(conn, episode)

    assert result.inserted is True
    assert len(conn.upserts) == 1


def test_cli_requires_dry_run_or_confirm_and_passes_filters(monkeypatch, capsys):
    calls: list[dict[str, Any]] = []

    def fake_backfill(**kwargs):
        calls.append(kwargs)
        return mod.BackfillSummary(feeds_scanned=1, episodes_inserted=2, episodes_updated=3)

    monkeypatch.setattr(mod, "backfill_podcast_episodes", fake_backfill)

    with pytest.raises(SystemExit) as exc:
        mod.main(["--feed-id", "42", "--comedian-id", "12", "--comedian-name", "Taylor Comic"])
    assert exc.value.code == 2
    assert "choose exactly one" in capsys.readouterr().err

    assert (
        mod.main(
            [
                "--dry-run",
                "--feed-id",
                "1001",
                "--comedian-id",
                "12",
                "--comedian-name",
                "Taylor Comic",
                "--limit",
                "5",
                "--max-episodes-per-feed",
                "25",
                "--since",
                "2024-01-01",
                "--until",
                "2024-12-31",
            ]
        )
        == 0
    )
    assert calls == [
        {
            "dry_run": True,
            "confirm": False,
            "feed_ids": ["1001"],
            "comedian_ids": [12],
            "comedian_names": ["Taylor Comic"],
            "limit": 5,
            "max_episodes_per_feed": 25,
            "since": "2024-01-01",
            "until": "2024-12-31",
        }
    ]
    assert "DRY RUN" in capsys.readouterr().out
