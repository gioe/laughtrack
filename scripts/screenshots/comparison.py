#!/usr/bin/env python3
"""Build scenario-oriented screenshot sheets and delta-aware audit metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.screenshots.manifest import (
        ContractError, SCENARIO_IDS, load_catalog, load_manifest, png_dimensions, validate_manifest,
    )
except ModuleNotFoundError:
    from manifest import (  # type: ignore[no-redef]
        ContractError, SCENARIO_IDS, load_catalog, load_manifest, png_dimensions, validate_manifest,
    )

BASELINE_SCHEMA_VERSION = 1
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
GIT_REVISION_RE = re.compile(r"[0-9a-f]{40}\Z")
PROFILE_ORDER = (
    "ios_phone",
    "android_phone",
    "ios_large_tablet",
    "android_large_tablet",
    "android_small_tablet",
)


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def decoded_pixel_sha256(path: Path, *, magick: str = "magick") -> str:
    """Hash normalized decoded RGBA pixels, independent of PNG encoding metadata."""
    try:
        result = subprocess.run(
            [magick, str(path), "-alpha", "on", "-colorspace", "sRGB", "-depth", "8", "RGBA:-"],
            check=True, capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ContractError([f"{path}: cannot decode pixels with ImageMagick: {exc}"]) from exc
    width, height = png_dimensions(path)
    return hashlib.sha256(f"{width}x{height}\0".encode() + result.stdout).hexdigest()


def _load_runs(
    ios_manifest_path: Path,
    android_manifest_path: Path,
    catalog_path: Path,
    fresh_since: datetime | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    catalog = load_catalog(catalog_path)
    captures: dict[tuple[str, str], dict[str, Any]] = {}
    manifests: dict[str, str] = {}
    revisions: set[str] = set()
    for platform, supplied_path in (("ios", ios_manifest_path), ("android", android_manifest_path)):
        path = supplied_path.resolve()
        manifest = load_manifest(path)
        validate_manifest(manifest, catalog, repo_root=path.parent, fresh_since=fresh_since)
        expected = [p["id"] for p in catalog["profiles"] if p["platform"] == platform]
        if manifest["profiles"] != expected:
            raise ContractError([f"{platform}: manifest profiles do not describe a complete run"])
        manifests[f"{platform}_manifest_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        revisions.add(manifest["git_revision"])
        for image in manifest["images"]:
            captures[(image["profile_id"], image["scenario_id"])] = {
                "profile_id": image["profile_id"],
                "scenario_id": image["scenario_id"],
                "platform": image["platform"],
                "form_factor": image["form_factor"],
                "path": str((path.parent / image["path"]).resolve()),
                "width": image["width"],
                "height": image["height"],
            }
    if len(revisions) != 1:
        raise ContractError(["iOS and Android run manifests must record the same Git revision"])
    ordered = [captures[(profile, scenario)] for scenario in SCENARIO_IDS for profile in PROFILE_ORDER]
    return catalog, ordered, {"git_revision": revisions.pop(), **manifests}


def _baseline_records(
    baseline_path: Path | None, *, catalog_sha: str
) -> tuple[dict[tuple[str, str], str], list[str]]:
    if baseline_path is None or not baseline_path.exists():
        return {}, ["reviewed baseline is missing"]
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"reviewed baseline is unreadable: {exc}"]
    reasons: list[str] = []
    if baseline.get("schema_version") != BASELINE_SCHEMA_VERSION:
        reasons.append("baseline schema version is invalid")
    if baseline.get("status") != "reviewed":
        reasons.append("baseline status is not reviewed")
    if baseline.get("catalog_sha256") != catalog_sha:
        reasons.append("baseline catalog provenance does not match")
    if baseline.get("scenario_order") != list(SCENARIO_IDS) or baseline.get("profile_order") != list(PROFILE_ORDER):
        reasons.append("baseline comparison order is invalid")
    provenance = baseline.get("source_provenance")
    if not isinstance(provenance, dict) or not GIT_REVISION_RE.fullmatch(provenance.get("git_revision", "")) or any(
        not SHA256_RE.fullmatch(provenance.get(key, ""))
        for key in ("ios_manifest_sha256", "android_manifest_sha256")
    ):
        reasons.append("baseline source provenance is invalid")
    records = baseline.get("captures")
    if not isinstance(records, list):
        reasons.append("baseline captures are invalid")
        records = []
    indexed: dict[tuple[str, str], str] = {}
    for record in records:
        if not isinstance(record, dict):
            reasons.append("baseline contains a malformed capture")
            continue
        key = (record.get("profile_id"), record.get("scenario_id"))
        digest = record.get("decoded_pixel_sha256")
        if key in indexed or key[0] not in PROFILE_ORDER or key[1] not in SCENARIO_IDS or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            reasons.append("baseline contains invalid or duplicate capture provenance")
            continue
        indexed[key] = digest
    if reasons:
        return {}, sorted(set(reasons))
    return indexed, []


def build_comparison(
    *, ios_manifest_path: Path, android_manifest_path: Path, catalog_path: Path,
    fresh_since: datetime | None = None, baseline_path: Path | None = None,
    scenario: str | None = None, decode=decoded_pixel_sha256,
) -> dict[str, Any]:
    catalog, captures, provenance = _load_runs(ios_manifest_path, android_manifest_path, catalog_path, fresh_since)
    catalog_sha = _canonical_sha(catalog)
    baseline, baseline_reasons = _baseline_records(baseline_path, catalog_sha=catalog_sha)
    groups = []
    for scenario_id in ([scenario] if scenario else SCENARIO_IDS):
        images = []
        reasons = list(baseline_reasons)
        for capture in (c for c in captures if c["scenario_id"] == scenario_id):
            digest = decode(Path(capture["path"]))
            expected = baseline.get((capture["profile_id"], scenario_id))
            state = "unchanged" if expected == digest else ("missing_baseline" if expected is None else "changed")
            if state != "unchanged":
                reasons.append(f"{capture['profile_id']}: {state}")
            images.append({**capture, "decoded_pixel_sha256": digest, "delta": state})
        groups.append({
            "scenario_id": scenario_id,
            "sheet_path": None,
            "review_required": bool(reasons),
            "review_reasons": sorted(set(reasons)),
            "images": images,
        })
    return {
        "schema_version": 1, "catalog_sha256": catalog_sha,
        "git_revision": provenance["git_revision"], "source_provenance": provenance,
        "baseline_usable": not baseline_reasons, "baseline_reasons": baseline_reasons,
        "groups": groups,
    }


def generate_sheets(comparison: dict[str, Any], output_dir: Path, *, magick: str = "magick") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for group in comparison["groups"]:
        destination = (output_dir / f"{group['scenario_id']}.png").resolve()
        command = [magick]
        for image in group["images"]:
            command += ["(", image["path"], "-thumbnail", "300x650", "-background", "#202124", "-gravity", "north", "-splice", "0x42", "-fill", "white", "-pointsize", "18", "-annotate", "+0+10", image["profile_id"], ")"]
        command += ["+append", "-background", "#202124", "-gravity", "north", "-splice", "0x48", "-fill", "white", "-pointsize", "22", "-annotate", "+0+12", group["scenario_id"], str(destination)]
        try:
            subprocess.run(command, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ContractError([f"failed to generate {destination.name}: {exc}"]) from exc
        group["sheet_path"] = str(destination)


def write_reviewed_baseline(comparison: Mapping[str, Any], path: Path, reviewed_by: str) -> None:
    groups = comparison.get("groups")
    if not isinstance(groups, list) or [g.get("scenario_id") for g in groups] != list(SCENARIO_IDS):
        raise ContractError(["a reviewed baseline requires the complete canonical scenario set"])
    captures = [
        {key: image[key] for key in ("profile_id", "scenario_id", "width", "height", "decoded_pixel_sha256")}
        for group in groups for image in group["images"]
    ]
    baseline = {
        "schema_version": BASELINE_SCHEMA_VERSION, "status": "reviewed",
        "reviewed_at": datetime.now(timezone.utc).isoformat(), "reviewed_by": reviewed_by,
        "catalog_sha256": comparison["catalog_sha256"], "scenario_order": list(SCENARIO_IDS),
        "profile_order": list(PROFILE_ORDER), "source_provenance": comparison["source_provenance"],
        "captures": captures,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")


def _fresh(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("must include a timezone offset")
    return parsed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ios-manifest", type=Path, required=True)
    parser.add_argument("--android-manifest", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=Path("screenshots/catalog.json"))
    parser.add_argument("--fresh-since", type=_fresh)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--scenario", choices=SCENARIO_IDS)
    parser.add_argument("--sheet-dir", type=Path)
    parser.add_argument("--write-baseline", type=Path)
    parser.add_argument("--reviewed-by")
    args = parser.parse_args(argv)
    try:
        result = build_comparison(ios_manifest_path=args.ios_manifest, android_manifest_path=args.android_manifest, catalog_path=args.catalog, fresh_since=args.fresh_since, baseline_path=args.baseline, scenario=args.scenario)
        if args.sheet_dir:
            generate_sheets(result, args.sheet_dir)
        if args.write_baseline:
            if not args.reviewed_by:
                raise ContractError(["--write-baseline requires --reviewed-by"])
            write_reviewed_baseline(result, args.write_baseline, args.reviewed_by)
    except (ContractError, ValueError) as exc:
        errors = exc.errors if isinstance(exc, ContractError) else (str(exc),)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
