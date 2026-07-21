#!/usr/bin/env python3
"""Validate the canonical mobile screenshot catalog and completed-run manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


CATALOG_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 2
SCENARIO_IDS = (
    "01_NearMe",
    "02_SearchShows",
    "03_SearchComedians",
    "04_SearchClubs",
    "05_ClubDetail",
    "06_ShowDetail",
    "07_ComedianDetail",
    "08_SearchPodcasts",
    "09_PodcastDetail",
    "11_Profile",
    "13_Onboarding",
    "14_NowPlaying",
    "15_AuthenticatedFavorites",
    "16_AuthenticatedProfile",
    "17_AuthenticatedNotifications",
    "18_AuthPrompt",
    "19_FirstEntryAuthChoice",
)
PROFILE_IDS = (
    "ios_phone",
    "ios_large_tablet",
    "android_phone",
    "android_small_tablet",
    "android_large_tablet",
)
PLATFORMS = {"ios", "android"}
FORM_FACTORS = {"phone", "small_tablet", "large_tablet"}
GIT_REVISION_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
FIXTURE_CAPTURE_CONTEXTS: Mapping[str, Mapping[str, Any]] = {
    "05_ClubDetail": {
        "screen": "club_detail",
        "source_scenario_id": "04_SearchClubs",
        "query": "The Comedy Store",
        "selection": "first_result",
    },
    "06_ShowDetail": {
        "screen": "show_detail",
        "source_scenario_id": "05_ClubDetail",
        "selection": "first_upcoming_show",
    },
    "07_ComedianDetail": {
        "screen": "comedian_detail",
        "source_scenario_id": "03_SearchComedians",
        "query": "Ali Wong",
        "selection": "first_result",
    },
    "09_PodcastDetail": {
        "screen": "podcast_detail",
        "source_scenario_id": "08_SearchPodcasts",
        "query": "The Joe Rogan Experience",
        "selection": "first_result",
    },
    "15_AuthenticatedFavorites": {
        "screen": "favorites",
        "auth_state": "authenticated",
        "persona": "screenshot-persona",
        "saved_categories": ["shows", "comedians", "clubs", "podcasts"],
        "saved_entities": {
            "shows": ["Taylor Tomlinson Live", "Sam Jay Live"],
            "comedians": ["Taylor Tomlinson", "Sam Jay"],
            "clubs": ["The Comedy Cellar"],
            "podcasts": ["Good One: A Podcast About Jokes"],
        },
    },
    "18_AuthPrompt": {
        "screen": "auth_prompt",
        "auth_state": "guest",
        "presentation": "in_app_modal",
        "background_screen": "profile",
        "trigger": "deterministic_test_seam",
    },
}


def content_fixture_fingerprint(catalog: Mapping[str, Any]) -> str:
    fixture = catalog.get("content_fixture")
    encoded = json.dumps(fixture, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class ContractError(ValueError):
    """A catalog or manifest failed contract validation."""

    def __init__(self, errors: Iterable[str]):
        self.errors = tuple(errors)
        super().__init__("\n".join(self.errors))


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError([f"{path}: cannot read JSON: {exc}"]) from exc


def load_catalog(path: Path | str) -> dict[str, Any]:
    """Load and validate a screenshot catalog."""
    catalog = _read_json(Path(path))
    validate_catalog(catalog)
    return catalog


def load_manifest(path: Path | str) -> dict[str, Any]:
    """Load a screenshot manifest without applying repository-specific checks."""
    manifest = _read_json(Path(path))
    if not isinstance(manifest, dict):
        raise ContractError(["manifest: root must be an object"])
    return manifest


def validate_catalog(catalog: Any) -> None:
    """Validate the checked-in catalog's stable scenarios and capture profiles."""
    errors: list[str] = []
    if not isinstance(catalog, dict):
        raise ContractError(["catalog: root must be an object"])

    if catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        errors.append(f"catalog.schema_version must be {CATALOG_SCHEMA_VERSION}")

    fixture = catalog.get("content_fixture")
    if not isinstance(fixture, dict) or not fixture:
        errors.append("catalog.content_fixture must be a non-empty object")
    else:
        try:
            from scripts.screenshots.fixture_server import CONTENT_FIXTURE
        except ModuleNotFoundError:
            from fixture_server import CONTENT_FIXTURE  # type: ignore[no-redef]
        if fixture != CONTENT_FIXTURE:
            errors.append("catalog.content_fixture must match the shared fixture server contract")

    scenarios = catalog.get("scenarios")
    if not isinstance(scenarios, list):
        errors.append("catalog.scenarios must be an array")
    else:
        actual_ids = [item.get("id") if isinstance(item, dict) else None for item in scenarios]
        if actual_ids != list(SCENARIO_IDS):
            errors.append(
                "catalog.scenarios must contain the canonical IDs in order: "
                + ", ".join(SCENARIO_IDS)
            )
        for index, scenario in enumerate(scenarios):
            prefix = f"catalog.scenarios[{index}]"
            if not isinstance(scenario, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for key in ("locale", "timezone"):
                if not isinstance(scenario.get(key), str) or not scenario[key].strip():
                    errors.append(f"{prefix}.{key} must be a non-empty string")
            context = scenario.get("capture_context")
            if not isinstance(context, dict) or not context:
                errors.append(f"{prefix}.capture_context must be a non-empty object")
            expected_context = FIXTURE_CAPTURE_CONTEXTS.get(scenario.get("id"))
            if expected_context is not None and context != expected_context:
                errors.append(
                    f"{prefix}.capture_context must match the cross-platform fixture contract"
                )

    profiles = catalog.get("profiles")
    if not isinstance(profiles, list):
        errors.append("catalog.profiles must be an array")
    else:
        actual_ids = [item.get("id") if isinstance(item, dict) else None for item in profiles]
        if actual_ids != list(PROFILE_IDS):
            errors.append(
                "catalog.profiles must contain the canonical profile IDs in order: "
                + ", ".join(PROFILE_IDS)
            )
        seen_pairs: set[tuple[Any, Any]] = set()
        for index, profile in enumerate(profiles):
            prefix = f"catalog.profiles[{index}]"
            if not isinstance(profile, dict):
                errors.append(f"{prefix} must be an object")
                continue
            platform = profile.get("platform")
            form_factor = profile.get("form_factor")
            if platform not in PLATFORMS:
                errors.append(f"{prefix}.platform must be one of {sorted(PLATFORMS)}")
            if form_factor not in FORM_FACTORS:
                errors.append(f"{prefix}.form_factor must be one of {sorted(FORM_FACTORS)}")
            pair = (platform, form_factor)
            if pair in seen_pairs:
                errors.append(f"{prefix} duplicates platform/form_factor {pair}")
            seen_pairs.add(pair)

    if errors:
        raise ContractError(errors)


def expected_capture_keys(
    catalog: Mapping[str, Any], profile_ids: Sequence[str]
) -> tuple[tuple[str, str], ...]:
    """Return the required (profile, scenario) keys in canonical capture order."""
    scenarios = [scenario["id"] for scenario in catalog["scenarios"]]
    selected = set(profile_ids)
    return tuple(
        (profile["id"], scenario_id)
        for profile in catalog["profiles"]
        if profile["id"] in selected
        for scenario_id in scenarios
    )


def png_dimensions(path: Path | str) -> tuple[int, int]:
    """Read dimensions from the PNG signature and IHDR chunk."""
    image_path = Path(path)
    try:
        header = image_path.read_bytes()[:24]
    except OSError as exc:
        raise ContractError([f"{image_path}: cannot read PNG: {exc}"]) from exc
    if len(header) < 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise ContractError([f"{image_path}: not a readable PNG with an IHDR chunk"])
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        raise ContractError([f"{image_path}: PNG dimensions must be positive"])
    return width, height


def _parse_timestamp(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str):
        errors.append(f"{field} must be an RFC 3339 timestamp")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be an RFC 3339 timestamp")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(f"{field} must include a timezone offset")
        return None
    return parsed


def _is_git_revision(value: Any) -> bool:
    return isinstance(value, str) and GIT_REVISION_RE.fullmatch(value) is not None


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def validate_manifest(
    manifest: Any,
    catalog: Mapping[str, Any],
    *,
    repo_root: Path | str,
    fresh_since: datetime | None = None,
    require_files: bool = True,
) -> None:
    """Validate a completed run, including exact corpus coverage and PNG metadata."""
    validate_catalog(catalog)
    errors: list[str] = []
    if not isinstance(manifest, dict):
        raise ContractError(["manifest: root must be an object"])

    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append(f"manifest.schema_version must be {MANIFEST_SCHEMA_VERSION}")
    if manifest.get("status") != "completed":
        errors.append("manifest.status must be 'completed'")
    if not isinstance(manifest.get("run_id"), str) or not manifest["run_id"].strip():
        errors.append("manifest.run_id must be a non-empty string")

    revision = manifest.get("git_revision")
    if not _is_git_revision(revision):
        errors.append("manifest.git_revision must be a 40-character lowercase Git SHA")

    expected_fixture_fingerprint = content_fixture_fingerprint(catalog)
    if manifest.get("content_fixture_fingerprint") != expected_fixture_fingerprint:
        errors.append("manifest.content_fixture_fingerprint must match the catalog content fixture")
    if not isinstance(manifest.get("git_dirty"), bool):
        errors.append("manifest.git_dirty must be a boolean")

    started_at = _parse_timestamp(manifest.get("started_at"), "manifest.started_at", errors)
    completed_at = _parse_timestamp(manifest.get("completed_at"), "manifest.completed_at", errors)
    if started_at and completed_at and completed_at < started_at:
        errors.append("manifest.completed_at must not precede manifest.started_at")
    if fresh_since is not None:
        if fresh_since.tzinfo is None or fresh_since.utcoffset() is None:
            raise ValueError("fresh_since must be timezone-aware")
        if started_at and started_at < fresh_since:
            errors.append("manifest.started_at predates the required freshness boundary")

    profile_ids = manifest.get("profiles")
    catalog_profiles = {profile["id"]: profile for profile in catalog["profiles"]}
    if not isinstance(profile_ids, list) or not profile_ids:
        errors.append("manifest.profiles must be a non-empty array")
        selected_profiles: list[str] = []
    else:
        raw_profiles = profile_ids
        if any(not isinstance(profile_id, str) for profile_id in raw_profiles):
            errors.append("manifest.profiles entries must be strings")
        selected_profiles = [profile_id for profile_id in raw_profiles if isinstance(profile_id, str)]
        if len(set(selected_profiles)) != len(selected_profiles):
            errors.append("manifest.profiles must not contain duplicates")
        unknown = [profile_id for profile_id in selected_profiles if profile_id not in catalog_profiles]
        if unknown:
            errors.append("manifest.profiles contains unknown profiles: " + ", ".join(map(str, unknown)))
        canonical_selected = [
            profile["id"] for profile in catalog["profiles"] if profile["id"] in selected_profiles
        ]
        if not unknown and selected_profiles != canonical_selected:
            errors.append("manifest.profiles must follow catalog order")
        selected_platforms = {
            catalog_profiles[profile_id]["platform"]
            for profile_id in selected_profiles
            if profile_id in catalog_profiles
        }
        complete_platform_profiles = [
            profile["id"]
            for profile in catalog["profiles"]
            if profile["platform"] in selected_platforms
        ]
        if not unknown and selected_profiles != complete_platform_profiles:
            errors.append(
                "manifest.profiles must include every form factor for each selected platform"
            )

    images = manifest.get("images")
    if not isinstance(images, list):
        errors.append("manifest.images must be an array")
        images = []

    root = Path(repo_root).resolve()
    actual_keys: list[tuple[Any, Any]] = []
    seen_paths: set[str] = set()
    provenance_by_profile: dict[str, set[tuple[Any, ...]]] = {}
    for index, image in enumerate(images):
        prefix = f"manifest.images[{index}]"
        if not isinstance(image, dict):
            errors.append(f"{prefix} must be an object")
            continue

        raw_profile_id = image.get("profile_id")
        raw_scenario_id = image.get("scenario_id")
        profile_id = raw_profile_id if isinstance(raw_profile_id, str) else None
        scenario_id = raw_scenario_id if isinstance(raw_scenario_id, str) else None
        actual_keys.append((profile_id, scenario_id))
        if profile_id is None:
            errors.append(f"{prefix}.profile_id must be a string")
        profile = catalog_profiles.get(profile_id)
        if profile is None:
            errors.append(f"{prefix}.profile_id is not in the catalog")
        else:
            if image.get("platform") != profile["platform"]:
                errors.append(f"{prefix}.platform does not match profile {profile_id}")
            if image.get("form_factor") != profile["form_factor"]:
                errors.append(f"{prefix}.form_factor does not match profile {profile_id}")
        if scenario_id is None:
            errors.append(f"{prefix}.scenario_id must be a string")
        elif scenario_id not in SCENARIO_IDS:
            errors.append(f"{prefix}.scenario_id is not canonical")

        width = image.get("width")
        height = image.get("height")
        if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
            errors.append(f"{prefix}.width must be a positive integer")
        if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
            errors.append(f"{prefix}.height must be a positive integer")
        if isinstance(width, int) and isinstance(height, int) and height <= width:
            errors.append(f"{prefix} must record portrait dimensions")

        captured_at = _parse_timestamp(image.get("captured_at"), f"{prefix}.captured_at", errors)
        materialized_at = _parse_timestamp(
            image.get("materialized_at"), f"{prefix}.materialized_at", errors
        )
        if captured_at and materialized_at and captured_at > materialized_at:
            errors.append(f"{prefix}.captured_at follows materialized_at")
        if materialized_at and started_at and materialized_at < started_at:
            errors.append(f"{prefix}.materialized_at precedes manifest.started_at")
        if materialized_at and completed_at and materialized_at > completed_at:
            errors.append(f"{prefix}.materialized_at follows manifest.completed_at")
        if materialized_at and fresh_since and materialized_at < fresh_since:
            errors.append(f"{prefix}.materialized_at predates the required freshness boundary")

        capture_revision = image.get("capture_git_revision")
        if not _is_git_revision(capture_revision):
            errors.append(
                f"{prefix}.capture_git_revision must be a 40-character lowercase Git SHA"
            )
        capture_dirty = image.get("capture_git_dirty")
        if not isinstance(capture_dirty, bool):
            errors.append(f"{prefix}.capture_git_dirty must be a boolean")
        provenance = image.get("provenance")
        if provenance not in {"capture", "cache"}:
            errors.append(f"{prefix}.provenance must be 'capture' or 'cache'")
        cache_key = image.get("cache_key")
        if not _is_sha256(cache_key):
            errors.append(f"{prefix}.cache_key must be a 64-character lowercase SHA-256")
        if (
            provenance == "capture"
            and _is_git_revision(capture_revision)
            and _is_git_revision(revision)
            and capture_revision != revision
        ):
            errors.append(f"{prefix}.capture_git_revision does not match the run revision")
        if profile_id is not None:
            provenance_by_profile.setdefault(profile_id, set()).add(
                (
                    image.get("captured_at"),
                    image.get("materialized_at"),
                    capture_revision,
                    capture_dirty,
                    provenance,
                    cache_key,
                )
            )

        relative_path = image.get("path")
        if not isinstance(relative_path, str) or not relative_path:
            errors.append(f"{prefix}.path must be a non-empty repository-relative path")
            continue
        pure_path = PurePosixPath(relative_path)
        if pure_path.is_absolute() or ".." in pure_path.parts or "\\" in relative_path:
            errors.append(f"{prefix}.path must be a safe repository-relative POSIX path")
            continue
        if relative_path in seen_paths:
            errors.append(f"{prefix}.path duplicates {relative_path}")
        seen_paths.add(relative_path)
        if isinstance(scenario_id, str) and pure_path.name != f"{scenario_id}.png":
            errors.append(f"{prefix}.path filename must be {scenario_id}.png")

        if require_files:
            image_path = (root / relative_path).resolve()
            try:
                image_path.relative_to(root)
            except ValueError:
                errors.append(f"{prefix}.path resolves outside repo_root")
                continue
            if not image_path.is_file():
                errors.append(f"{prefix}.path does not name a regular file")
                continue
            try:
                png_width, png_height = png_dimensions(image_path)
            except ContractError as exc:
                errors.extend(f"{prefix}: {error}" for error in exc.errors)
            else:
                if width != png_width or height != png_height:
                    errors.append(
                        f"{prefix} dimensions {width}x{height} do not match PNG "
                        f"{png_width}x{png_height}"
                    )

    for profile_id, records in provenance_by_profile.items():
        if len(records) > 1:
            errors.append(
                f"manifest.images provenance must be consistent within profile {profile_id}"
            )

    if all(profile_id in catalog_profiles for profile_id in selected_profiles):
        expected_keys = expected_capture_keys(catalog, selected_profiles)
        if tuple(actual_keys) != expected_keys:
            expected_set = set(expected_keys)
            actual_set = set(actual_keys)
            missing = sorted(expected_set - actual_set, key=repr)
            unexpected = sorted(actual_set - expected_set, key=repr)
            duplicates = sorted(
                {key for key in actual_keys if actual_keys.count(key) > 1}, key=repr
            )
            detail = []
            if missing:
                detail.append(f"missing={missing}")
            if unexpected:
                detail.append(f"unexpected={unexpected}")
            if duplicates:
                detail.append(f"duplicates={duplicates}")
            if not detail:
                detail.append("entries are not in canonical order")
            errors.append("manifest.images must exactly cover selected profiles: " + "; ".join(detail))

    if errors:
        raise ContractError(errors)


def _parse_fresh_since(value: str) -> datetime:
    errors: list[str] = []
    parsed = _parse_timestamp(value, "--fresh-since", errors)
    if errors or parsed is None:
        raise argparse.ArgumentTypeError(errors[0])
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate canonical mobile screenshot catalog and run manifests."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    catalog_parser = subparsers.add_parser("validate-catalog")
    catalog_parser.add_argument("--catalog", type=Path, default=Path("screenshots/catalog.json"))

    run_parser = subparsers.add_parser("validate-run")
    run_parser.add_argument("manifest", type=Path)
    run_parser.add_argument("--catalog", type=Path, default=Path("screenshots/catalog.json"))
    run_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    run_parser.add_argument("--fresh-since", type=_parse_fresh_since)

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--catalog", type=Path, default=Path("screenshots/catalog.json"))
    plan_parser.add_argument("--profile", action="append", dest="profiles", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        catalog = load_catalog(args.catalog)
        if args.command == "validate-catalog":
            print(f"valid catalog: {len(catalog['scenarios'])} scenarios")
        elif args.command == "plan":
            catalog_profiles = {profile["id"]: profile for profile in catalog["profiles"]}
            known_profiles = set(catalog_profiles)
            unknown = [profile for profile in args.profiles if profile not in known_profiles]
            if unknown:
                raise ContractError(["unknown profiles: " + ", ".join(unknown)])
            canonical_selected = [
                profile["id"]
                for profile in catalog["profiles"]
                if profile["id"] in args.profiles
            ]
            if args.profiles != canonical_selected:
                raise ContractError(["profiles must be unique and follow catalog order"])
            selected_platforms = {
                catalog_profiles[profile_id]["platform"] for profile_id in args.profiles
            }
            complete_platform_profiles = [
                profile["id"]
                for profile in catalog["profiles"]
                if profile["platform"] in selected_platforms
            ]
            if args.profiles != complete_platform_profiles:
                raise ContractError(
                    ["profiles must include every form factor for each selected platform"]
                )
            plan = [
                {"profile_id": profile_id, "scenario_id": scenario_id}
                for profile_id, scenario_id in expected_capture_keys(catalog, args.profiles)
            ]
            print(json.dumps(plan, indent=2))
        else:
            manifest = load_manifest(args.manifest)
            validate_manifest(
                manifest,
                catalog,
                repo_root=args.repo_root,
                fresh_since=args.fresh_since,
            )
            print(f"valid completed run: {len(manifest['images'])} images")
    except ContractError as exc:
        for error in exc.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
