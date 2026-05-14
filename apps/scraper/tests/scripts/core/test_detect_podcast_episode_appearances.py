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
    host_ids: list[int] | None = None,
    host_types: list[str] | None = None,
) -> mod.PodcastEpisodeCandidateInput:
    return mod.PodcastEpisodeCandidateInput(
        episode_id=episode_id,
        podcast_id=podcast_id,
        source="podcast_index",
        source_episode_id=f"ep-{episode_id}",
        podcast_title="Comedy Talk",
        title=title,
        description=description,
        episode_url=f"https://podcast.example/{episode_id}",
        host_comedian_ids=host_ids or [],
        host_association_types=host_types or [],
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


def test_host_relationship_does_not_create_appearance_without_episode_evidence():
    comedian = mod.MatchComedian(12, "Ari Shaffir", [])
    episode = _episode(
        episode_id=1,
        title="Solo episode about travel",
        description="No guest names here",
        host_ids=[12],
        host_types=["host"],
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
        (2, "mention", "pending"),
        (3, "host", "pending"),
    ]
    assert rows[0].source_field == "title"
    assert rows[0].confidence >= mod._AUTO_ACCEPT_CONFIDENCE
    assert rows[1].confidence < mod._AUTO_ACCEPT_CONFIDENCE
    assert "Ari Shaffir" in rows[0].evidence_text

    conn = _FakeConn()
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    summary = mod.persist_candidates(rows, dry_run=False)

    assert summary.candidates == 3
    assert summary.auto_accepted == 1
    assert summary.pending == 2
    assert len(conn.review_writes) == 3
    assert len(conn.appearance_writes) == 1
    review_params = conn.review_writes[0]
    evidence = json.loads(review_params[7])
    assert review_params[:6] == (12, 1, "podcast_index", "ep-1", "accepted", "guest")
    assert evidence["matched_name"] == "Ari Shaffir"
    assert evidence["source_field"] == "title"
    assert evidence["role_guess"] == "guest"
    assert evidence["evidence_text"]


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
                "Ari Shaffir appears",
                "Episode description",
                "https://podcast.example/4",
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
    assert "LIMIT %s" in conn.executed[0][0]
