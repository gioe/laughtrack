#!/usr/bin/env python3
"""Validate fresh, one-to-one iOS and Android store screenshot pairs."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


EXPECTED_KEYS = (
    "01_NearMe",
    "02_SearchShows",
    "03_SearchComedians",
    "04_SearchClubs",
    "05_ClubDetail",
    "06_ShowDetail",
    "07_ComedianDetail",
    "08_SearchPodcasts",
    "09_PodcastDetail",
)


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as image:
        header = image.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a readable PNG")
    return struct.unpack(">II", header[16:24])


def capture_key(path: Path) -> str | None:
    name = path.stem
    for key in EXPECTED_KEYS:
        if key in name:
            return key
    return None


def collect(directory: Path, fresh_since: float | None) -> tuple[dict[str, list[Path]], list[Path], list[Path]]:
    grouped = {key: [] for key in EXPECTED_KEYS}
    unexpected: list[Path] = []
    stale: list[Path] = []
    for path in sorted(directory.glob("*.png")):
        key = capture_key(path)
        if key is None:
            unexpected.append(path)
            continue
        if fresh_since is not None and path.stat().st_mtime < fresh_since:
            stale.append(path)
            continue
        grouped[key].append(path)
    return grouped, unexpected, stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--fresh-since", type=float)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    directories = {
        "ios": root / "ios/fastlane/screenshots/en-US",
        "android": root / "android/fastlane/metadata/android/en-US/images/phoneScreenshots",
    }
    errors: list[str] = []
    captures: dict[str, dict[str, list[Path]]] = {}

    for platform, directory in directories.items():
        if not directory.is_dir():
            errors.append(f"{platform}: output directory does not exist: {directory}")
            continue
        grouped, unexpected, stale = collect(directory, args.fresh_since)
        captures[platform] = grouped
        if unexpected:
            errors.append(f"{platform}: unexpected PNGs: {', '.join(path.name for path in unexpected)}")
        if stale:
            errors.append(f"{platform}: stale PNGs: {', '.join(path.name for path in stale)}")
        for key, paths in grouped.items():
            if len(paths) != 1:
                errors.append(f"{platform}: expected exactly one {key} capture, found {len(paths)}")

    manifest: list[dict[str, object]] = []
    if not errors:
        for key in EXPECTED_KEYS:
            row: dict[str, object] = {"key": key}
            for platform in ("ios", "android"):
                path = captures[platform][key][0]
                try:
                    width, height = png_dimensions(path)
                except (OSError, ValueError) as exc:
                    errors.append(f"{platform}: {path.name}: {exc}")
                    continue
                row[platform] = {
                    "path": str(path),
                    "width": width,
                    "height": height,
                }
            manifest.append(row)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(json.dumps({"pairs": manifest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
