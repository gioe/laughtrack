from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import backfill_podcast_appearances as mod  # noqa: E402
from scripts.core import detect_podcast_episode_appearances as detect  # noqa: E402


class _FakeTx:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def __enter__(self) -> "_FakeTx":
        return self

    def __exit__(self, exc_type: Any, *_exc: Any) -> bool:
        self.committed = exc_type is None
        self.rolled_back = exc_type is not None
        return False


def _candidate(status: str = "accepted") -> detect.EpisodeAppearanceCandidate:
    return detect.EpisodeAppearanceCandidate(
        comedian_id=12,
        episode_id=34,
        source="podcast_index",
        source_episode_id="episode-34",
        matched_name="Ari Shaffir",
        source_field="title",
        role_guess="guest",
        confidence=0.97,
        evidence_text="Ari Shaffir",
        evidence={"detected_by": "test"},
        status=status,
    )


def test_backfill_runs_all_comedians_in_one_transaction_and_stamps_evidence(monkeypatch):
    tx = _FakeTx()
    calls: dict[str, Any] = {}

    monkeypatch.setattr(mod, "get_transaction", lambda: tx)
    monkeypatch.setattr(mod, "validate_shape", lambda conn: [])
    monkeypatch.setattr(mod, "load_before_snapshot", lambda conn: mod.BackfillSnapshot(0, 0, 0, 0))
    monkeypatch.setattr(mod, "load_after_snapshot", lambda conn: mod.BackfillSnapshot(2, 2, 1, 0))

    def fake_load_comedians(conn: Any, **kwargs: Any) -> list[detect.MatchComedian]:
        calls["comedian_kwargs"] = kwargs
        return [detect.MatchComedian(12, "Ari Shaffir", [])]

    def fake_load_episodes(conn: Any, **kwargs: Any) -> list[detect.PodcastEpisodeCandidateInput]:
        calls["episode_kwargs"] = kwargs
        return []

    def fake_detect(
        comedians: list[detect.MatchComedian],
        episodes: list[detect.PodcastEpisodeCandidateInput],
        **kwargs: Any,
    ) -> list[detect.EpisodeAppearanceCandidate]:
        calls["detect_kwargs"] = kwargs
        return [_candidate()]

    def fake_persist(
        conn: Any,
        candidates: list[detect.EpisodeAppearanceCandidate],
        dry_run: bool,
    ) -> detect.DetectSummary:
        calls["persist"] = (conn, candidates, dry_run)
        return detect.DetectSummary(candidates=1, auto_accepted=1, written=1)

    monkeypatch.setattr(mod.detect_mod, "load_match_comedians_from_conn", fake_load_comedians)
    monkeypatch.setattr(mod.detect_mod, "load_episode_inputs_from_conn", fake_load_episodes)
    monkeypatch.setattr(mod.detect_mod, "detect_episode_candidates", fake_detect)
    monkeypatch.setattr(mod.detect_mod, "persist_candidates_with_conn", fake_persist)

    summary = mod.backfill_podcast_appearances(dry_run=False)

    assert tx.committed is True
    assert summary.written == 1
    assert calls["comedian_kwargs"] == {"comedian_ids": None, "comedian_names": None, "limit": None}
    assert calls["episode_kwargs"] == {"episode_ids": None, "limit": None}
    assert calls["detect_kwargs"] == {"include_aliases": True, "auto_accept": True}
    persisted_candidate = calls["persist"][1][0]
    assert persisted_candidate.evidence[mod._METADATA_KEY]["task_id"] == 2261
    assert persisted_candidate.evidence[mod._METADATA_KEY]["kind"] == "podcast_appearance_backfill"


def test_dry_run_detects_candidates_but_does_not_write(monkeypatch):
    tx = _FakeTx()
    persisted: list[Any] = []

    monkeypatch.setattr(mod, "get_transaction", lambda: tx)
    monkeypatch.setattr(mod, "validate_shape", lambda conn: [])
    monkeypatch.setattr(mod, "load_before_snapshot", lambda conn: mod.BackfillSnapshot(0, 0, 0, 0))
    monkeypatch.setattr(mod, "load_after_snapshot", lambda conn: mod.BackfillSnapshot(0, 0, 0, 0))
    monkeypatch.setattr(mod.detect_mod, "load_match_comedians_from_conn", lambda conn, **kwargs: [])
    monkeypatch.setattr(mod.detect_mod, "load_episode_inputs_from_conn", lambda conn, **kwargs: [])
    monkeypatch.setattr(mod.detect_mod, "detect_episode_candidates", lambda *_args, **_kwargs: [_candidate()])
    monkeypatch.setattr(
        mod.detect_mod,
        "persist_candidates_with_conn",
        lambda *_args, **_kwargs: persisted.append((_args, _kwargs)),
    )

    summary = mod.backfill_podcast_appearances(dry_run=True)

    assert tx.committed is True
    assert summary.candidates == 1
    assert summary.written == 0
    assert persisted == []


def test_shape_mismatch_refuses_to_detect_or_write(monkeypatch):
    tx = _FakeTx()
    detect_called = False

    monkeypatch.setattr(mod, "get_transaction", lambda: tx)
    monkeypatch.setattr(mod, "validate_shape", lambda conn: ["missing episode_appearances.review_status"])
    monkeypatch.setattr(mod, "load_before_snapshot", lambda conn: mod.BackfillSnapshot(0, 0, 0, 0))

    def fake_detect(*_args: Any, **_kwargs: Any) -> list[Any]:
        nonlocal detect_called
        detect_called = True
        return []

    monkeypatch.setattr(mod.detect_mod, "detect_episode_candidates", fake_detect)

    result = mod.backfill_podcast_appearances(dry_run=False)

    assert result.problems == ["missing episode_appearances.review_status"]
    assert detect_called is False
