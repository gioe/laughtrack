from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import discover_comedian_podcast_candidates as mod  # noqa: E402


class _FakeCursor:
    def __init__(
        self,
        rows: list[Any] | None = None,
        *,
        fetchall_results: list[list[Any]] | None = None,
        fetchone_results: list[Any] | None = None,
    ):
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []
        if rows is not None and fetchall_results is None and fetchone_results is None:
            self._fetchall_queue: list[list[Any]] = [list(rows)]
            self._fetchone_queue: list[Any] = [rows[0] if rows else None]
        else:
            self._fetchall_queue = (
                [list(rs) for rs in fetchall_results] if fetchall_results else []
            )
            self._fetchone_queue = list(fetchone_results) if fetchone_results else []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[Any]:
        if self._fetchall_queue:
            return self._fetchall_queue.pop(0)
        return []

    def fetchone(self) -> Any:
        if self._fetchone_queue:
            return self._fetchone_queue.pop(0)
        return None


class _FakeConnection:
    def __init__(
        self,
        rows: list[Any] | None = None,
        *,
        fetchall_results: list[list[Any]] | None = None,
        fetchone_results: list[Any] | None = None,
    ):
        self.cursor_obj = _FakeCursor(
            rows,
            fetchall_results=fetchall_results,
            fetchone_results=fetchone_results,
        )
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *_args, **_kwargs):
        return self.cursor_obj

    def commit(self) -> None:
        self.commits += 1


def test_discovery_query_uses_canonical_non_denied_comedians_and_alias_inputs():
    query = mod._GET_DISCOVERY_COMEDIANS_SQL

    assert "c.parent_comedian_id IS NULL" in query
    assert "comedian_deny_list" in query
    assert "NOT EXISTS" in query
    assert "LOWER(BTRIM(d.name)) = LOWER(BTRIM(c.name))" in query
    assert "a.parent_comedian_id = c.id" in query
    assert "array_agg" in query


def test_load_target_comedians_returns_aliases_without_alias_seed_rows(monkeypatch):
    conn = _FakeConnection([(12, "Steve-O", ["Steve O", "Steven Glover"])])

    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    rows = mod.load_target_comedians(comedian_ids=[12], comedian_names=None, limit=5)

    query, params = conn.cursor_obj.executed[0]
    assert rows == [mod.PodcastDiscoveryComedian(12, "Steve-O", ["Steve O", "Steven Glover"])]
    assert "c.id = ANY(%s::int[])" in query
    assert "LIMIT %s" in query
    assert params == ([12], 5)


def test_search_terms_include_canonical_name_and_unique_aliases():
    comedian = mod.PodcastDiscoveryComedian(12, "Steve-O", ["Steve O", "Steve-O", "Steven Glover", ""])

    assert mod.build_search_terms(comedian) == ["Steve-O", "Steve O", "Steven Glover"]


def test_normalization_handles_html_entities_unicode_punctuation_and_steve_o_variants():
    assert mod.normalize_match_text("Steve&#45;O's Wild Ride") == "steve o wild ride"
    assert mod.normalize_match_text("Steve-O") == mod.normalize_match_text("Steve O")
    assert mod.normalize_match_text("Marc Maron's WTF") == "marc maron wtf"
    assert mod.normalize_match_text("J.R. De Guzman") == "j r de guzman"
    assert mod.normalize_match_text("John Mulaney's Show") == "john mulaney show"


def test_candidate_scoring_assigns_distinct_debuggable_confidence_bands():
    comedian = mod.PodcastDiscoveryComedian(12, "Steve-O", ["Steve O"])
    cases = [
        ("Steve-O", "Comedy Network", "", "Steve-O", 0.99, "title_exact"),
        ("Wild Ride", "Steve-O", "", "Steve-O", 0.97, "author_exact"),
        ("Steve O Podcast", "Comedy Network", "", "Steve O", 0.94, "alias_title_exact"),
        ("Wild Ride with Steve-O", "Comedy Network", "", "Steve-O", 0.86, "title_contains"),
        ("Comedy Talk", "Steve-O Network", "", "Steve-O", 0.82, "author_contains"),
        ("Comedy Talk", "Comedy Network", "Interviews Steve-O about touring", "Steve-O", 0.48, "description_contains"),
        ("Best Comedy Shows", "Comedy Network", "A roundup of stand-up", "Steve-O", 0.12, "false_positive_pattern"),
    ]

    for title, author, description, matched_name, confidence, band in cases:
        candidate = mod.candidate_from_feed(
            comedian=comedian,
            feed={
                "id": 101,
                "title": title,
                "author": author,
                "description": description,
                "url": "https://feeds.example.com/show.xml",
            },
            search_term=matched_name,
            rank=1,
        )

        assert candidate is not None
        assert candidate.matched_name == matched_name
        assert candidate.confidence == confidence
        assert candidate.evidence["confidence_band"] == band
        assert candidate.evidence["normalized_match"] == mod.normalize_match_text(matched_name)


def test_parse_search_payload_stores_source_fields_and_image_url():
    comedian = mod.PodcastDiscoveryComedian(12, "Steve-O", ["Steve O"])
    payload = {
        "feeds": [
            {
                "id": 101,
                "title": "Steve-O's Wild Ride",
                "author": "Steve-O",
                "url": "https://feeds.example.com/show.xml",
                "link": "https://example.com",
                "image": "https://example.com/image.jpg",
                "description": "Comedy interviews",
            }
        ]
    }

    candidates = mod.parse_search_payload(comedian, "Steve-O", payload)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.source_podcast_id == "101"
    assert candidate.title == "Steve-O's Wild Ride"
    assert candidate.author_name == "Steve-O"
    assert candidate.feed_url == "https://feeds.example.com/show.xml"
    assert candidate.website_url == "https://example.com"
    assert candidate.image_url == "https://example.com/image.jpg"
    assert candidate.evidence["source_fields"]["podcast_index_feed_id"] == 101
    assert candidate.evidence["source_fields"]["feed_url"] == "https://feeds.example.com/show.xml"


def test_persist_candidates_upserts_podcasts_and_candidate_reviews(monkeypatch):
    conn = _FakeConnection(
        fetchall_results=[[]],
        fetchone_results=[(42,)],
    )
    candidate = mod.PodcastCandidate(
        comedian_id=12,
        source=mod._SOURCE,
        source_podcast_id="101",
        matched_name="Steve-O",
        normalized_match="steve o",
        confidence=0.99,
        title="Steve-O's Wild Ride",
        author_name="Steve-O",
        feed_url="https://feeds.example.com/show.xml",
        website_url="https://example.com",
        image_url="https://example.com/image.jpg",
        description="Comedy interviews",
        evidence={"confidence_band": "title_exact", "source_fields": {"podcast_index_feed_id": 101}},
    )

    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    written = mod.persist_candidates([candidate], dry_run=False)

    assert written == 1
    assert conn.commits == 1
    assert len(conn.cursor_obj.executed) == 3
    deny_query, _ = conn.cursor_obj.executed[0]
    podcast_query, podcast_params = conn.cursor_obj.executed[1]
    review_query, review_params = conn.cursor_obj.executed[2]
    assert "FROM podcast_deny_list" in deny_query
    assert "restored_at IS NULL" in deny_query
    assert "INSERT INTO podcasts" in podcast_query
    assert "ON CONFLICT (source, source_podcast_id)" in podcast_query
    assert podcast_params[:7] == (
        mod._SOURCE,
        "101",
        "steve-o-s-wild-ride-podcast-index-101",
        "https://feeds.example.com/show.xml",
        "Steve-O's Wild Ride",
        "Steve-O",
        "https://example.com",
    )
    assert "INSERT INTO podcast_candidate_reviews" in review_query
    assert "ON CONFLICT (comedian_id, source, source_podcast_id)" in review_query
    assert review_params[:6] == (12, 42, mod._SOURCE, "101", "pending", "host")
    evidence = json.loads(review_params[7])
    assert evidence["matched_name"] == "Steve-O"
    assert evidence["normalized_match"] == "steve o"
    assert evidence["confidence_band"] == "title_exact"


def _candidate(
    *,
    comedian_id: int = 12,
    source: str = mod._SOURCE,
    source_podcast_id: str = "101",
    feed_url: str | None = "https://feeds.example.com/show.xml",
) -> Any:
    return mod.PodcastCandidate(
        comedian_id=comedian_id,
        source=source,
        source_podcast_id=source_podcast_id,
        matched_name="Steve-O",
        normalized_match="steve o",
        confidence=0.99,
        title="Steve-O's Wild Ride",
        author_name="Steve-O",
        feed_url=feed_url,
        website_url="https://example.com",
        image_url="https://example.com/image.jpg",
        description="Comedy interviews",
        evidence={"confidence_band": "title_exact", "source_fields": {}},
    )


def test_load_active_deny_list_excludes_restored_entries():
    cursor = _FakeCursor(
        fetchall_results=[
            [
                (mod._SOURCE, "101", None),
                ("manual_rss", "abc123", "https://feeds.example.com/manual.xml"),
                (None, None, "https://feeds.example.com/urlonly.xml"),
            ]
        ]
    )

    deny_keys, deny_urls = mod.load_active_deny_list(cursor)

    query, _ = cursor.executed[0]
    assert "FROM podcast_deny_list" in query
    assert "restored_at IS NULL" in query
    assert deny_keys == {(mod._SOURCE, "101"), ("manual_rss", "abc123")}
    assert deny_urls == {
        "https://feeds.example.com/manual.xml",
        "https://feeds.example.com/urlonly.xml",
    }


def test_candidate_is_denied_matches_source_pair_or_feed_url():
    deny_keys = {(mod._SOURCE, "101")}
    deny_urls = {"https://feeds.example.com/blocked.xml"}

    assert mod.candidate_is_denied(_candidate(source_podcast_id="101"), deny_keys, deny_urls)
    assert mod.candidate_is_denied(
        _candidate(source_podcast_id="999", feed_url="https://feeds.example.com/blocked.xml"),
        deny_keys,
        deny_urls,
    )
    assert not mod.candidate_is_denied(
        _candidate(source_podcast_id="999", feed_url="https://feeds.example.com/allowed.xml"),
        deny_keys,
        deny_urls,
    )
    assert not mod.candidate_is_denied(
        _candidate(source_podcast_id="999", feed_url=None),
        deny_keys,
        deny_urls,
    )


def test_persist_candidates_skips_deny_listed_source_podcast_id(monkeypatch):
    conn = _FakeConnection(
        fetchall_results=[[(mod._SOURCE, "101", None)]],
        fetchone_results=[],
    )
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    written = mod.persist_candidates([_candidate(source_podcast_id="101")], dry_run=False)

    assert written == 0
    assert conn.commits == 1
    queries = [q for q, _ in conn.cursor_obj.executed]
    assert any("FROM podcast_deny_list" in q for q in queries)
    assert not any("INSERT INTO podcasts" in q for q in queries)
    assert not any("INSERT INTO podcast_candidate_reviews" in q for q in queries)


def test_persist_candidates_skips_deny_listed_feed_url(monkeypatch):
    conn = _FakeConnection(
        fetchall_results=[[(None, None, "https://feeds.example.com/show.xml")]],
        fetchone_results=[],
    )
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    written = mod.persist_candidates(
        [_candidate(source_podcast_id="999", feed_url="https://feeds.example.com/show.xml")],
        dry_run=False,
    )

    assert written == 0
    queries = [q for q, _ in conn.cursor_obj.executed]
    assert not any("INSERT INTO podcasts" in q for q in queries)


def test_persist_candidates_writes_allowed_candidate_alongside_denied_one(monkeypatch):
    conn = _FakeConnection(
        fetchall_results=[[(mod._SOURCE, "blocked-101", None)]],
        fetchone_results=[(42,)],
    )
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    written = mod.persist_candidates(
        [
            _candidate(source_podcast_id="blocked-101"),
            _candidate(source_podcast_id="allowed-202", feed_url="https://feeds.example.com/ok.xml"),
        ],
        dry_run=False,
    )

    assert written == 1
    insert_queries = [
        q for q, _ in conn.cursor_obj.executed if "INSERT INTO podcasts" in q
    ]
    assert len(insert_queries) == 1
    review_queries = [
        q for q, _ in conn.cursor_obj.executed if "INSERT INTO podcast_candidate_reviews" in q
    ]
    assert len(review_queries) == 1


def test_persist_candidates_does_not_treat_restored_entries_as_denied(monkeypatch):
    # The deny-list query already filters WHERE restored_at IS NULL — so a restored
    # row never reaches load_active_deny_list. Simulating that here ensures the
    # restore path proceeds with a normal write.
    conn = _FakeConnection(
        fetchall_results=[[]],
        fetchone_results=[(42,)],
    )
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    written = mod.persist_candidates([_candidate(source_podcast_id="101")], dry_run=False)

    assert written == 1
    insert_queries = [
        q for q, _ in conn.cursor_obj.executed if "INSERT INTO podcasts" in q
    ]
    assert len(insert_queries) == 1


def test_persist_candidates_dry_run_does_not_write(monkeypatch):
    conn = _FakeConnection([])
    candidate = mod.PodcastCandidate(
        comedian_id=12,
        source=mod._SOURCE,
        source_podcast_id="101",
        matched_name="Steve-O",
        normalized_match="steve o",
        confidence=0.99,
        title="Steve-O's Wild Ride",
        author_name="Steve-O",
        feed_url="https://feeds.example.com/show.xml",
        website_url="https://example.com",
        image_url="https://example.com/image.jpg",
        description="Comedy interviews",
        evidence={"confidence_band": "title_exact"},
    )

    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    assert mod.persist_candidates([candidate], dry_run=True) == 1
    assert conn.commits == 0
    assert conn.cursor_obj.executed == []


def test_cli_supports_limit_ids_names_dry_run_and_max_results_flags(monkeypatch):
    calls: list[dict[str, Any]] = []

    def fake_discover(**kwargs):
        calls.append(kwargs)
        return {"processed": 0, "candidates": 0, "written": 0, "failed": 0}

    monkeypatch.setattr(mod, "discover_podcast_candidates", fake_discover)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "discover_comedian_podcast_candidates.py",
            "--limit",
            "3",
            "--comedian-ids",
            "12",
            "13",
            "--comedian-names",
            "Steve-O",
            "J.R. De Guzman",
            "--max-results",
            "7",
            "--dry-run",
        ],
    )

    assert mod.main() == 0
    assert calls == [
        {
            "limit": 3,
            "comedian_ids": [12, 13],
            "comedian_names": ["Steve-O", "J.R. De Guzman"],
            "max_results": 7,
            "dry_run": True,
        }
    ]
