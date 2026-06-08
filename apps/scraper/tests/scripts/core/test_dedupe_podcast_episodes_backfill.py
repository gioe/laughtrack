from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import dedupe_podcast_episodes_backfill as mod  # noqa: E402


class _FakeCursor:
    def __init__(self, conn: "_FakeConn") -> None:
        self._conn = conn
        self._last_result: list[tuple[Any, ...]] = []
        self.rowcount = 0

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def execute(self, sql: str, params: Any = None) -> None:
        self._conn.executed.append((sql, params))
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT podcast_id, release_date, title, array_agg"):
            groups: dict[tuple[int, Any, str], list[int]] = {}
            for row in self._conn.episodes:
                key = (row["podcast_id"], row["release_date"], row["title"])
                groups.setdefault(key, []).append(row["id"])
            self._last_result = [
                (k[0], k[1], k[2], sorted(ids)) for k, ids in groups.items() if len(ids) > 1
            ]
        elif normalized.startswith("SELECT COUNT(*) FROM ( SELECT DISTINCT ON"):
            non_canonical_ids, canonical_id = params
            self._last_result = [(self._compute_repointable(canonical_id, non_canonical_ids),)]
        elif normalized.startswith("SELECT COUNT(*) FROM episode_appearances"):
            (non_canonical_ids,) = params
            target_ids = set(non_canonical_ids)
            count = sum(1 for a in self._conn.appearances if a["episode_id"] in target_ids)
            self._last_result = [(count,)]
        elif normalized.startswith("SELECT COUNT(*) FROM episode_appearance_reviews"):
            (non_canonical_ids,) = params
            target_ids = set(non_canonical_ids)
            count = sum(1 for r in self._conn.reviews if r["episode_id"] in target_ids)
            self._last_result = [(count,)]
        elif normalized.startswith("UPDATE episode_appearances"):
            canonical_id, non_canonical_ids, canonical_id_check = params
            assert canonical_id == canonical_id_check
            ids_to_repoint = self._compute_repointable_ids(canonical_id, non_canonical_ids)
            updated = 0
            for appearance in self._conn.appearances:
                if appearance["id"] in ids_to_repoint:
                    appearance["episode_id"] = canonical_id
                    updated += 1
            self.rowcount = updated
        elif normalized.startswith("DELETE FROM episode_appearances"):
            (non_canonical_ids,) = params
            target_ids = set(non_canonical_ids)
            before = len(self._conn.appearances)
            self._conn.appearances = [
                a for a in self._conn.appearances if a["episode_id"] not in target_ids
            ]
            self.rowcount = before - len(self._conn.appearances)
        elif normalized.startswith("UPDATE episode_appearance_reviews"):
            canonical_id, non_canonical_ids = params
            target_ids = set(non_canonical_ids)
            updated = 0
            for review in self._conn.reviews:
                if review["episode_id"] in target_ids:
                    review["episode_id"] = canonical_id
                    updated += 1
            self.rowcount = updated
        elif normalized.startswith("DELETE FROM podcast_episodes"):
            (non_canonical_ids,) = params
            target_ids = set(non_canonical_ids)
            before = len(self._conn.episodes)
            self._conn.episodes = [e for e in self._conn.episodes if e["id"] not in target_ids]
            self.rowcount = before - len(self._conn.episodes)
        else:
            self._last_result = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last_result

    def fetchone(self) -> Any:
        return self._last_result[0] if self._last_result else None

    def _compute_repointable_ids(self, canonical_id: int, non_canonical_ids: list[int]) -> set[int]:
        """Mirror the production DISTINCT ON (comedian_id, source) ORDER BY id semantics.

        Picks the lowest-id appearance row per (comedian_id, source) tuple,
        excluding rows that would collide with an existing appearance on the
        canonical episode. Other rows on non-canonical episodes fall through
        to the DELETE step.
        """
        target_ids = set(non_canonical_ids)
        already_on_canonical = {
            (a["comedian_id"], a["source"])
            for a in self._conn.appearances
            if a["episode_id"] == canonical_id
        }
        chosen: dict[tuple[int, str], int] = {}
        for appearance in sorted(self._conn.appearances, key=lambda a: a["id"]):
            if appearance["episode_id"] not in target_ids:
                continue
            slot = (appearance["comedian_id"], appearance["source"])
            if slot in already_on_canonical or slot in chosen:
                continue
            chosen[slot] = appearance["id"]
        return set(chosen.values())

    def _compute_repointable(self, canonical_id: int, non_canonical_ids: list[int]) -> int:
        return len(self._compute_repointable_ids(canonical_id, non_canonical_ids))


class _FakeConn:
    def __init__(
        self,
        episodes: list[dict[str, Any]] | None = None,
        appearances: list[dict[str, Any]] | None = None,
        reviews: list[dict[str, Any]] | None = None,
    ) -> None:
        self.episodes = list(episodes or [])
        self.appearances = list(appearances or [])
        self.reviews = list(reviews or [])
        self.executed: list[tuple[str, Any]] = []
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


def _install_conn(monkeypatch: pytest.MonkeyPatch, conn: _FakeConn) -> None:
    def _factory(*, autocommit: bool = True) -> _FakeConn:
        conn.autocommit_args.append(autocommit)
        return conn

    monkeypatch.setattr(mod, "get_connection", _factory)


def test_dry_run_reports_planned_deletes_without_mutating(monkeypatch):
    """Criterion 8882: dry-run pytest exercises canonical-row choice and re-point
    plan against a fixture without writes."""
    conn = _FakeConn(
        episodes=[
            # Dupe group A: two episodes, lowest id is canonical
            {"id": 100, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            {"id": 101, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            # Dupe group B: three episodes
            {"id": 200, "podcast_id": 2, "release_date": "2025-02-01", "title": "Ep Two"},
            {"id": 201, "podcast_id": 2, "release_date": "2025-02-01", "title": "Ep Two"},
            {"id": 202, "podcast_id": 2, "release_date": "2025-02-01", "title": "Ep Two"},
            # Unique episode — not in any dupe group
            {"id": 300, "podcast_id": 3, "release_date": "2025-03-01", "title": "Solo"},
        ],
        appearances=[
            {"id": 1, "episode_id": 100, "comedian_id": 7, "source": "rss"},
            {"id": 2, "episode_id": 101, "comedian_id": 8, "source": "rss"},
            {"id": 3, "episode_id": 202, "comedian_id": 9, "source": "rss"},
        ],
    )
    _install_conn(monkeypatch, conn)

    summary = mod.dedupe_podcast_episodes(dry_run=True, confirm=False)

    # Plan reports both dupe groups and the planned delete count
    assert summary.groups_scanned == 2
    assert summary.episodes_deleted == 3  # 1 from group A + 2 from group B

    # Preview reports the appearance-level impact (criterion 8882 — canonical
    # row choice + re-point plan exercised against the fixture without writes)
    assert summary.appearances_repointed == 2  # 1 on ep 101 + 1 on ep 202
    assert summary.appearances_absorbed == 0
    assert summary.reviews_repointed == 0
    assert summary.groups_failed == 0

    # State must be untouched: only SELECTs executed, no UPDATEs/DELETEs
    assert len(conn.episodes) == 6
    assert len(conn.appearances) == 3
    assert {a["episode_id"] for a in conn.appearances} == {100, 101, 202}
    assert conn.commits == 0
    assert conn.rollbacks == 0
    only_select = [
        sql for sql, _ in conn.executed if " ".join(sql.split()).startswith("SELECT")
    ]
    assert len(only_select) == len(conn.executed)


def test_confirm_repoints_and_deletes_with_unchanged_appearance_count(monkeypatch):
    """Criterion 8883: after confirm-mode, dupe count is zero and the raw
    episode_appearances row count is unchanged (no collisions in the fixture)."""
    conn = _FakeConn(
        episodes=[
            {"id": 100, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            {"id": 101, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            {"id": 200, "podcast_id": 2, "release_date": "2025-02-01", "title": "Ep Two"},
            {"id": 201, "podcast_id": 2, "release_date": "2025-02-01", "title": "Ep Two"},
            {"id": 202, "podcast_id": 2, "release_date": "2025-02-01", "title": "Ep Two"},
        ],
        appearances=[
            # Different (comedian, source) per row — no collisions on re-point
            {"id": 1, "episode_id": 100, "comedian_id": 7, "source": "rss"},
            {"id": 2, "episode_id": 101, "comedian_id": 8, "source": "rss"},
            {"id": 3, "episode_id": 200, "comedian_id": 9, "source": "rss"},
            {"id": 4, "episode_id": 201, "comedian_id": 10, "source": "rss"},
            {"id": 5, "episode_id": 202, "comedian_id": 11, "source": "rss"},
        ],
        reviews=[
            {"id": 1, "episode_id": 101, "status": "pending"},
            {"id": 2, "episode_id": 202, "status": "approved"},
        ],
    )
    _install_conn(monkeypatch, conn)

    pre_appearance_count = len(conn.appearances)

    summary = mod.dedupe_podcast_episodes(dry_run=False, confirm=True)

    # Dupe-count post-condition: GROUP BY having COUNT > 1 returns zero groups
    remaining_groups: dict[tuple[int, Any, str], int] = {}
    for episode in conn.episodes:
        key = (episode["podcast_id"], episode["release_date"], episode["title"])
        remaining_groups[key] = remaining_groups.get(key, 0) + 1
    assert all(count == 1 for count in remaining_groups.values())

    # Raw appearance count is unchanged — no collisions in this fixture
    assert len(conn.appearances) == pre_appearance_count

    # Re-point landed on canonical ids
    assert {a["episode_id"] for a in conn.appearances} == {100, 200}
    assert {r["episode_id"] for r in conn.reviews} == {100, 200}

    # Summary numbers reflect the work
    assert summary.groups_scanned == 2
    assert summary.episodes_deleted == 3
    # Non-canonical appearance rows: 1 on episode 101 + 1 on 201 + 1 on 202.
    # Episodes 100 and 200 already sat on the canonical side and were not touched.
    assert summary.appearances_repointed == 3
    assert summary.appearances_absorbed == 0
    assert summary.reviews_repointed == 2
    assert summary.groups_failed == 0

    # Transaction discipline
    assert conn.commits == 1
    assert conn.rollbacks == 0
    assert conn.autocommit_args == [False]


def test_confirm_absorbs_appearance_collisions_and_preserves_podcast_comedian_pairs(
    monkeypatch,
):
    """Criterion 8885 (collision case): when re-pointing would violate the
    (comedian_id, episode_id, source) unique constraint, the duplicate row is
    absorbed. Every (podcast_id, comedian_id) connection that existed before
    must still exist after — no comedian is silently dropped from the podcast."""
    conn = _FakeConn(
        episodes=[
            {"id": 100, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            {"id": 101, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
        ],
        appearances=[
            # Both rows are for the same comedian/source on the same podcast —
            # re-point would collide, so the dupe row gets absorbed instead.
            {"id": 1, "episode_id": 100, "comedian_id": 7, "source": "rss"},
            {"id": 2, "episode_id": 101, "comedian_id": 7, "source": "rss"},
            # Distinct (comedian, source) on the dupe — should re-point cleanly.
            {"id": 3, "episode_id": 101, "comedian_id": 8, "source": "rss"},
        ],
    )
    _install_conn(monkeypatch, conn)

    # Snapshot pre-state: which (podcast, comedian) pairs are recorded?
    episode_to_podcast = {e["id"]: e["podcast_id"] for e in conn.episodes}
    pre_pairs = {
        (episode_to_podcast[a["episode_id"]], a["comedian_id"]) for a in conn.appearances
    }

    summary = mod.dedupe_podcast_episodes(dry_run=False, confirm=True)

    # Every pre-existing (podcast, comedian) pair survives — comedian 7 still
    # appears on podcast 1, just via the canonical episode now.
    post_pairs = {(1, a["comedian_id"]) for a in conn.appearances}
    assert post_pairs == pre_pairs

    # Raw count drops by exactly the collider that got absorbed
    assert len(conn.appearances) == 2
    assert summary.appearances_repointed == 1  # comedian 8's row re-pointed
    assert summary.appearances_absorbed == 1  # comedian 7's dupe absorbed
    assert summary.episodes_deleted == 1

    # Surviving rows all live on the canonical episode
    assert {a["episode_id"] for a in conn.appearances} == {100}


def test_confirm_handles_intra_non_canonical_collision_without_constraint_violation(
    monkeypatch,
):
    """Reviewer finding #2897 / #2899: when 3+ siblings carry the same
    (comedian_id, source) tuple on the non-canonical side AND no such row
    exists on the canonical, the script must absorb all but one without
    tripping the (comedian_id, episode_id, source) unique constraint."""
    conn = _FakeConn(
        episodes=[
            {"id": 100, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            {"id": 101, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            {"id": 102, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
        ],
        appearances=[
            # Three sibling rows for the same (comedian, source), canonical has none
            {"id": 1, "episode_id": 101, "comedian_id": 7, "source": "rss"},
            {"id": 2, "episode_id": 102, "comedian_id": 7, "source": "rss"},
            # A non-colliding row that should still re-point cleanly
            {"id": 3, "episode_id": 102, "comedian_id": 8, "source": "rss"},
        ],
    )
    _install_conn(monkeypatch, conn)

    summary = mod.dedupe_podcast_episodes(dry_run=False, confirm=True)

    # Exactly one row per (comedian, source) on the canonical, no constraint violation
    canonical_slots = {
        (a["comedian_id"], a["source"]) for a in conn.appearances if a["episode_id"] == 100
    }
    assert canonical_slots == {(7, "rss"), (8, "rss")}
    assert all(a["episode_id"] == 100 for a in conn.appearances)

    # The duplicate sibling for comedian 7 was absorbed, the unique row re-pointed
    assert summary.appearances_repointed == 2  # one (c=7) + one (c=8)
    assert summary.appearances_absorbed == 1  # the duplicate (c=7, e=102)
    assert summary.episodes_deleted == 2
    assert summary.groups_failed == 0
    assert conn.commits == 1
    assert conn.rollbacks == 0


def test_dry_run_preview_counts_match_confirm_outcome(monkeypatch):
    """Reviewer finding #2900: dry-run must populate the full preview, not
    just episodes_deleted, so operators can estimate impact before --confirm."""

    def _fresh_fixture() -> _FakeConn:
        return _FakeConn(
            episodes=[
                {"id": 100, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
                {"id": 101, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
                {"id": 102, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            ],
            appearances=[
                {"id": 1, "episode_id": 101, "comedian_id": 7, "source": "rss"},
                {"id": 2, "episode_id": 102, "comedian_id": 7, "source": "rss"},
                {"id": 3, "episode_id": 102, "comedian_id": 8, "source": "rss"},
            ],
            reviews=[
                {"id": 1, "episode_id": 101, "status": "pending"},
                {"id": 2, "episode_id": 102, "status": "approved"},
            ],
        )

    dry_conn = _fresh_fixture()
    _install_conn(monkeypatch, dry_conn)
    dry_summary = mod.dedupe_podcast_episodes(dry_run=True, confirm=False)

    confirm_conn = _fresh_fixture()
    _install_conn(monkeypatch, confirm_conn)
    confirm_summary = mod.dedupe_podcast_episodes(dry_run=False, confirm=True)

    assert dry_summary.groups_scanned == confirm_summary.groups_scanned
    assert dry_summary.episodes_deleted == confirm_summary.episodes_deleted
    assert dry_summary.appearances_repointed == confirm_summary.appearances_repointed
    assert dry_summary.appearances_absorbed == confirm_summary.appearances_absorbed
    assert dry_summary.reviews_repointed == confirm_summary.reviews_repointed

    # Dry-run does not mutate
    assert dry_conn.commits == 0
    assert dry_conn.rollbacks == 0
    assert len(dry_conn.episodes) == 3
    assert len(dry_conn.appearances) == 3


def test_limit_caps_groups_processed(monkeypatch):
    conn = _FakeConn(
        episodes=[
            {"id": 100, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            {"id": 101, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            {"id": 200, "podcast_id": 2, "release_date": "2025-02-01", "title": "Ep Two"},
            {"id": 201, "podcast_id": 2, "release_date": "2025-02-01", "title": "Ep Two"},
        ],
    )
    _install_conn(monkeypatch, conn)

    summary = mod.dedupe_podcast_episodes(dry_run=True, confirm=False, limit=1)

    assert summary.groups_scanned == 1
    assert summary.episodes_deleted == 1


def test_main_rejects_missing_mode_flag(monkeypatch):
    with pytest.raises(SystemExit) as excinfo:
        mod.main([])
    assert excinfo.value.code == 2


def test_main_rejects_both_mode_flags(monkeypatch):
    with pytest.raises(SystemExit) as excinfo:
        mod.main(["--dry-run", "--confirm"])
    # argparse's mutually exclusive group exits 2 by itself
    assert excinfo.value.code == 2


def test_failure_rolls_back_transaction(monkeypatch):
    conn = _FakeConn(
        episodes=[
            {"id": 100, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
            {"id": 101, "podcast_id": 1, "release_date": "2025-01-01", "title": "Ep One"},
        ],
    )
    _install_conn(monkeypatch, conn)

    def _boom(_conn, _group):
        raise RuntimeError("simulated DB error")

    monkeypatch.setattr(mod, "_reconcile_group", _boom)

    with pytest.raises(RuntimeError, match="simulated DB error"):
        mod.dedupe_podcast_episodes(dry_run=False, confirm=True)

    assert conn.commits == 0
    assert conn.rollbacks == 1
