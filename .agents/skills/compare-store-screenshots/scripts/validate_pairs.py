#!/usr/bin/env python3
"""Validate screenshot run manifests and emit adjacent cross-platform views."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.screenshots.manifest import (  # noqa: E402
    ContractError,
    SCENARIO_IDS,
    load_catalog,
    load_manifest,
    validate_manifest,
)


VIEW_PROFILES = {
    "phone": ("ios_phone", "android_phone"),
    "tablet": ("ios_large_tablet", "android_large_tablet", "android_small_tablet"),
    "all": (
        "ios_phone",
        "android_phone",
        "ios_large_tablet",
        "android_large_tablet",
        "android_small_tablet",
    ),
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def parse_fresh_since(value: str) -> datetime:
    """Parse a timezone-aware RFC 3339 freshness boundary."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must include a timezone offset")
    return parsed


def _validate_run_files(run_root: Path, manifest: Mapping[str, Any], platform: str) -> None:
    """Reject image files that exist in a normalized run but are undeclared."""
    declared = {
        image["path"]
        for image in manifest["images"]
        if isinstance(image, dict) and isinstance(image.get("path"), str)
    }
    actual = {
        path.relative_to(run_root).as_posix()
        for path in run_root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    }
    unexpected = sorted(actual - declared)
    if unexpected:
        raise ContractError([f"{platform}: unexpected captures: {', '.join(unexpected)}"])


def build_view(
    *,
    ios_manifest_path: Path,
    android_manifest_path: Path,
    catalog_path: Path,
    fresh_since: datetime | None,
    view: str,
    scenario: str | None,
) -> dict[str, Any]:
    """Validate two completed runs and return an ordered comparison view."""
    catalog = load_catalog(catalog_path)
    manifests: dict[str, tuple[Path, dict[str, Any]]] = {}
    expected_profiles = {
        platform: {
            profile["id"] for profile in catalog["profiles"] if profile["platform"] == platform
        }
        for platform in ("ios", "android")
    }

    for platform, manifest_path in (
        ("ios", ios_manifest_path),
        ("android", android_manifest_path),
    ):
        resolved_manifest = manifest_path.resolve()
        run_root = resolved_manifest.parent
        manifest = load_manifest(resolved_manifest)
        validate_manifest(
            manifest,
            catalog,
            repo_root=run_root,
            fresh_since=fresh_since,
        )
        actual_profiles = set(manifest["profiles"])
        if actual_profiles != expected_profiles[platform]:
            raise ContractError(
                [
                    f"{platform}: manifest profiles do not describe a complete {platform} run: "
                    f"expected={sorted(expected_profiles[platform])}, "
                    f"actual={sorted(actual_profiles)}"
                ]
            )
        _validate_run_files(run_root, manifest, platform)
        manifests[platform] = (run_root, manifest)

    revisions = {manifest["git_revision"] for _, manifest in manifests.values()}
    if len(revisions) != 1:
        raise ContractError(["iOS and Android run manifests must record the same Git revision"])

    indexed: dict[tuple[str, str], tuple[Path, Mapping[str, Any]]] = {}
    for run_root, manifest in manifests.values():
        for image in manifest["images"]:
            indexed[(image["profile_id"], image["scenario_id"])] = (run_root, image)

    scenario_ids = [scenario] if scenario else list(SCENARIO_IDS)
    groups = []
    for scenario_id in scenario_ids:
        images = []
        for profile_id in VIEW_PROFILES[view]:
            run_root, image = indexed[(profile_id, scenario_id)]
            images.append(
                {
                    "profile_id": profile_id,
                    "platform": image["platform"],
                    "form_factor": image["form_factor"],
                    "path": str((run_root / image["path"]).resolve()),
                    "width": image["width"],
                    "height": image["height"],
                }
            )
        groups.append({"scenario_id": scenario_id, "images": images})

    return {
        "view": view,
        "scenario": scenario,
        "git_revision": revisions.pop(),
        "groups": groups,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ios-manifest", type=Path, required=True)
    parser.add_argument("--android-manifest", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=Path("screenshots/catalog.json"))
    parser.add_argument("--fresh-since", type=parse_fresh_since, required=True)
    parser.add_argument("--view", choices=tuple(VIEW_PROFILES), default="phone")
    parser.add_argument("--scenario", choices=SCENARIO_IDS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = build_view(
            ios_manifest_path=args.ios_manifest,
            android_manifest_path=args.android_manifest,
            catalog_path=args.catalog,
            fresh_since=args.fresh_since,
            view=args.view,
            scenario=args.scenario,
        )
    except ContractError as exc:
        for error in exc.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
