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
    def __init__(self, rows: list[Any]):
        self.rows = rows
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[Any]:
        return self.rows

    def fetchone(self) -> Any:
        return self.rows[0] if self.rows else None


class _FakeConnection:
    def __init__(self, rows: list[Any]):
        self.cursor_obj = _FakeCursor(rows)
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
    conn = _FakeConnection([(42,)])
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
    assert len(conn.cursor_obj.executed) == 2
    podcast_query, podcast_params = conn.cursor_obj.executed[0]
    review_query, review_params = conn.cursor_obj.executed[1]
    assert "INSERT INTO podcasts" in podcast_query
    assert "ON CONFLICT (source, source_podcast_id)" in podcast_query
    assert podcast_params[:6] == (
        mod._SOURCE,
        "101",
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
