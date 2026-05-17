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

from scripts.core import detect_podcast_episode_appearances as mod  # noqa: E402


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
        if normalized.startswith("SELECT c.id, c.name"):
            self._last_result = self._conn.comedian_rows
        elif normalized.startswith("SELECT pe.id, pe.podcast_id"):
            self._last_result = self._conn.episode_rows
        elif normalized.startswith("INSERT INTO episode_appearance_reviews"):
            self._conn.review_writes.append(params)
            self._last_result = []
        elif normalized.startswith("INSERT INTO episode_appearances"):
            self._conn.appearance_writes.append(params)
            self._last_result = []
        else:
            self._last_result = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last_result


class _FakeConn:
    def __init__(
        self,
        *,
        comedian_rows: list[tuple[Any, ...]] | None = None,
        episode_rows: list[tuple[Any, ...]] | None = None,
    ) -> None:
        self.comedian_rows = comedian_rows or []
        self.episode_rows = episode_rows or []
        self.review_writes: list[Any] = []
        self.appearance_writes: list[Any] = []
        self.executed: list[tuple[str, Any]] = []
        self.commits = 0

    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1


def _episode(
    *,
    episode_id: int,
    podcast_id: int = 7,
    title: str,
    description: str = "",
    podcast_author: str = "",
    host_ids: list[int] | None = None,
    host_types: list[str] | None = None,
    source_payload: dict[str, Any] | None = None,
) -> mod.PodcastEpisodeCandidateInput:
    return mod.PodcastEpisodeCandidateInput(
        episode_id=episode_id,
        podcast_id=podcast_id,
        source="podcast_index",
        source_episode_id=f"ep-{episode_id}",
        podcast_title="Comedy Talk",
        podcast_author=podcast_author,
        title=title,
        description=description,
        episode_url=f"https://podcast.example/{episode_id}",
        host_comedian_ids=host_ids or [],
        host_association_types=host_types or [],
        source_payload=source_payload or {},
    )


def test_comedian_query_uses_canonical_non_denied_comedians_and_aliases():
    query = mod._GET_MATCH_COMEDIANS_SQL

    assert "c.parent_comedian_id IS NULL" in query
    assert "comedian_deny_list" in query
    assert "NOT EXISTS" in query
    assert "LOWER(BTRIM(d.name)) = LOWER(BTRIM(c.name))" in query
    assert "a.parent_comedian_id = c.id" in query


def test_episode_query_scans_only_accepted_podcast_relationships():
    query = mod._GET_EPISODES_SQL

    assert "p.author_name AS podcast_author" in query
    assert "EXISTS" in query
    assert "accepted_cp.podcast_id = p.id" in query
    assert "accepted_cp.review_status = 'accepted'" in query


def test_normalization_handles_entities_unicode_punctuation_variants_and_initials():
    assert mod.normalize_match_text("J.R. De&#45;Guzman's Cafe") == "j r de guzman cafe"
    assert mod.normalize_match_text("Steve-O") == mod.normalize_match_text("Steve O")
    assert mod.normalize_match_text("Marc Maron\u2019s WTF") == "marc maron wtf"

    comedian = mod.MatchComedian(12, "J.R. De Guzman", ["JR DeGuzman"])
    terms = mod.build_match_terms(comedian)

    assert any(term.pattern.search("Episode with J R De-Guzman") for term in terms)
    assert any(term.pattern.search("Episode with JR DeGuzman") for term in terms)
    assert not any(term.pattern.search("Dance Party Tonight") for term in terms)


def test_build_match_terms_can_exclude_aliases():
    comedian = mod.MatchComedian(12, "J.R. De Guzman", ["JR DeGuzman"])
    terms = mod.build_match_terms(comedian, include_aliases=False)

    assert any(term.pattern.search("Episode with J R De-Guzman") for term in terms)
    assert not any(term.pattern.search("Episode with JR DeGuzman") for term in terms)


def test_host_relationship_auto_accepts_host_appearance_without_episode_evidence():
    comedian = mod.MatchComedian(12, "Ari Shaffir", [])
    episode = _episode(
        episode_id=1,
        title="Solo episode about travel",
        description="No guest names here",
        host_ids=[12],
        host_types=["host"],
    )

    rows = mod.detect_episode_candidates([comedian], [episode])

    assert [(c.episode_id, c.role_guess, c.status) for c in rows] == [(1, "host", "accepted")]
    assert rows[0].evidence["auto_acceptance"]["rule_id"] == "accepted_host_relationship"


def test_owner_relationship_does_not_create_appearance_even_with_episode_evidence():
    comedian = mod.MatchComedian(12, "Ari Shaffir", [])
    episode = _episode(
        episode_id=3,
        title="Ari Shaffir previews the tour",
        description="Hosted by Ari Shaffir.",
        host_ids=[12],
        host_types=["owner"],
    )

    assert mod.detect_episode_candidates([comedian], [episode]) == []


def test_episode_matching_scores_roles_and_materializes_only_auto_accepted(monkeypatch):
    comedian = mod.MatchComedian(12, "Ari Shaffir", ["Ari"])
    rows = mod.detect_episode_candidates(
        [comedian],
        [
            _episode(
                episode_id=1,
                title="Ari Shaffir on the road",
                description="A wide-ranging interview.",
            ),
            _episode(
                episode_id=2,
                title="Network update",
                description="We mention Ari Shaffir in passing.",
            ),
            _episode(
                episode_id=3,
                title="Ari Shaffir previews the tour",
                description="Hosted by Ari Shaffir.",
                host_ids=[12],
                host_types=["host"],
            ),
        ],
    )

    assert [(c.episode_id, c.role_guess, c.status) for c in rows] == [
        (1, "guest", "accepted"),
        (2, "mention", "ignored"),
        (3, "host", "accepted"),
    ]
    assert rows[0].source_field == "title"
    assert rows[0].confidence >= mod._AUTO_ACCEPT_TITLE_CONFIDENCE
    assert rows[0].evidence["auto_acceptance"]["rule_id"] == "high_confidence_title_name"
    assert rows[1].evidence["auto_acceptance"]["rule_id"] == "low_signal_mention"
    assert "Ari Shaffir" in rows[0].evidence_text

    conn = _FakeConn()
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    summary = mod.persist_candidates(rows, dry_run=False)

    assert summary.candidates == 3
    assert summary.auto_accepted == 2
    assert summary.pending == 0
    assert summary.ignored == 1
    assert len(conn.review_writes) == 3
    assert len(conn.appearance_writes) == 2
    review_params = conn.review_writes[0]
    evidence = json.loads(review_params[7])
    assert review_params[:6] == (12, 1, "podcast_index", "ep-1", "accepted", "guest")
    assert evidence["matched_name"] == "Ari Shaffir"
    assert evidence["source_field"] == "title"
    assert evidence["role_guess"] == "guest"
    assert evidence["auto_acceptance"]["rule_id"] == "high_confidence_title_name"
    assert evidence["evidence_text"]


def test_near_threshold_guest_stays_pending_for_manual_review():
    comedian = mod.MatchComedian(12, "Ari", [])
    rows = mod.detect_episode_candidates(
        [comedian],
        [_episode(episode_id=1, title="Ari on the road")],
    )

    assert [(c.episode_id, c.role_guess, c.confidence, c.status) for c in rows] == [
        (1, "guest", 0.94, "pending")
    ]
    assert "auto_acceptance" not in rows[0].evidence


def test_review_only_detection_keeps_auto_matches_pending(monkeypatch):
    comedian = mod.MatchComedian(12, "Ari Shaffir", [])
    rows = mod.detect_episode_candidates(
        [comedian],
        [_episode(episode_id=1, title="Ari Shaffir on the road")],
        auto_accept=False,
    )

    assert [(c.episode_id, c.role_guess, c.status) for c in rows] == [(1, "guest", "pending")]

    conn = _FakeConn()
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    summary = mod.persist_candidates(rows, dry_run=False)

    assert summary.auto_accepted == 0
    assert summary.pending == 1
    assert len(conn.review_writes) == 1
    assert len(conn.appearance_writes) == 0


def test_person_guest_metadata_creates_high_confidence_candidate_before_title_matching():
    comedian = mod.MatchComedian(12, "Ron Pearson", [])
    rows = mod.detect_episode_candidates(
        [comedian],
        [
            _episode(
                episode_id=9,
                title="Juggling Comedy, Chaos, and Faith",
                source_payload={
                    "persons": [
                        {
                            "id": 73151611,
                            "name": "Ron Pearson",
                            "role": "guest",
                            "href": "http://www.ronpearsoncomedy.com",
                            "img": "https://example.test/ron.jpg",
                        }
                    ]
                },
            )
        ],
        auto_accept=False,
    )

    assert [(c.comedian_id, c.role_guess, c.confidence, c.status) for c in rows] == [
        (12, "guest", 0.99, "pending")
    ]
    assert rows[0].source_field == "persons"
    assert rows[0].evidence_text == "Ron Pearson"
    assert rows[0].evidence["match_source"] == "podcast_index_person"
    assert rows[0].evidence["podcast_index_person_id"] == 73151611
    assert rows[0].evidence["podcast_index_person_role"] == "guest"
    assert rows[0].evidence["podcast_index_person_href"] == "http://www.ronpearsoncomedy.com"
    assert rows[0].evidence["podcast_index_person_img"] == "https://example.test/ron.jpg"


def test_person_host_metadata_is_not_a_guest_candidate():
    comedian = mod.MatchComedian(12, "Ron Pearson", [])
    rows = mod.detect_episode_candidates(
        [comedian],
        [
            _episode(
                episode_id=9,
                title="Juggling Comedy, Chaos, and Faith",
                source_payload={"persons": [{"id": 1, "name": "Ron Pearson", "role": "host"}]},
            )
        ],
        auto_accept=False,
    )

    assert rows == []


def test_load_functions_parse_database_rows(monkeypatch):
    conn = _FakeConn(
        comedian_rows=[(12, "Ari Shaffir", ["Ari"])],
        episode_rows=[
            (
                4,
                9,
                "podcast_index",
                "ep-4",
                "Comedy Talk",
                "Ari Network",
                "Ari Shaffir appears",
                "Episode description",
                "https://podcast.example/4",
                {"persons": [{"name": "Ari Shaffir", "role": "guest"}]},
                [12],
                ["host"],
            )
        ],
    )
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    comedians = mod.load_match_comedians(comedian_ids=[12], limit=1)
    episodes = mod.load_episode_inputs(limit=1)

    assert comedians == [mod.MatchComedian(12, "Ari Shaffir", ["Ari"])]
    assert episodes[0].host_comedian_ids == [12]
    assert episodes[0].host_association_types == ["host"]
    assert episodes[0].podcast_author == "Ari Network"
    assert episodes[0].source_payload == {"persons": [{"name": "Ari Shaffir", "role": "guest"}]}
    assert "LIMIT %s" in conn.executed[0][0]


def test_detect_passes_comedian_limit_and_matching_options(monkeypatch):
    calls: dict[str, Any] = {}

    def fake_load_comedians(**kwargs: Any) -> list[mod.MatchComedian]:
        calls["comedians"] = kwargs
        return [mod.MatchComedian(12, "Ari Shaffir", ["Ari"])]

    def fake_load_episodes(**kwargs: Any) -> list[mod.PodcastEpisodeCandidateInput]:
        calls["episodes"] = kwargs
        return [_episode(episode_id=1, title="Ari Shaffir on the road")]

    def fake_persist(candidates: list[mod.EpisodeAppearanceCandidate], dry_run: bool) -> mod.DetectSummary:
        calls["candidates"] = candidates
        calls["dry_run"] = dry_run
        return mod.DetectSummary(candidates=len(candidates), pending=len(candidates), written=len(candidates))

    monkeypatch.setattr(mod, "load_match_comedians", fake_load_comedians)
    monkeypatch.setattr(mod, "load_episode_inputs", fake_load_episodes)
    monkeypatch.setattr(mod, "persist_candidates", fake_persist)

    summary = mod.detect_podcast_episode_appearances(
        dry_run=False,
        comedian_ids=None,
        comedian_names=None,
        episode_ids=None,
        episode_limit=None,
        comedian_limit=1000,
        include_aliases=False,
        auto_accept=False,
    )

    assert summary.candidates == 1
    assert calls["comedians"] == {"comedian_ids": None, "comedian_names": None, "limit": 1000}
    assert calls["episodes"] == {"episode_ids": None, "limit": None}
    assert calls["candidates"][0].matched_name == "Ari Shaffir"
    assert calls["candidates"][0].status == "pending"
