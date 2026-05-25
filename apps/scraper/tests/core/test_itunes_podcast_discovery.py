from __future__ import annotations

import json
from typing import Any

from laughtrack.core import itunes_podcast_discovery as mod


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: dict[str, Any] | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content or b""
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


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
        if normalized.startswith("SELECT id, external_ids FROM podcasts"):
            self._last = self.conn.feed_matches
        elif normalized.startswith("INSERT INTO podcasts"):
            self.conn.podcast_upserts.append(params)
            self._last = [(self.conn.next_podcast_id,)]
        elif normalized.startswith("UPDATE podcasts"):
            self.conn.podcast_updates.append(params)
            self._last = [(self.conn.existing_podcast_id,)]
        elif normalized.startswith("INSERT INTO podcast_candidate_reviews"):
            self.conn.review_upserts.append(params)
            self._last = []
        else:
            self._last = []

    def fetchone(self) -> Any:
        return self._last[0] if self._last else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last


class _FakeConn:
    def __init__(self, feed_matches: list[tuple[Any, ...]] | None = None) -> None:
        self.feed_matches = feed_matches or []
        self.existing_podcast_id = 77
        self.next_podcast_id = 42
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []
        self.podcast_upserts: list[tuple[Any, ...] | None] = []
        self.podcast_updates: list[tuple[Any, ...] | None] = []
        self.review_upserts: list[tuple[Any, ...] | None] = []

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)


def _candidate(**overrides: Any) -> mod.ItunesPodcastCandidate:
    values = {
        "comedian_id": 12,
        "source_podcast_id": "12345",
        "matched_name": "Taylor Comic",
        "normalized_match": "taylor comic",
        "confidence": 0.99,
        "title": "Taylor Comic Podcast",
        "author_name": "Taylor Comic",
        "feed_url": "https://feeds.example.com/taylor.xml",
        "website_url": "https://podcasts.apple.com/us/podcast/taylor/id12345",
        "image_url": "https://example.com/art.jpg",
        "description": "Comedy interviews",
        "evidence": {"confidence_band": "title_exact", "source_fields": {"collectionId": 12345}},
    }
    values.update(overrides)
    return mod.ItunesPodcastCandidate(**values)


def test_search_podcasts_uses_itunes_podcast_search_shape() -> None:
    session = _FakeSession(
        [
            _FakeResponse(
                payload={
                    "resultCount": 1,
                    "results": [{"collectionId": 12345, "collectionName": "Taylor Comic Podcast"}],
                }
            )
        ]
    )

    results = mod.search_itunes_podcasts(
        "Taylor Comic",
        limit=7,
        country="US",
        session=session,
        sleep=lambda _seconds: None,
    )

    assert results == [{"collectionId": 12345, "collectionName": "Taylor Comic Podcast"}]
    assert session.calls == [
        {
            "url": mod._ITUNES_SEARCH_URL,
            "params": {"media": "podcast", "entity": "podcast", "term": "Taylor Comic", "limit": 7, "country": "US"},
            "timeout": mod._TIMEOUT_SECONDS,
        }
    ]


def test_search_podcasts_can_scope_to_attribute() -> None:
    session = _FakeSession([_FakeResponse(payload={"results": []})])

    mod.search_itunes_podcasts(
        "Taylor Comic",
        attribute="authorTerm",
        session=session,
        sleep=lambda _seconds: None,
    )

    assert session.calls[0]["params"]["attribute"] == "authorTerm"


def test_lookup_podcast_uses_collection_id() -> None:
    session = _FakeSession(
        [
            _FakeResponse(
                payload={
                    "resultCount": 1,
                    "results": [{"collectionId": 12345, "collectionName": "Taylor Comic Podcast"}],
                }
            )
        ]
    )

    result = mod.lookup_itunes_podcast("12345", session=session, sleep=lambda _seconds: None)

    assert result == {"collectionId": 12345, "collectionName": "Taylor Comic Podcast"}
    assert session.calls[0]["url"] == mod._ITUNES_LOOKUP_URL
    assert session.calls[0]["params"] == {"id": "12345", "entity": "podcast"}


def test_search_retries_rate_limits_using_retry_after() -> None:
    sleeps: list[float] = []
    session = _FakeSession(
        [
            _FakeResponse(status_code=429, headers={"Retry-After": "1.5"}),
            _FakeResponse(payload={"results": []}),
        ]
    )

    results = mod.search_itunes_podcasts(
        "Taylor Comic",
        session=session,
        sleep=sleeps.append,
    )

    assert results == []
    assert sleeps == [1.5]
    assert len(session.calls) == 2


def test_candidate_from_result_normalizes_itunes_payload() -> None:
    comedian = mod.PodcastDiscoveryComedian(12, "Taylor Comic", ["Taylor C"])

    candidate = mod.candidate_from_itunes_result(
        comedian,
        {
            "collectionId": 12345,
            "collectionName": "Taylor Comic Podcast",
            "artistName": "Taylor Comic",
            "feedUrl": "https://feeds.example.com/taylor.xml",
            "collectionViewUrl": "https://podcasts.apple.com/us/podcast/taylor/id12345",
            "artworkUrl600": "https://example.com/art.jpg",
            "description": "A comedy interview podcast",
            "primaryGenreName": "Comedy",
        },
        search_term="Taylor Comic",
        rank=1,
    )

    assert candidate is not None
    assert candidate.source == mod._SOURCE
    assert candidate.source_podcast_id == "12345"
    assert candidate.title == "Taylor Comic Podcast"
    assert candidate.author_name == "Taylor Comic"
    assert candidate.feed_url == "https://feeds.example.com/taylor.xml"
    assert candidate.website_url == "https://podcasts.apple.com/us/podcast/taylor/id12345"
    assert candidate.image_url == "https://example.com/art.jpg"
    assert candidate.confidence == 0.99
    assert candidate.evidence["confidence_band"] == "title_exact"
    assert candidate.evidence["source_fields"]["collection_id"] == 12345


def test_owner_style_feed_description_scores_above_threshold() -> None:
    comedian = mod.PodcastDiscoveryComedian(223960, "Jess Hilarious", [])

    candidate = mod.candidate_from_itunes_result(
        comedian,
        {
            "collectionId": 1539709257,
            "collectionName": "Carefully Reckless",
            "artistName": "The Black Effect Podcast Network and iHeartPodcasts",
            "feedUrl": "https://feeds.example.com/carefully-reckless.xml",
            "description": (
                "Comedian and Actress Jessica Jess Hilarious Moore is now taking her no hold bar "
                "topics to The Black Effect Network introducing Carefully Reckless."
            ),
        },
        search_term="Jess Hilarious",
        rank=1,
    )

    assert candidate is not None
    assert candidate.confidence == 0.84
    assert candidate.evidence["confidence_band"] == "owner_description_contains"
    assert candidate.evidence["match_field"] == "description"


def test_discovery_enriches_missing_description_from_rss_feed() -> None:
    comedian = mod.PodcastDiscoveryComedian(223960, "Jess Hilarious", [])
    rss = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Carefully Reckless</title>
<description>Comedian and Actress Jessica Jess Hilarious Moore is now taking her topics to The Black Effect Network introducing Carefully Reckless.</description>
</channel></rss>"""
    session = _FakeSession(
        [
            _FakeResponse(
                payload={
                    "results": [
                        {
                            "collectionId": 1539709257,
                            "collectionName": "Carefully Reckless",
                            "artistName": "The Black Effect Podcast Network and iHeartPodcasts",
                            "feedUrl": "https://feeds.example.com/carefully-reckless.xml",
                        }
                    ]
                }
            ),
            _FakeResponse(content=rss),
        ]
    )

    candidates, failures = mod.discover_candidates_for_comedian(
        comedian,
        max_results=5,
        country="US",
        request_delay=0,
        session=session,
        sleep=lambda _seconds: None,
    )

    assert failures == []
    assert len(candidates) == 1
    assert candidates[0].confidence == 0.84
    assert candidates[0].description is not None
    assert candidates[0].evidence["source_fields"]["rss_description_enriched"] is True
    assert [call["url"] for call in session.calls] == [
        mod._ITUNES_SEARCH_URL,
        "https://feeds.example.com/carefully-reckless.xml",
    ]


def test_upsert_candidate_merges_itunes_id_into_existing_feed_url_match() -> None:
    conn = _FakeConn(feed_matches=[(77, {"podcast_index_feed_id": 998})])

    result = mod.upsert_candidate_with_conn(conn, _candidate())

    assert result.podcast_id == 77
    assert result.action == "merged_feed_url"
    assert conn.podcast_upserts == []
    assert len(conn.podcast_updates) == 1
    update_params = conn.podcast_updates[0]
    assert update_params is not None
    merged_external_ids = json.loads(update_params[0])
    assert merged_external_ids == {
        "itunes_collection_id": "12345",
        "podcast_index_feed_id": 998,
    }
    assert len(conn.review_upserts) == 1
    assert conn.review_upserts[0][:6] == (12, 77, mod._SOURCE, "12345", "pending", "host")


def test_upsert_candidate_inserts_when_no_feed_url_match() -> None:
    conn = _FakeConn(feed_matches=[])

    result = mod.upsert_candidate_with_conn(conn, _candidate())

    assert result.podcast_id == 42
    assert result.action == "upserted_source"
    assert len(conn.podcast_upserts) == 1
    podcast_params = conn.podcast_upserts[0]
    assert podcast_params is not None
    assert podcast_params[:5] == (
        mod._SOURCE,
        "12345",
        "taylor-comic-podcast-itunes-12345",
        "https://feeds.example.com/taylor.xml",
        "Taylor Comic Podcast",
    )
    assert json.loads(podcast_params[9]) == {"itunes_collection_id": "12345"}
    assert len(conn.review_upserts) == 1
