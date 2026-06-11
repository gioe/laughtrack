from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parents[3]
_src_path = _repo_root / "src"
for _p in (str(_src_path), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.core import cleanup_podcast_canonical_duplicates as mod  # noqa: E402


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
        if normalized.startswith("SELECT podcast_id") and "'guid' AS reason" in normalized:
            podcast_ids = params[0] if params else None
            self._last_result = self._episode_groups("guid", podcast_ids=podcast_ids)
        elif normalized.startswith("SELECT podcast_id") and "'audio_url' AS reason" in normalized:
            podcast_ids = params[0] if params else None
            self._last_result = self._episode_groups("audio_url", podcast_ids=podcast_ids)
        elif normalized.startswith("SELECT COUNT(*) FROM ( SELECT DISTINCT ON"):
            non_canonical_ids, canonical_id = params
            self._last_result = [(len(self._repointable_appearance_ids(canonical_id, non_canonical_ids)),)]
        elif normalized.startswith("SELECT COUNT(*) FROM episode_appearances"):
            (non_canonical_ids,) = params
            target_ids = set(non_canonical_ids)
            self._last_result = [
                (sum(1 for a in self._conn.appearances if a["episode_id"] in target_ids),)
            ]
        elif normalized.startswith("SELECT COUNT(*) FROM episode_appearance_reviews"):
            (non_canonical_ids,) = params
            target_ids = set(non_canonical_ids)
            self._last_result = [(sum(1 for r in self._conn.reviews if r["episode_id"] in target_ids),)]
        elif normalized.startswith("UPDATE episode_appearances"):
            canonical_id, non_canonical_ids, canonical_id_check = params
            assert canonical_id == canonical_id_check
            target_appearance_ids = self._repointable_appearance_ids(canonical_id, non_canonical_ids)
            updated = 0
            for appearance in self._conn.appearances:
                if appearance["id"] in target_appearance_ids:
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
        elif normalized.startswith("WITH scored") and "FROM podcasts p" in normalized:
            self._last_result = self._podcast_groups()
        elif normalized.startswith("UPDATE podcast_episodes SET podcast_id"):
            canonical_id, non_canonical_ids = params
            target_ids = set(non_canonical_ids)
            updated = 0
            for episode in self._conn.episodes:
                if episode["podcast_id"] in target_ids:
                    episode["podcast_id"] = canonical_id
                    updated += 1
            self.rowcount = updated
        elif normalized.startswith("UPDATE comedian_podcasts"):
            canonical_id, non_canonical_ids, canonical_id_check = params
            assert canonical_id == canonical_id_check
            ids_to_repoint = self._repointable_comedian_podcast_ids(canonical_id, non_canonical_ids)
            updated = 0
            for row in self._conn.comedian_podcasts:
                if row["id"] in ids_to_repoint:
                    row["podcast_id"] = canonical_id
                    updated += 1
            self.rowcount = updated
        elif normalized.startswith("DELETE FROM comedian_podcasts"):
            (non_canonical_ids,) = params
            target_ids = set(non_canonical_ids)
            before = len(self._conn.comedian_podcasts)
            self._conn.comedian_podcasts = [
                r for r in self._conn.comedian_podcasts if r["podcast_id"] not in target_ids
            ]
            self.rowcount = before - len(self._conn.comedian_podcasts)
        elif normalized.startswith("UPDATE podcast_candidate_reviews"):
            canonical_id, non_canonical_ids = params
            target_ids = set(non_canonical_ids)
            updated = 0
            for row in self._conn.candidate_reviews:
                if row["podcast_id"] in target_ids:
                    row["podcast_id"] = canonical_id
                    updated += 1
            self.rowcount = updated
        elif normalized.startswith("UPDATE podcast_deny_list"):
            canonical_id, non_canonical_ids, canonical_id_check = params
            assert canonical_id == canonical_id_check
            target_ids = set(non_canonical_ids)
            has_canonical = any(row["podcast_id"] == canonical_id for row in self._conn.deny_list)
            updated = 0
            if not has_canonical:
                for row in sorted(self._conn.deny_list, key=lambda r: r["id"]):
                    if row["podcast_id"] in target_ids:
                        row["podcast_id"] = canonical_id
                        updated += 1
                        break
            self.rowcount = updated
        elif normalized.startswith("DELETE FROM podcast_deny_list"):
            (non_canonical_ids,) = params
            target_ids = set(non_canonical_ids)
            before = len(self._conn.deny_list)
            self._conn.deny_list = [
                r for r in self._conn.deny_list if r["podcast_id"] not in target_ids
            ]
            self.rowcount = before - len(self._conn.deny_list)
        elif normalized.startswith("UPDATE favorite_podcasts"):
            canonical_id, non_canonical_ids, canonical_id_check = params
            assert canonical_id == canonical_id_check
            ids_to_repoint = self._repointable_favorite_ids(canonical_id, non_canonical_ids)
            updated = 0
            for row in self._conn.favorites:
                if row["id"] in ids_to_repoint:
                    row["podcast_id"] = canonical_id
                    updated += 1
            self.rowcount = updated
        elif normalized.startswith("DELETE FROM favorite_podcasts"):
            (non_canonical_ids,) = params
            target_ids = set(non_canonical_ids)
            before = len(self._conn.favorites)
            self._conn.favorites = [r for r in self._conn.favorites if r["podcast_id"] not in target_ids]
            self.rowcount = before - len(self._conn.favorites)
        elif normalized.startswith("DELETE FROM podcasts"):
            (non_canonical_ids,) = params
            target_ids = set(non_canonical_ids)
            before = len(self._conn.podcasts)
            self._conn.podcasts = [p for p in self._conn.podcasts if p["id"] not in target_ids]
            self.rowcount = before - len(self._conn.podcasts)
        else:
            self._last_result = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._last_result

    def fetchone(self) -> Any:
        return self._last_result[0] if self._last_result else None

    def _episode_groups(self, key: str, *, podcast_ids: list[int] | None = None) -> list[tuple[Any, ...]]:
        groups: dict[tuple[int, str], list[int]] = {}
        column = "guid" if key == "guid" else "audio_url"
        target_podcast_ids = set(podcast_ids) if podcast_ids is not None else None
        for episode in self._conn.episodes:
            if target_podcast_ids is not None and episode["podcast_id"] not in target_podcast_ids:
                continue
            value = episode.get(column)
            if value:
                groups.setdefault((episode["podcast_id"], value), []).append(episode["id"])
        return [
            (podcast_id, key, value, sorted(ids))
            for (podcast_id, value), ids in groups.items()
            if len(ids) > 1
        ]

    def _podcast_groups(self) -> list[tuple[Any, ...]]:
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for podcast in self._conn.podcasts:
            key = (
                str(podcast["title"]).strip().lower(),
                str(podcast.get("author_name") or "").strip().lower(),
            )
            groups.setdefault(key, []).append(podcast)
        rows: list[tuple[Any, ...]] = []
        for (_title, _author), podcasts in groups.items():
            if len(podcasts) < 2:
                continue
            ids = [p["id"] for p in sorted(podcasts, key=lambda p: p["id"])]
            rows.append((ids[0], tuple(ids[1:])))
        return rows

    def _repointable_appearance_ids(self, canonical_id: int, non_canonical_ids: list[int]) -> set[int]:
        target_ids = set(non_canonical_ids)
        existing = {
            (a["comedian_id"], a["source"])
            for a in self._conn.appearances
            if a["episode_id"] == canonical_id
        }
        chosen: dict[tuple[int, str], int] = {}
        for appearance in sorted(self._conn.appearances, key=lambda a: a["id"]):
            if appearance["episode_id"] not in target_ids:
                continue
            key = (appearance["comedian_id"], appearance["source"])
            if key in existing or key in chosen:
                continue
            chosen[key] = appearance["id"]
        return set(chosen.values())

    def _repointable_comedian_podcast_ids(self, canonical_id: int, non_canonical_ids: list[int]) -> set[int]:
        target_ids = set(non_canonical_ids)
        existing = {
            (r["comedian_id"], r["association_type"], r["source"])
            for r in self._conn.comedian_podcasts
            if r["podcast_id"] == canonical_id
        }
        chosen: dict[tuple[int, str, str], int] = {}
        for row in sorted(self._conn.comedian_podcasts, key=lambda r: r["id"]):
            if row["podcast_id"] not in target_ids:
                continue
            key = (row["comedian_id"], row["association_type"], row["source"])
            if key in existing or key in chosen:
                continue
            chosen[key] = row["id"]
        return set(chosen.values())

    def _repointable_favorite_ids(self, canonical_id: int, non_canonical_ids: list[int]) -> set[int]:
        target_ids = set(non_canonical_ids)
        existing_profiles = {
            r["profile_id"] for r in self._conn.favorites if r["podcast_id"] == canonical_id
        }
        chosen: dict[str, int] = {}
        for row in sorted(self._conn.favorites, key=lambda r: r["id"]):
            if row["podcast_id"] not in target_ids:
                continue
            profile_id = row["profile_id"]
            if profile_id in existing_profiles or profile_id in chosen:
                continue
            chosen[profile_id] = row["id"]
        return set(chosen.values())


class _FakeConn:
    def __init__(
        self,
        *,
        podcasts: list[dict[str, Any]] | None = None,
        episodes: list[dict[str, Any]] | None = None,
        appearances: list[dict[str, Any]] | None = None,
        reviews: list[dict[str, Any]] | None = None,
        comedian_podcasts: list[dict[str, Any]] | None = None,
        candidate_reviews: list[dict[str, Any]] | None = None,
        deny_list: list[dict[str, Any]] | None = None,
        favorites: list[dict[str, Any]] | None = None,
    ) -> None:
        self.podcasts = list(podcasts or [])
        self.episodes = list(episodes or [])
        self.appearances = list(appearances or [])
        self.reviews = list(reviews or [])
        self.comedian_podcasts = list(comedian_podcasts or [])
        self.candidate_reviews = list(candidate_reviews or [])
        self.deny_list = list(deny_list or [])
        self.favorites = list(favorites or [])
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


def _install_conn(monkeypatch, conn: _FakeConn) -> None:
    def _factory(*, autocommit: bool = True) -> _FakeConn:
        conn.autocommit_args.append(autocommit)
        return conn

    monkeypatch.setattr(mod, "get_connection", _factory)


def test_strong_episode_identity_dedupe_repoints_and_absorbs_collisions(monkeypatch):
    conn = _FakeConn(
        episodes=[
            {"id": 10, "podcast_id": 1, "guid": "g1", "audio_url": "a1"},
            {"id": 11, "podcast_id": 1, "guid": "g1", "audio_url": "a1"},
        ],
        appearances=[
            {"id": 1, "episode_id": 10, "comedian_id": 7, "source": "rss"},
            {"id": 2, "episode_id": 11, "comedian_id": 7, "source": "rss"},
            {"id": 3, "episode_id": 11, "comedian_id": 8, "source": "rss"},
        ],
        reviews=[{"id": 1, "episode_id": 11}],
    )
    _install_conn(monkeypatch, conn)

    summary = mod.cleanup_canonical_podcast_duplicates(dry_run=False, confirm=True)

    assert summary.episode_groups_scanned == 1
    assert summary.episodes_deleted == 1
    assert summary.appearances_repointed == 1
    assert summary.appearances_absorbed == 1
    assert summary.reviews_repointed == 1
    assert conn.episodes == [{"id": 10, "podcast_id": 1, "guid": "g1", "audio_url": "a1"}]
    assert {a["episode_id"] for a in conn.appearances} == {10}
    assert {a["comedian_id"] for a in conn.appearances} == {7, 8}
    assert conn.reviews[0]["episode_id"] == 10
    assert conn.commits == 1
    assert conn.rollbacks == 0


def test_podcast_row_dedupe_repoints_relationships_and_absorbs_collisions(monkeypatch):
    conn = _FakeConn(
        podcasts=[
            {"id": 20, "title": "Bad Friends", "author_name": "Bobby Lee & Andrew Santino"},
            {"id": 21, "title": "bad friends", "author_name": "bobby lee & andrew santino"},
        ],
        episodes=[
            {"id": 1, "podcast_id": 20},
            {"id": 2, "podcast_id": 21},
        ],
        comedian_podcasts=[
            {
                "id": 1,
                "podcast_id": 20,
                "comedian_id": 7,
                "association_type": "host",
                "source": "review",
                "review_status": "accepted",
            },
            {
                "id": 2,
                "podcast_id": 21,
                "comedian_id": 7,
                "association_type": "host",
                "source": "review",
                "review_status": "accepted",
            },
            {
                "id": 3,
                "podcast_id": 21,
                "comedian_id": 8,
                "association_type": "host",
                "source": "review",
                "review_status": "accepted",
            },
        ],
        candidate_reviews=[{"id": 1, "podcast_id": 21}],
        deny_list=[
            {"id": 1, "podcast_id": 20},
            {"id": 2, "podcast_id": 21},
        ],
        favorites=[
            {"id": 1, "podcast_id": 20, "profile_id": "u1"},
            {"id": 2, "podcast_id": 21, "profile_id": "u1"},
            {"id": 3, "podcast_id": 21, "profile_id": "u2"},
        ],
    )
    _install_conn(monkeypatch, conn)

    summary = mod.cleanup_canonical_podcast_duplicates(dry_run=False, confirm=True)

    assert summary.podcast_groups_scanned == 1
    assert summary.podcasts_deleted == 1
    assert summary.podcast_episodes_repointed == 1
    assert summary.comedian_podcasts_repointed == 1
    assert summary.comedian_podcasts_absorbed == 1
    assert summary.deny_list_repointed == 0
    assert summary.deny_list_absorbed == 1
    assert summary.favorite_podcasts_repointed == 1
    assert summary.favorite_podcasts_absorbed == 1
    assert conn.podcasts == [{"id": 20, "title": "Bad Friends", "author_name": "Bobby Lee & Andrew Santino"}]
    assert {episode["podcast_id"] for episode in conn.episodes} == {20}
    assert {row["podcast_id"] for row in conn.comedian_podcasts} == {20}
    assert {row["comedian_id"] for row in conn.comedian_podcasts} == {7, 8}
    assert conn.candidate_reviews[0]["podcast_id"] == 20
    assert conn.deny_list == [{"id": 1, "podcast_id": 20}]
    assert {row["profile_id"] for row in conn.favorites} == {"u1", "u2"}
    assert {row["podcast_id"] for row in conn.favorites} == {20}


def test_targeted_podcast_row_dedupe_merges_bonfire_author_drift(monkeypatch):
    conn = _FakeConn(
        podcasts=[
            {"id": 767, "title": "The Bonfire with Big Jay Oakerson and Robert Kelly", "author_name": "SiriusXM"},
            {
                "id": 770,
                "title": "The Bonfire with Big Jay Oakerson and Robert Kelly",
                "author_name": "pangerang pettarani",
            },
        ],
        episodes=[
            {"id": 1, "podcast_id": 767},
            {"id": 2, "podcast_id": 770},
        ],
        comedian_podcasts=[
            {
                "id": 1,
                "podcast_id": 767,
                "comedian_id": 14676,
                "association_type": "host",
                "source": "review",
                "review_status": "accepted",
            },
            {
                "id": 2,
                "podcast_id": 767,
                "comedian_id": 4672,
                "association_type": "host",
                "source": "review",
                "review_status": "accepted",
            },
            {
                "id": 3,
                "podcast_id": 770,
                "comedian_id": 14676,
                "association_type": "host",
                "source": "review",
                "review_status": "accepted",
            },
            {
                "id": 4,
                "podcast_id": 770,
                "comedian_id": 4672,
                "association_type": "host",
                "source": "review",
                "review_status": "accepted",
            },
        ],
    )
    _install_conn(monkeypatch, conn)

    summary = mod.cleanup_canonical_podcast_duplicates(
        dry_run=False,
        confirm=True,
        canonical_podcast_id=767,
        non_canonical_podcast_ids=[770],
    )

    assert summary.podcast_groups_scanned == 1
    assert summary.podcasts_deleted == 1
    assert summary.podcast_episodes_repointed == 1
    assert summary.comedian_podcasts_absorbed == 2
    assert conn.podcasts == [
        {"id": 767, "title": "The Bonfire with Big Jay Oakerson and Robert Kelly", "author_name": "SiriusXM"}
    ]
    assert {episode["podcast_id"] for episode in conn.episodes} == {767}
    assert {row["podcast_id"] for row in conn.comedian_podcasts} == {767}
    assert {row["comedian_id"] for row in conn.comedian_podcasts} == {4672, 14676}
