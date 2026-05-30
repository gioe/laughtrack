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
    rowcount = -1

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
    source: str = "podcast_index",
) -> mod.PodcastEpisodeCandidateInput:
    return mod.PodcastEpisodeCandidateInput(
        episode_id=episode_id,
        podcast_id=podcast_id,
        source=source,
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


def _capture_execute_values(monkeypatch):
    def fake_execute_values(cur: _FakeCursor, sql: str, rows: list[tuple[Any, ...]], **_kwargs: Any) -> None:
        normalized = " ".join(sql.split())
        if normalized.startswith("INSERT INTO episode_appearance_reviews"):
            cur._conn.review_writes.extend(rows)
        elif normalized.startswith("INSERT INTO episode_appearances"):
            cur._conn.appearance_writes.extend(rows)

    monkeypatch.setattr(mod, "execute_values", fake_execute_values)


def test_comedian_query_uses_canonical_non_denied_comedians_and_aliases():
    query = mod._GET_MATCH_COMEDIANS_SQL

    assert "c.parent_comedian_id IS NULL" in query
    assert "comedian_deny_list" in query
    assert "NOT EXISTS" in query
    assert "LOWER(BTRIM(d.name)) = LOWER(BTRIM(c.name))" in query
    assert "a.parent_comedian_id = c.id" in query


def test_episode_query_scans_only_accepted_podcast_relationships():
    # Eligibility (only episodes from accepted-comedian podcasts) is enforced in
    # the Phase-1 candidate-id selection; Phase 2 hydrates the chosen ids.
    id_query = mod._GET_EPISODE_IDS_SQL
    assert "EXISTS" in id_query
    assert "accepted_cp.podcast_id = p.id" in id_query
    assert "accepted_cp.review_status = 'accepted'" in id_query

    hydrate_query = mod._GET_EPISODES_SQL
    assert "p.author_name AS podcast_author" in hydrate_query
    # Phase 2 is bounded to the Phase-1 id set rather than re-scanning the backlog.
    assert "pe.id = ANY(%s::int[])" in hydrate_query


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
    _capture_execute_values(monkeypatch)

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
    _capture_execute_values(monkeypatch)

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


def test_load_episode_inputs_is_two_phase_and_hydrates_only_phase1_ids(monkeypatch):
    # Regression guard for TASK-2530: episode loading must stay two-phase so the
    # heavy GROUP BY / array_agg runs only over the bounded candidate-id set, not
    # the full eligible backlog (which tripped Neon's 30s statement_timeout).
    conn = _FakeConn(
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
                {},
                [12],
                ["host"],
            )
        ],
    )
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    mod.load_episode_inputs(limit=10)

    assert len(conn.executed) == 2, "expected a candidate-id query then a hydrate query"
    id_sql, _ = conn.executed[0]
    hydrate_sql, hydrate_params = conn.executed[1]
    # Phase 1 selects ids in cursor order with the bound; no GROUP BY there.
    assert id_sql.strip().startswith("SELECT pe.id, pe.podcast_id")
    assert "GROUP BY" not in id_sql
    assert "LIMIT %s" in id_sql
    # Phase 2 hydrates only the ids Phase 1 returned (episode id 4 here).
    assert "pe.id = ANY(%s::int[])" in hydrate_sql
    assert "GROUP BY" in hydrate_sql
    assert hydrate_params == ([4],)


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
    assert calls["episodes"] == {"episode_ids": None, "sources": None, "limit": None}
    assert calls["candidates"][0].matched_name == "Ari Shaffir"
    assert calls["candidates"][0].status == "pending"


def test_detector_processes_episodes_from_multiple_sources_and_preserves_source_on_writes(monkeypatch):
    comedian = mod.MatchComedian(12, "Ari Shaffir", [])
    rows = mod.detect_episode_candidates(
        [comedian],
        [
            _episode(
                episode_id=101,
                title="Ari Shaffir on the road",
                source="podcast_index",
            ),
            _episode(
                episode_id=202,
                title="Ari Shaffir on the road",
                source="itunes",
            ),
        ],
    )

    assert [(c.episode_id, c.source, c.role_guess, c.status) for c in rows] == [
        (101, "podcast_index", "guest", "accepted"),
        (202, "itunes", "guest", "accepted"),
    ]
    for candidate in rows:
        assert candidate.confidence >= mod._AUTO_ACCEPT_TITLE_CONFIDENCE
        assert candidate.evidence["auto_acceptance"]["rule_id"] == "high_confidence_title_name"

    conn = _FakeConn()
    monkeypatch.setattr(mod, "get_connection", lambda: conn)
    _capture_execute_values(monkeypatch)

    summary = mod.persist_candidates(rows, dry_run=False)

    assert summary.auto_accepted == 2
    review_sources = sorted(params[2] for params in conn.review_writes)
    appearance_sources = sorted(params[2] for params in conn.appearance_writes)
    assert review_sources == ["itunes", "podcast_index"]
    assert appearance_sources == ["itunes", "podcast_index"]


def test_cohost_relationship_persists_as_host_role(monkeypatch):
    comedian = mod.MatchComedian(12, "Ari Shaffir", [])
    rows = mod.detect_episode_candidates(
        [comedian],
        [
            _episode(
                episode_id=303,
                title="Ari Shaffir checks in",
                host_ids=[12],
                host_types=["cohost"],
            ),
        ],
    )

    assert [(c.role_guess, c.status) for c in rows] == [("host", "accepted")]

    conn = _FakeConn()
    monkeypatch.setattr(mod, "get_connection", lambda: conn)
    _capture_execute_values(monkeypatch)

    mod.persist_candidates(rows, dry_run=False)

    assert conn.review_writes[0][5] == "host"
    assert conn.appearance_writes[0][3] == "host"


def test_load_episode_inputs_default_query_omits_source_filter_and_binds_no_params(monkeypatch):
    conn = _FakeConn(episode_rows=[])
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    mod.load_episode_inputs()

    sql, params = conn.executed[0]
    assert "p.source = %s" not in sql
    assert "pe.source = %s" not in sql
    assert params is None


def test_load_episode_inputs_source_filter_binds_array_params_for_each_source_column(monkeypatch):
    conn = _FakeConn(episode_rows=[])
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    mod.load_episode_inputs(sources=["itunes", "podcast_index"])

    sql, params = conn.executed[0]
    assert "AND p.source = ANY(%s::text[])" in sql
    assert "AND pe.source = ANY(%s::text[])" in sql
    assert params == (["itunes", "podcast_index"], ["itunes", "podcast_index"])


def test_episode_query_orders_least_recently_scanned_first():
    query = mod._GET_EPISODES_SQL

    # NULLS FIRST keeps never-scanned episodes ahead of the oldest-scanned ones,
    # so a bounded --episode-limit batch rotates through the full backlog.
    assert "appearances_detected_at ASC NULLS FIRST" in query


def test_mark_episodes_scanned_issues_bounded_update(monkeypatch):
    conn = _FakeConn()
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    mod.mark_episodes_scanned([3, 1, 2])

    update_calls = [call for call in conn.executed if "UPDATE podcast_episodes" in call[0]]
    assert len(update_calls) == 1
    assert "appearances_detected_at = NOW()" in update_calls[0][0]
    assert update_calls[0][1] == ([3, 1, 2],)
    assert conn.commits == 1


def test_mark_episodes_scanned_noop_for_empty_batch(monkeypatch):
    conn = _FakeConn()
    monkeypatch.setattr(mod, "get_connection", lambda: conn)

    assert mod.mark_episodes_scanned([]) == 0
    assert conn.executed == []


def _stub_detect_pipeline(monkeypatch, marked: dict[str, Any]) -> None:
    monkeypatch.setattr(
        mod, "load_match_comedians", lambda **_kw: [mod.MatchComedian(12, "Ari Shaffir", [])]
    )
    monkeypatch.setattr(
        mod,
        "load_episode_inputs",
        lambda **_kw: [_episode(episode_id=5, title="Ari Shaffir on the road")],
    )
    monkeypatch.setattr(mod, "persist_candidates", lambda _c, dry_run: mod.DetectSummary())
    monkeypatch.setattr(mod, "mark_episodes_scanned", lambda ids: marked.__setitem__("ids", ids))


def test_full_roster_run_marks_scanned_episodes(monkeypatch):
    marked: dict[str, Any] = {}
    _stub_detect_pipeline(monkeypatch, marked)

    mod.detect_podcast_episode_appearances(
        dry_run=False,
        comedian_ids=None,
        comedian_names=None,
        episode_ids=None,
        episode_limit=2000,
        comedian_limit=None,
        include_aliases=True,
        auto_accept=True,
    )

    assert marked["ids"] == [5]


def test_comedian_subset_run_does_not_advance_scan_cursor(monkeypatch):
    marked: dict[str, Any] = {}
    _stub_detect_pipeline(monkeypatch, marked)

    mod.detect_podcast_episode_appearances(
        dry_run=False,
        comedian_ids=None,
        comedian_names=None,
        episode_ids=None,
        episode_limit=2000,
        comedian_limit=1000,
        include_aliases=True,
        auto_accept=True,
    )

    assert "ids" not in marked


def test_dry_run_does_not_advance_scan_cursor(monkeypatch):
    marked: dict[str, Any] = {}
    _stub_detect_pipeline(monkeypatch, marked)

    mod.detect_podcast_episode_appearances(
        dry_run=True,
        comedian_ids=None,
        comedian_names=None,
        episode_ids=None,
        episode_limit=2000,
        comedian_limit=None,
        include_aliases=True,
        auto_accept=True,
    )

    assert "ids" not in marked


def test_empty_roster_run_does_not_drain_backlog(monkeypatch):
    # An anomalous empty comedian load (transient DB hiccup or query regression)
    # must not bump episodes that were never matched against anyone — otherwise
    # the next run sorts them last and skips them, the opposite of rotation.
    marked: dict[str, Any] = {}
    _stub_detect_pipeline(monkeypatch, marked)
    monkeypatch.setattr(mod, "load_match_comedians", lambda **_kw: [])

    mod.detect_podcast_episode_appearances(
        dry_run=False,
        comedian_ids=None,
        comedian_names=None,
        episode_ids=None,
        episode_limit=2000,
        comedian_limit=None,
        include_aliases=True,
        auto_accept=True,
    )

    assert "ids" not in marked
