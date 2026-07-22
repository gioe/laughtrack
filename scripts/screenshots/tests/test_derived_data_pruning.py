from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from scripts.screenshots.cache import prune_derived_data_caches


REPO_ROOT = Path(__file__).resolve().parents[3]
CACHE_PREFIX = "LaughTrack-screenshots-wt-"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _cache_name(worktree: Path) -> str:
    digest = hashlib.sha256(str(worktree.absolute()).encode()).hexdigest()[:12]
    return f"{CACHE_PREFIX}{digest}"


def _make_repo_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.com")
    _git(repo, "config", "user.name", "Derived Data Tests")
    (repo / "tracked.txt").write_text("fixture\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-qm", "fixture")
    linked = tmp_path / "linked worktree"
    _git(repo, "worktree", "add", "-qb", "linked", str(linked))
    return repo, linked


def _cache(root: Path, name: str, content: bytes = b"cache") -> Path:
    path = root / name
    path.mkdir(parents=True)
    (path / "artifact").write_bytes(content)
    return path


def test_prune_preserves_registered_and_explicit_caches_and_removes_orphans(
    tmp_path: Path,
) -> None:
    repo, linked = _make_repo_with_worktree(tmp_path)
    derived_data = tmp_path / "DerivedData"
    primary_cache = _cache(derived_data, _cache_name(repo))
    linked_cache = _cache(derived_data, _cache_name(linked))
    explicit_cache = _cache(derived_data, f"{CACHE_PREFIX}bbbbbbbbbbbb")
    orphan_cache = _cache(derived_data, f"{CACHE_PREFIX}aaaaaaaaaaaa", b"orphan")
    lookalike = _cache(derived_data, f"{CACHE_PREFIX}not-a-hash")
    symlink_target = _cache(tmp_path, "external-cache")
    symlink = derived_data / f"{CACHE_PREFIX}cccccccccccc"
    symlink.symlink_to(symlink_target, target_is_directory=True)

    result = prune_derived_data_caches(
        repo_root=repo,
        derived_data_root=derived_data,
        preserve_paths=[explicit_cache],
    )

    assert result["registered_worktrees"] == 2
    assert result["removed_caches"] == [str(orphan_cache)]
    assert result["bytes_reclaimed"] == len(b"orphan")
    assert primary_cache.is_dir()
    assert linked_cache.is_dir()
    assert explicit_cache.is_dir()
    assert lookalike.is_dir()
    assert symlink.is_symlink()
    assert symlink_target.is_dir()


def test_prune_handles_missing_derived_data_root(tmp_path: Path) -> None:
    repo, _ = _make_repo_with_worktree(tmp_path)

    result = prune_derived_data_caches(
        repo_root=repo,
        derived_data_root=tmp_path / "missing",
    )

    assert result["removed_caches"] == []
    assert result["bytes_reclaimed"] == 0


def test_regenerate_comparisons_prunes_orphaned_derived_data() -> None:
    script = (REPO_ROOT / "scripts" / "screenshots" / "regenerate-comparisons").read_text()

    prune_position = script.index("prune-derived-data")
    capture_position = script.index('echo "Capturing iOS comparison matrix..."')
    assert prune_position < capture_position
    assert 'prune_args=(prune-derived-data --repo-root "$repo_root")' in script
    assert 'prune_args+=(--preserve-path "$LAUGHTRACK_SCREENSHOT_DERIVED_DATA_PATH")' in script
    assert 'python3 "$repo_root/scripts/screenshots/cache.py" "${prune_args[@]}"' in script
