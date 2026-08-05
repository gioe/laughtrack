#!/usr/bin/env python3
"""Manage content-addressed native screenshot profile caches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.screenshots.export import PROFILE_LAYOUTS, validate_capture_profile
    from scripts.screenshots.manifest import ContractError, load_catalog
except ModuleNotFoundError:  # Direct execution: python scripts/screenshots/cache.py
    from export import PROFILE_LAYOUTS, validate_capture_profile  # type: ignore[no-redef]
    from manifest import ContractError, load_catalog  # type: ignore[no-redef]


CACHE_SCHEMA_VERSION = 2
CAPTURE_PROVENANCE_SCHEMA_VERSION = 1
PROVENANCE_FILENAME = ".screenshot-cache-provenance.json"
SHARED_INPUTS = (
    "screenshots/catalog.json",
    "scripts/screenshots/fixture_server.py",
    "scripts/screenshots/assets",
)
PLATFORM_ROOTS = {"ios": "ios", "android": "android"}
EXCLUDED_PARTS = {
    ".git",
    ".gradle",
    ".swiftpm",
    "DerivedData",
    "build",
}
EXCLUDED_SUFFIXES = {".md", ".markdown", ".mobileprovision", ".cer"}
FASTLANE_INPUTS = {
    "ios": {"Fastfile", "Snapfile", "SnapshotHelper.swift"},
    "android": {"Fastfile", "Screengrabfile"},
}
SCREENSHOT_DERIVED_DATA_PREFIX = "LaughTrack-screenshots-wt-"
SCREENSHOT_DERIVED_DATA_NAME = re.compile(
    rf"^{re.escape(SCREENSHOT_DERIVED_DATA_PREFIX)}[0-9a-f]{{12}}$"
)
DEFAULT_DERIVED_DATA_ROOT = Path.home() / "Library" / "Developer" / "Xcode" / "DerivedData"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo_root), *args], text=True, stderr=subprocess.DEVNULL
    ).strip()


def _git_paths(repo_root: Path, *args: str) -> set[str]:
    output = subprocess.check_output(
        ["git", "-C", str(repo_root), "ls-files", "-z", *args], stderr=subprocess.DEVNULL
    )
    return {item.decode("utf-8") for item in output.split(b"\0") if item}


def screenshot_derived_data_cache_name(worktree_path: str | os.PathLike[str]) -> str:
    """Return the cache name used by the iOS Fastfile for a worktree path."""
    absolute_path = os.path.abspath(os.fspath(worktree_path))
    digest = hashlib.sha256(os.fsencode(absolute_path)).hexdigest()[:12]
    return f"{SCREENSHOT_DERIVED_DATA_PREFIX}{digest}"


def _registered_worktree_paths(repo_root: Path) -> list[str]:
    output = subprocess.check_output(
        ["git", "-C", str(repo_root), "worktree", "list", "--porcelain", "-z"],
        stderr=subprocess.DEVNULL,
    )
    prefix = b"worktree "
    return [
        os.fsdecode(field[len(prefix) :])
        for field in output.split(b"\0")
        if field.startswith(prefix)
    ]


def _tree_size(path: Path) -> int:
    total = 0
    for root, directories, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        directories[:] = [
            directory
            for directory in directories
            if not (root_path / directory).is_symlink()
        ]
        for filename in files:
            try:
                total += (root_path / filename).stat(follow_symlinks=False).st_size
            except FileNotFoundError:
                continue
    return total


def prune_derived_data_caches(
    *,
    repo_root: Path,
    derived_data_root: Path = DEFAULT_DERIVED_DATA_ROOT,
    preserve_paths: Sequence[Path] = (),
) -> dict[str, Any]:
    """Remove screenshot DerivedData caches that do not belong to registered worktrees."""
    repo_root = Path(os.path.abspath(repo_root))
    derived_data_root = Path(os.path.abspath(derived_data_root))
    protected_names = {
        screenshot_derived_data_cache_name(path)
        for path in _registered_worktree_paths(repo_root)
    }
    protected_paths = {
        os.path.abspath(path)
        for path in preserve_paths
    }
    removed: list[str] = []
    reclaimed = 0
    if derived_data_root.is_dir():
        for candidate in sorted(derived_data_root.iterdir()):
            if (
                not SCREENSHOT_DERIVED_DATA_NAME.fullmatch(candidate.name)
                or candidate.name in protected_names
                or os.path.abspath(candidate) in protected_paths
                or candidate.is_symlink()
                or not candidate.is_dir()
            ):
                continue
            reclaimed += _tree_size(candidate)
            shutil.rmtree(candidate)
            removed.append(str(candidate))
    return {
        "derived_data_root": str(derived_data_root),
        "registered_worktrees": len(protected_names),
        "removed_caches": removed,
        "bytes_reclaimed": reclaimed,
    }


def _is_render_input(path: str, platform: str) -> bool:
    candidate = Path(path)
    if any(path == shared or path.startswith(f"{shared}/") for shared in SHARED_INPUTS):
        return True
    if not candidate.parts or candidate.parts[0] != PLATFORM_ROOTS[platform]:
        return False
    excluded_outputs = (
        f"{platform}/fastlane/screenshots/",
        f"{platform}/fastlane/test_output/",
        f"{platform}/fastlane/metadata/",
    )
    if path.startswith(excluded_outputs):
        return False
    if candidate.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if any(part in EXCLUDED_PARTS for part in candidate.parts[1:]):
        return False
    if len(candidate.parts) > 1 and candidate.parts[1] == "fastlane":
        return candidate.name in FASTLANE_INPUTS[platform] or candidate.suffix == ".rb"
    return True


def render_inputs(repo_root: Path, platform: str) -> list[dict[str, Any]]:
    """Describe tracked, untracked, modified, and deleted render inputs."""
    if platform not in PLATFORM_ROOTS:
        raise ContractError([f"unsupported platform: {platform}"])
    candidates = _git_paths(repo_root, "--", PLATFORM_ROOTS[platform], *SHARED_INPUTS)
    candidates |= _git_paths(
        repo_root,
        "--others",
        "--exclude-standard",
        "--",
        PLATFORM_ROOTS[platform],
        *SHARED_INPUTS,
    )
    inputs: list[dict[str, Any]] = []
    for relative in sorted(path for path in candidates if _is_render_input(path, platform)):
        path = repo_root / relative
        if path.is_symlink():
            data = os.fsencode(os.readlink(path))
            inputs.append(
                {
                    "path": relative,
                    "state": "symlink",
                    "mode": "120000",
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        elif path.is_file():
            data = path.read_bytes()
            executable = bool(path.stat().st_mode & 0o111)
            inputs.append(
                {
                    "path": relative,
                    "state": "present",
                    "mode": "100755" if executable else "100644",
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        else:
            inputs.append({"path": relative, "state": "deleted"})
    return inputs


def profile_cache_key(
    *,
    repo_root: Path,
    platform: str,
    profile_id: str,
    profile_config: Mapping[str, Any],
    native_environment: Mapping[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    inputs = render_inputs(repo_root.resolve(), platform)
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "platform": platform,
        "profile_id": profile_id,
        "profile_config": profile_config,
        "native_environment": native_environment,
        "inputs": inputs,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), inputs


def _profile_configurations(raw: str, profile_ids: Sequence[str]) -> dict[str, Mapping[str, Any]]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContractError([f"invalid profile config JSON: {exc}"]) from exc
    if isinstance(value, dict) and isinstance(value.get("profiles"), dict):
        value = value["profiles"]
    if isinstance(value, list):
        value = {item.get("id"): item for item in value if isinstance(item, dict) and item.get("id")}
    if not isinstance(value, dict):
        raise ContractError(["profile config JSON must map profile IDs to configuration objects"])
    missing = [profile_id for profile_id in profile_ids if not isinstance(value.get(profile_id), dict)]
    if missing:
        raise ContractError([f"profile config missing object(s): {', '.join(missing)}"])
    return {profile_id: value[profile_id] for profile_id in profile_ids}


def _native_environment(raw: str) -> Mapping[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContractError([f"invalid native environment JSON: {exc}"]) from exc
    if not isinstance(value, dict) or not value:
        raise ContractError(["native environment JSON must be a non-empty object"])
    return value


def _profile_files(profile_id: str, catalog_path: Path, root: Path) -> list[tuple[str, Path]]:
    catalog = load_catalog(catalog_path)
    layout = PROFILE_LAYOUTS[profile_id]
    return [
        (
            scenario["id"],
            root
            / layout["source_directory"]
            / f"{layout['source_prefix']}{scenario['id']}.png",
        )
        for scenario in catalog["scenarios"]
    ]


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _replace_tree(staged: Path, destination: Path) -> None:
    backup = Path(tempfile.mkdtemp(prefix=f".{destination.name}-backup-", dir=destination.parent))
    backup.rmdir()
    if destination.exists():
        os.replace(destination, backup)
    try:
        os.replace(staged, destination)
    except BaseException:
        if backup.exists() and not destination.exists():
            os.replace(backup, destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def _load_provenance(capture_root: Path) -> dict[str, Any]:
    path = capture_root / PROVENANCE_FILENAME
    if not path.is_file():
        return {"schema_version": CAPTURE_PROVENANCE_SCHEMA_VERSION, "profiles": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"schema_version": CAPTURE_PROVENANCE_SCHEMA_VERSION, "profiles": {}}
    if value.get("schema_version") != CAPTURE_PROVENANCE_SCHEMA_VERSION or not isinstance(
        value.get("profiles"), dict
    ):
        return {"schema_version": CAPTURE_PROVENANCE_SCHEMA_VERSION, "profiles": {}}
    return value


def _record_provenance(capture_root: Path, profile_id: str, record: Mapping[str, Any]) -> Path:
    provenance = _load_provenance(capture_root)
    provenance["profiles"][profile_id] = dict(record)
    provenance["updated_at"] = _now()
    path = capture_root / PROVENANCE_FILENAME
    _write_json_atomic(path, provenance)
    return path


def _cache_entry(cache_root: Path, platform: str, profile_id: str, key: str) -> Path:
    return cache_root.resolve() / platform / profile_id / key


def _validated_entry(
    entry: Path,
    profile_id: str,
    catalog_path: Path,
    *,
    profile_config: Mapping[str, Any],
    native_environment: Mapping[str, Any],
    inputs: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    metadata_path = entry / "metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("schema_version") != CACHE_SCHEMA_VERSION
            or metadata.get("profile_id") != profile_id
            or metadata.get("platform") != PROFILE_LAYOUTS[profile_id]["platform"]
            or metadata.get("cache_key") != entry.name
            or len(entry.name) != 64
            or any(character not in "0123456789abcdef" for character in entry.name)
            or not _valid_timestamp(metadata.get("captured_at"))
            or not isinstance(metadata.get("capture_git_revision"), str)
            or len(metadata["capture_git_revision"]) != 40
            or any(
                character not in "0123456789abcdef"
                for character in metadata["capture_git_revision"]
            )
            or not isinstance(metadata.get("capture_git_dirty"), bool)
            or metadata.get("profile_config") != profile_config
            or metadata.get("native_environment") != native_environment
            or metadata.get("inputs") != list(inputs)
            or not isinstance(metadata.get("images"), list)
        ):
            return None
        expected = _profile_files(profile_id, catalog_path, entry / "capture")
        images = {
            image["scenario_id"]: image
            for image in metadata["images"]
            if isinstance(image, dict)
            and isinstance(image.get("scenario_id"), str)
            and isinstance(image.get("sha256"), str)
            and len(image["sha256"]) == 64
            and isinstance(image.get("path"), str)
            and isinstance(image.get("size"), int)
        }
        if len(images) != len(expected):
            return None
        for scenario_id, path in expected:
            image = images.get(scenario_id)
            if (
                image is None
                or image["path"] != path.relative_to(entry).as_posix()
                or not path.is_file()
                or path.stat().st_size != image["size"]
                or hashlib.sha256(path.read_bytes()).hexdigest() != image["sha256"]
            ):
                return None
        validate_capture_profile(profile_id=profile_id, source_root=entry / "capture", catalog_path=catalog_path)
    except (ContractError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return metadata


def _materialize(entry: Path, profile_id: str, catalog_path: Path, capture_root: Path) -> None:
    planned = _profile_files(profile_id, catalog_path, entry / "capture")
    staged: list[tuple[Path, Path]] = []
    try:
        for _, source in planned:
            destination = capture_root / source.relative_to(entry / "capture")
            destination.parent.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=f".{destination.name}-", dir=destination.parent)
            os.close(descriptor)
            temporary = Path(name)
            shutil.copy2(source, temporary)
            staged.append((temporary, destination))
        for temporary, destination in staged:
            os.replace(temporary, destination)
        validate_capture_profile(profile_id=profile_id, source_root=capture_root, catalog_path=catalog_path)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def plan_cache(
    *,
    platform: str,
    capture_root: Path,
    cache_root: Path,
    repo_root: Path,
    catalog_path: Path,
    profile_configs: Mapping[str, Mapping[str, Any]],
    native_environment: Mapping[str, Any],
    force_fresh: bool = False,
) -> dict[str, Any]:
    catalog = load_catalog(catalog_path)
    profile_ids = [profile["id"] for profile in catalog["profiles"] if profile["platform"] == platform]
    profiles: list[dict[str, str]] = []
    reused: list[str] = []
    pending: list[str] = []
    for profile_id in profile_ids:
        key, inputs = profile_cache_key(
            repo_root=repo_root,
            platform=platform,
            profile_id=profile_id,
            profile_config=profile_configs[profile_id],
            native_environment=native_environment,
        )
        entry = _cache_entry(cache_root, platform, profile_id, key)
        metadata = (
            None
            if force_fresh
            else _validated_entry(
                entry,
                profile_id,
                catalog_path,
                profile_config=profile_configs[profile_id],
                native_environment=native_environment,
                inputs=inputs,
            )
        )
        if metadata is None:
            status = "capture"
            pending.append(profile_id)
        else:
            _materialize(entry, profile_id, catalog_path, capture_root)
            materialized_at = _now()
            _record_provenance(
                capture_root,
                profile_id,
                {
                    "source": "cache",
                    "cache_key": key,
                    "captured_at": metadata["captured_at"],
                    "capture_git_revision": metadata["capture_git_revision"],
                    "capture_git_dirty": metadata["capture_git_dirty"],
                    "materialized_at": materialized_at,
                },
            )
            status = "reused"
            reused.append(profile_id)
        profiles.append({"profile_id": profile_id, "key": key, "status": status})
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "platform": platform,
        "force_fresh": force_fresh,
        "reused_profiles": reused,
        "pending_profiles": pending,
        "profile_fingerprints": {profile["profile_id"]: profile["key"] for profile in profiles},
        "profiles": profiles,
        "provenance_path": str(capture_root / PROVENANCE_FILENAME),
    }


def store_profile(
    *,
    platform: str,
    profile_id: str,
    capture_root: Path,
    cache_root: Path,
    repo_root: Path,
    catalog_path: Path,
    profile_config: Mapping[str, Any],
    native_environment: Mapping[str, Any],
    expected_key: str,
) -> dict[str, Any]:
    layout = PROFILE_LAYOUTS.get(profile_id)
    if layout is None or layout["platform"] != platform:
        raise ContractError([f"profile {profile_id} does not belong to {platform}"])
    validate_capture_profile(profile_id=profile_id, source_root=capture_root, catalog_path=catalog_path)
    key, inputs = profile_cache_key(
        repo_root=repo_root,
        platform=platform,
        profile_id=profile_id,
        profile_config=profile_config,
        native_environment=native_environment,
    )
    if key != expected_key:
        raise ContractError(
            [
                f"render inputs changed while capturing {profile_id}; "
                "discard this capture and retry"
            ]
        )
    entry = _cache_entry(cache_root, platform, profile_id, key)
    entry.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{key}-", dir=entry.parent))
    captured_at = _now()
    revision = _git(repo_root, "rev-parse", "HEAD")
    dirty = bool(_git(repo_root, "status", "--porcelain"))
    images: list[dict[str, Any]] = []
    try:
        for scenario_id, source in _profile_files(profile_id, catalog_path, capture_root):
            destination = staged / "capture" / source.relative_to(capture_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            images.append(
                {
                    "scenario_id": scenario_id,
                    "path": destination.relative_to(staged).as_posix(),
                    "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                    "size": destination.stat().st_size,
                }
            )
        final_key, final_inputs = profile_cache_key(
            repo_root=repo_root,
            platform=platform,
            profile_id=profile_id,
            profile_config=profile_config,
            native_environment=native_environment,
        )
        if final_key != expected_key or final_inputs != inputs:
            raise ContractError(
                [
                    f"render inputs changed while storing {profile_id}; "
                    "discard this capture and retry"
                ]
            )
        metadata = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "platform": platform,
            "profile_id": profile_id,
            "cache_key": key,
            "profile_config": profile_config,
            "native_environment": native_environment,
            "captured_at": captured_at,
            "capture_git_revision": revision,
            "capture_git_dirty": dirty,
            "inputs": inputs,
            "images": images,
        }
        _write_json_atomic(staged / "metadata.json", metadata)
        _replace_tree(staged, entry)
        if (
            _validated_entry(
                entry,
                profile_id,
                catalog_path,
                profile_config=profile_config,
                native_environment=native_environment,
                inputs=inputs,
            )
            is None
        ):
            raise ContractError([f"stored cache entry failed validation: {profile_id}"])
    except BaseException:
        if staged.exists():
            shutil.rmtree(staged)
        raise
    materialized_at = _now()
    provenance_path = _record_provenance(
        capture_root,
        profile_id,
        {
            "source": "capture",
            "cache_key": key,
            "captured_at": captured_at,
            "capture_git_revision": revision,
            "capture_git_dirty": dirty,
            "materialized_at": materialized_at,
        },
    )
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "platform": platform,
        "profile_id": profile_id,
        "key": key,
        "cache_entry": str(entry),
        "provenance_path": str(provenance_path),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage content-addressed native screenshot profile caches.")
    parser.add_argument("--catalog", type=Path, default=Path("screenshots/catalog.json"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    prune_parser = subparsers.add_parser("prune-derived-data")
    prune_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    prune_parser.add_argument(
        "--derived-data-root",
        type=Path,
        default=DEFAULT_DERIVED_DATA_ROOT,
    )
    prune_parser.add_argument("--preserve-path", type=Path, action="append", default=[])
    for command in ("plan", "store-profile"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("platform", choices=tuple(PLATFORM_ROOTS))
        command_parser.add_argument("--capture-root", type=Path, required=True)
        command_parser.add_argument("--cache-root", type=Path, required=True)
        command_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
        command_parser.add_argument("--profile-config-json", required=True)
        command_parser.add_argument("--native-environment-json", required=True)
        if command == "plan":
            command_parser.add_argument("--force-fresh", action="store_true")
        else:
            command_parser.add_argument("profile_id", choices=tuple(PROFILE_LAYOUTS))
            command_parser.add_argument("--expected-key", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "prune-derived-data":
            result = prune_derived_data_caches(
                repo_root=args.repo_root,
                derived_data_root=args.derived_data_root,
                preserve_paths=args.preserve_path,
            )
        else:
            catalog = load_catalog(args.catalog)
            profile_ids = [
                p["id"] for p in catalog["profiles"] if p["platform"] == args.platform
            ]
            configs = _profile_configurations(args.profile_config_json, profile_ids)
            native_environment = _native_environment(args.native_environment_json)
        if args.command == "plan":
            result = plan_cache(
                platform=args.platform,
                capture_root=args.capture_root,
                cache_root=args.cache_root,
                repo_root=args.repo_root,
                catalog_path=args.catalog,
                profile_configs=configs,
                native_environment=native_environment,
                force_fresh=args.force_fresh,
            )
        elif args.command == "store-profile":
            result = store_profile(
                platform=args.platform,
                profile_id=args.profile_id,
                capture_root=args.capture_root,
                cache_root=args.cache_root,
                repo_root=args.repo_root,
                catalog_path=args.catalog,
                profile_config=configs[args.profile_id],
                native_environment=native_environment,
                expected_key=args.expected_key,
            )
        print(json.dumps(result, sort_keys=True))
    except (ContractError, OSError, subprocess.CalledProcessError) as exc:
        errors = exc.errors if isinstance(exc, ContractError) else (str(exc),)
        print(json.dumps({"error": "; ".join(errors)}, sort_keys=True), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
