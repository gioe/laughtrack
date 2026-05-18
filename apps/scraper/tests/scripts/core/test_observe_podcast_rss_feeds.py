from __future__ import annotations

from typing import Any

from scripts.core import backfill_podcast_episodes as episode_mod
from scripts.core import observe_podcast_rss_feeds as mod


def _feed() -> episode_mod.AcceptedPodcastFeed:
    return episode_mod.AcceptedPodcastFeed(
        podcast_id=42,
        source_podcast_id="1001",
        feed_url="https://feeds.example.com/show.xml",
        title="Comedy Talk",
        comedian_ids=[12],
        comedian_names=["Taylor Comic"],
        association_types=["host"],
    )


def test_observer_dry_run_fetches_accepted_feeds_without_writing(monkeypatch):
    calls: dict[str, Any] = {}
    conn = object()

    class _ConnContext:
        def __enter__(self) -> object:
            return conn

        def __exit__(self, *_exc: Any) -> bool:
            return False

    monkeypatch.setattr(mod.episode_mod, "_load_podcast_index_credentials", lambda: object())

    def fake_load_feeds(**kwargs: Any) -> list[episode_mod.AcceptedPodcastFeed]:
        calls["load_feeds"] = kwargs
        return [_feed()]

    monkeypatch.setattr(mod.episode_mod, "load_accepted_feeds", fake_load_feeds)
    monkeypatch.setattr(mod, "get_connection", lambda autocommit=False: _ConnContext())
    monkeypatch.setattr(mod, "_load_latest_release_date", lambda _conn, podcast_id: "2024-05-01T00:00:00+00:00")

    def fake_fetch(feed: Any, credentials: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
        calls["fetch_params"] = params
        return [{"id": 987, "title": "Taylor Comic Returns"}]

    monkeypatch.setattr(mod.episode_mod, "fetch_feed_episodes", fake_fetch)

    def fail_upsert(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("dry-run must not upsert podcast_episodes")

    monkeypatch.setattr(mod.episode_mod, "upsert_episode_with_result", fail_upsert)
    monkeypatch.setattr(mod, "_detect_new_episode_appearances", fail_upsert)

    summary = mod.observe_podcast_rss_feeds(
        dry_run=True,
        feed_ids=["1001"],
        comedian_ids=[12],
        comedian_names=["Taylor Comic"],
        limit=1,
        max_episodes_per_feed=25,
        include_aliases=True,
    )

    assert calls["load_feeds"] == {
        "feed_ids": ["1001"],
        "comedian_ids": [12],
        "comedian_names": ["Taylor Comic"],
        "limit": 1,
    }
    assert calls["fetch_params"] == {
        "id": "1001",
        "max": 25,
        "fulltext": "",
        "since": 1714521600,
    }
    assert summary.feeds_scanned == 1
    assert summary.episodes_seen == 1
    assert summary.episodes_changed == 0
    assert summary.detector_episode_ids == []


def test_observer_upserts_only_changed_episodes_and_scopes_detector(monkeypatch):
    conn = object()
    detector_calls: list[tuple[list[int], bool]] = []

    class _ConnContext:
        def __enter__(self) -> object:
            return conn

        def __exit__(self, *_exc: Any) -> bool:
            return False

    monkeypatch.setattr(mod, "get_connection", lambda autocommit=False: _ConnContext())
    monkeypatch.setattr(mod.episode_mod, "_load_podcast_index_credentials", lambda: object())
    monkeypatch.setattr(mod.episode_mod, "load_accepted_feeds", lambda **_kwargs: [_feed()])
    monkeypatch.setattr(mod, "_load_latest_release_date", lambda _conn, _podcast_id: None)
    monkeypatch.setattr(
        mod.episode_mod,
        "fetch_feed_episodes",
        lambda _feed, _credentials, _params: [
            {"id": 987, "title": "New episode"},
            {"id": 988, "title": "Changed episode"},
            {"id": 989, "title": "Unchanged episode"},
        ],
    )

    upsert_results = iter(
        [
            episode_mod.EpisodeUpsertResult(episode_id=101, inserted=True, changed=True),
            episode_mod.EpisodeUpsertResult(episode_id=102, inserted=False, changed=True),
            episode_mod.EpisodeUpsertResult(episode_id=103, inserted=False, changed=False),
        ]
    )
    monkeypatch.setattr(
        mod.episode_mod,
        "upsert_episode_with_result",
        lambda _conn, _episode: next(upsert_results),
    )

    def fake_detect(target_conn: Any, episode_ids: list[int], include_aliases: bool) -> mod.detect_mod.DetectSummary:
        assert target_conn is conn
        detector_calls.append((episode_ids, include_aliases))
        return mod.detect_mod.DetectSummary(candidates=3, auto_accepted=2, pending=1, written=3)

    monkeypatch.setattr(mod, "_detect_new_episode_appearances", fake_detect)

    summary = mod.observe_podcast_rss_feeds(
        dry_run=False,
        feed_ids=None,
        comedian_ids=None,
        comedian_names=None,
        limit=None,
        max_episodes_per_feed=100,
        include_aliases=False,
    )

    assert detector_calls == [([101, 102], False)]
    assert summary.episodes_inserted == 1
    assert summary.episodes_updated == 1
    assert summary.episodes_unchanged == 1
    assert summary.detector_episode_ids == [101, 102]
    assert summary.detection_candidates == 3
    assert summary.detection_auto_accepted == 2
    assert summary.detection_pending == 1
