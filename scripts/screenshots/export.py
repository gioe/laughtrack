#!/usr/bin/env python3
"""Collect validated screenshot runs and export storefront-specific projections."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.screenshots.manifest import (
        ContractError,
        load_catalog,
        load_manifest,
        png_dimensions,
        validate_manifest,
    )
except ModuleNotFoundError:  # Direct execution: python scripts/screenshots/export.py
    from manifest import (  # type: ignore[no-redef]
        ContractError,
        load_catalog,
        load_manifest,
        png_dimensions,
        validate_manifest,
    )


PROFILE_LAYOUTS: dict[str, dict[str, str]] = {
    "ios_phone": {
        "platform": "ios",
        "source_directory": "en-US",
        "source_prefix": "iPhone 16 Pro Max-",
        "destination_directory": "en-US",
        "destination_prefix": "iPhone 16 Pro Max-",
    },
    "ios_large_tablet": {
        "platform": "ios",
        "source_directory": "en-US",
        "source_prefix": "iPad Pro 13-inch (M4)-",
        "destination_directory": "en-US",
        "destination_prefix": "iPad Pro 13-inch (M4)-",
    },
    "android_phone": {
        "platform": "android",
        "source_directory": "en-US/images/phoneScreenshots",
        "source_prefix": "",
        "destination_directory": "en-US/images/phoneScreenshots",
        "destination_prefix": "",
    },
    "android_small_tablet": {
        "platform": "android",
        "source_directory": "en-US/images/sevenInchScreenshots",
        "source_prefix": "",
        "destination_directory": "en-US/images/sevenInchScreenshots",
        "destination_prefix": "",
    },
    "android_large_tablet": {
        "platform": "android",
        "source_directory": "en-US/images/tenInchScreenshots",
        "source_prefix": "",
        "destination_directory": "en-US/images/tenInchScreenshots",
        "destination_prefix": "",
    },
}

PROFILE_DIMENSIONS: dict[str, tuple[int, int]] = {
    "ios_phone": (1320, 2868),
    "ios_large_tablet": (2064, 2752),
    "android_phone": (1320, 2868),
    "android_small_tablet": (1200, 2133),
    "android_large_tablet": (1600, 2844),
}

STOREFRONT_SELECTIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "play": {
        "android_phone": (
            "01_NearMe",
            "02_SearchShows",
            "03_SearchComedians",
            "04_SearchClubs",
            "05_ClubDetail",
            "06_ShowDetail",
            "07_ComedianDetail",
            "09_PodcastDetail",
        ),
        "android_small_tablet": (
            "01_NearMe",
            "02_SearchShows",
            "05_ClubDetail",
            "06_ShowDetail",
        ),
        "android_large_tablet": (
            "01_NearMe",
            "02_SearchShows",
            "05_ClubDetail",
            "06_ShowDetail",
        ),
    },
    "app-store": {
        "ios_phone": (
            "01_NearMe",
            "02_SearchShows",
            "03_SearchComedians",
            "04_SearchClubs",
            "05_ClubDetail",
            "06_ShowDetail",
            "07_ComedianDetail",
            "08_SearchPodcasts",
            "09_PodcastDetail",
        ),
        "ios_large_tablet": (
            "01_NearMe",
            "02_SearchShows",
            "03_SearchComedians",
            "04_SearchClubs",
            "05_ClubDetail",
            "06_ShowDetail",
            "07_ComedianDetail",
            "08_SearchPodcasts",
            "09_PodcastDetail",
        ),
    },
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _assert_disjoint(first: Path, second: Path, labels: tuple[str, str]) -> None:
    first = first.resolve()
    second = second.resolve()
    if _is_within(first, second) or _is_within(second, first):
        raise ContractError([f"{labels[0]} and {labels[1]} must not overlap"])


def _hash_files(paths: Sequence[Path]) -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _git_value(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo_root), *args], text=True, stderr=subprocess.DEVNULL).strip()


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


def _capture_profile_errors(
    *,
    source_root: Path,
    profile: Mapping[str, Any],
    platform_profiles: Sequence[Mapping[str, Any]],
    scenario_ids: Sequence[str],
) -> list[str]:
    profile_id = profile["id"]
    layout = PROFILE_LAYOUTS.get(profile_id)
    dimensions = PROFILE_DIMENSIONS.get(profile_id)
    if layout is None or layout["platform"] != profile["platform"] or dimensions is None:
        return [f"no Fastlane layout configured for profile {profile_id}"]

    directory = source_root / layout["source_directory"]
    expected_names = {f"{layout['source_prefix']}{scenario_id}.png" for scenario_id in scenario_ids}
    allowed_names = {
        f"{candidate_layout['source_prefix']}{scenario_id}.png"
        for candidate in platform_profiles
        if (candidate_layout := PROFILE_LAYOUTS.get(candidate["id"])) is not None
        and candidate_layout["source_directory"] == layout["source_directory"]
        for scenario_id in scenario_ids
    }
    actual_names = (
        {path.name for path in directory.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES}
        if directory.is_dir()
        else set()
    )
    errors: list[str] = []
    missing_names = expected_names - actual_names
    unexpected_names = actual_names - allowed_names
    if missing_names or unexpected_names:
        errors.append(
            f"capture directory {directory} is not canonical: "
            f"missing={sorted(missing_names)}, "
            f"unexpected={sorted(unexpected_names)}"
        )

    for name in sorted(expected_names & actual_names):
        path = directory / name
        try:
            actual_dimensions = png_dimensions(path)
        except ContractError as exc:
            errors.extend(exc.errors)
            continue
        if actual_dimensions != dimensions:
            errors.append(
                f"capture image {path} has dimensions {actual_dimensions[0]}x{actual_dimensions[1]}; "
                f"expected {dimensions[0]}x{dimensions[1]} for profile {profile_id}"
            )
    return errors


def validate_capture_profile(
    *,
    profile_id: str,
    source_root: Path,
    catalog_path: Path,
) -> None:
    """Validate one durable Fastlane profile before treating it as resumable."""
    catalog = load_catalog(catalog_path)
    profile = next((item for item in catalog["profiles"] if item["id"] == profile_id), None)
    if profile is None:
        raise ContractError([f"unknown profile: {profile_id}"])
    platform_profiles = [item for item in catalog["profiles"] if item["platform"] == profile["platform"]]
    errors = _capture_profile_errors(
        source_root=source_root.resolve(),
        profile=profile,
        platform_profiles=platform_profiles,
        scenario_ids=[scenario["id"] for scenario in catalog["scenarios"]],
    )
    if errors:
        raise ContractError(errors)


def reusable_capture_profiles(
    *,
    platform: str,
    source_root: Path,
    catalog_path: Path,
) -> tuple[str, ...]:
    """Return complete, dimension-valid profile IDs in canonical catalog order."""
    catalog = load_catalog(catalog_path)
    scenario_ids = [scenario["id"] for scenario in catalog["scenarios"]]
    source_root = source_root.resolve()
    platform_profiles = [profile for profile in catalog["profiles"] if profile["platform"] == platform]
    return tuple(
        profile["id"]
        for profile in platform_profiles
        if not _capture_profile_errors(
            source_root=source_root,
            profile=profile,
            platform_profiles=platform_profiles,
            scenario_ids=scenario_ids,
        )
    )


def collect_run(
    *,
    platform: str,
    source_root: Path,
    run_root: Path,
    catalog_path: Path,
    repo_root: Path,
) -> Path:
    """Normalize a complete Fastlane capture into an isolated validated run."""
    source_root = source_root.resolve()
    run_root = run_root.resolve()
    repo_root = repo_root.resolve()
    _assert_disjoint(source_root, run_root, ("capture source", "run root"))

    catalog = load_catalog(catalog_path)
    profiles = [profile for profile in catalog["profiles"] if profile["platform"] == platform]
    if not profiles:
        raise ContractError([f"catalog has no profiles for platform {platform!r}"])

    scenarios = [scenario["id"] for scenario in catalog["scenarios"]]
    sources: list[tuple[dict[str, Any], str, Path]] = []
    errors: list[str] = []
    for profile in profiles:
        profile_id = profile["id"]
        layout = PROFILE_LAYOUTS.get(profile_id)
        if layout is None or layout["platform"] != platform:
            errors.append(f"no Fastlane layout configured for profile {profile_id}")
            continue
        directory = source_root / layout["source_directory"]
        errors.extend(
            _capture_profile_errors(
                source_root=source_root,
                profile=profile,
                platform_profiles=profiles,
                scenario_ids=scenarios,
            )
        )
        for scenario_id in scenarios:
            sources.append(
                (
                    profile,
                    scenario_id,
                    directory / f"{layout['source_prefix']}{scenario_id}.png",
                )
            )

    if errors:
        raise ContractError(errors)

    source_hashes = _hash_files([source for _, _, source in sources])
    run_root.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{run_root.name}-", dir=run_root.parent))
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    revision = _git_value(repo_root, "rev-parse", "HEAD")
    dirty = bool(_git_value(repo_root, "status", "--porcelain"))
    images = []
    try:
        for profile, scenario_id, source in sources:
            relative_path = Path("images") / profile["id"] / f"{scenario_id}.png"
            destination = staged / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            width, height = png_dimensions(destination)
            images.append(
                {
                    "path": relative_path.as_posix(),
                    "scenario_id": scenario_id,
                    "profile_id": profile["id"],
                    "platform": profile["platform"],
                    "form_factor": profile["form_factor"],
                    "width": width,
                    "height": height,
                    "captured_at": now,
                    "git_revision": revision,
                }
            )
        manifest = {
            "schema_version": 1,
            "status": "completed",
            "run_id": f"{platform}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            "started_at": now,
            "completed_at": now,
            "git_revision": revision,
            "git_dirty": dirty,
            "profiles": [profile["id"] for profile in profiles],
            "images": images,
        }
        validate_manifest(manifest, catalog, repo_root=staged)
        (staged / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if _hash_files([source for _, _, source in sources]) != source_hashes:
            raise ContractError(["capture source changed while collecting the run"])
        _replace_tree(staged, run_root)
    except BaseException:
        if staged.exists():
            shutil.rmtree(staged)
        raise
    return run_root / "manifest.json"


def export_projection(
    *,
    storefront: str,
    manifest_path: Path,
    output_root: Path,
    catalog_path: Path,
    repo_root: Path,
) -> tuple[Path, ...]:
    """Validate a completed run and copy its deterministic storefront projection."""
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    _assert_disjoint(repo_root, output_root, ("raw run", "projection output"))

    catalog = load_catalog(catalog_path)
    manifest = load_manifest(manifest_path)
    validate_manifest(manifest, catalog, repo_root=repo_root)

    selection = STOREFRONT_SELECTIONS[storefront]
    missing_profiles = [profile_id for profile_id in selection if profile_id not in manifest["profiles"]]
    if missing_profiles:
        raise ContractError([f"{storefront} projection requires profiles: {', '.join(missing_profiles)}"])

    images: Mapping[tuple[str, str], Mapping[str, Any]] = {
        (image["profile_id"], image["scenario_id"]): image for image in manifest["images"]
    }
    planned: list[tuple[Path, Path]] = []
    for profile_id, scenario_ids in selection.items():
        layout = PROFILE_LAYOUTS[profile_id]
        for scenario_id in scenario_ids:
            image = images[(profile_id, scenario_id)]
            source = repo_root / image["path"]
            destination = Path(layout["destination_directory"]) / f"{layout['destination_prefix']}{scenario_id}.png"
            planned.append((source, destination))

    source_hashes = _hash_files([source for source, _ in planned])
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{output_root.name}-", dir=output_root.parent))
    try:
        if output_root.exists():
            shutil.copytree(output_root, staged, dirs_exist_ok=True)
        for profile_id in selection:
            directory = staged / PROFILE_LAYOUTS[profile_id]["destination_directory"]
            directory.mkdir(parents=True, exist_ok=True)
            for path in directory.iterdir():
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                    path.unlink()
        for source, relative_destination in planned:
            destination = staged / relative_destination
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        if _hash_files([source for source, _ in planned]) != source_hashes:
            raise ContractError(["raw run changed while exporting the projection"])
        _replace_tree(staged, output_root)
    except BaseException:
        if staged.exists():
            shutil.rmtree(staged)
        raise
    return tuple(output_root / destination for _, destination in planned)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("screenshots/catalog.json"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("platform", choices=("ios", "android"))
    collect_parser.add_argument("--source-root", type=Path, required=True)
    collect_parser.add_argument("--run-root", type=Path, required=True)
    collect_parser.add_argument("--repo-root", type=Path, default=Path.cwd())

    reusable_parser = subparsers.add_parser("reusable-profiles")
    reusable_parser.add_argument("platform", choices=("ios", "android"))
    reusable_parser.add_argument("--source-root", type=Path, required=True)

    profile_parser = subparsers.add_parser("validate-profile")
    profile_parser.add_argument("profile_id", choices=tuple(PROFILE_LAYOUTS))
    profile_parser.add_argument("--source-root", type=Path, required=True)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("storefront", choices=tuple(STOREFRONT_SELECTIONS))
    export_parser.add_argument("manifest", type=Path)
    export_parser.add_argument("--output-root", type=Path, required=True)
    export_parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "collect":
            manifest = collect_run(
                platform=args.platform,
                source_root=args.source_root,
                run_root=args.run_root,
                catalog_path=args.catalog,
                repo_root=args.repo_root,
            )
            print(f"validated run manifest: {manifest}")
        elif args.command == "reusable-profiles":
            profiles = reusable_capture_profiles(
                platform=args.platform,
                source_root=args.source_root,
                catalog_path=args.catalog,
            )
            print("\n".join(profiles))
        elif args.command == "validate-profile":
            validate_capture_profile(
                profile_id=args.profile_id,
                source_root=args.source_root,
                catalog_path=args.catalog,
            )
            print(f"valid capture profile: {args.profile_id}")
        else:
            exported = export_projection(
                storefront=args.storefront,
                manifest_path=args.manifest,
                output_root=args.output_root,
                catalog_path=args.catalog,
                repo_root=args.repo_root,
            )
            print(f"exported {len(exported)} {args.storefront} screenshots")
    except (ContractError, OSError, subprocess.CalledProcessError) as exc:
        errors = exc.errors if isinstance(exc, ContractError) else (str(exc),)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
