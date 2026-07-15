from __future__ import annotations

import hashlib
import json
import struct
import zlib
from pathlib import Path

import pytest

from scripts.screenshots.export import (
    PROFILE_LAYOUTS,
    STOREFRONT_SELECTIONS,
    collect_run,
    export_projection,
)
from scripts.screenshots.manifest import ContractError, load_catalog

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "screenshots" / "catalog.json"


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def write_png(path: Path, width: int, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IEND", b""))


def file_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.png"))
    }


def make_capture(root: Path, platform: str) -> None:
    catalog = load_catalog(CATALOG_PATH)
    dimensions = {
        "ios_phone": (1320, 2868),
        "ios_large_tablet": (2064, 2752),
        "android_phone": (1320, 2868),
        "android_small_tablet": (1200, 2133),
        "android_large_tablet": (1600, 2844),
    }
    for profile in catalog["profiles"]:
        if profile["platform"] != platform:
            continue
        layout = PROFILE_LAYOUTS[profile["id"]]
        for scenario in catalog["scenarios"]:
            write_png(
                root / layout["source_directory"] / f"{layout['source_prefix']}{scenario['id']}.png",
                *dimensions[profile["id"]],
            )


def collect(tmp_path: Path, platform: str) -> tuple[Path, Path]:
    source = tmp_path / f"{platform}-capture"
    run_root = tmp_path / f"{platform}-run"
    make_capture(source, platform)
    manifest = collect_run(
        platform=platform,
        source_root=source,
        run_root=run_root,
        catalog_path=CATALOG_PATH,
        repo_root=REPO_ROOT,
    )
    return source, manifest


def test_play_projection_exports_eight_phone_and_four_per_tablet(tmp_path: Path) -> None:
    source, manifest = collect(tmp_path, "android")
    source_before = file_hashes(source)
    run_before = file_hashes(manifest.parent)
    output = tmp_path / "play-metadata"
    marker = output / "en-US" / "full_description.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("LaughTrack", encoding="utf-8")

    exported = export_projection(
        storefront="play",
        manifest_path=manifest,
        output_root=output,
        catalog_path=CATALOG_PATH,
        repo_root=manifest.parent,
    )

    assert len(exported) == 16
    for profile_id, selected in STOREFRONT_SELECTIONS["play"].items():
        directory = output / PROFILE_LAYOUTS[profile_id]["destination_directory"]
        assert [path.stem for path in sorted(directory.glob("*.png"))] == sorted(selected)
    assert marker.read_text(encoding="utf-8") == "LaughTrack"
    assert file_hashes(source) == source_before
    assert file_hashes(manifest.parent) == run_before


def test_app_store_projection_exports_all_canonical_phone_and_ipad_images(
    tmp_path: Path,
) -> None:
    source, manifest = collect(tmp_path, "ios")
    source_before = file_hashes(source)
    run_before = file_hashes(manifest.parent)
    output = tmp_path / "app-store-screenshots"

    exported = export_projection(
        storefront="app-store",
        manifest_path=manifest,
        output_root=output,
        catalog_path=CATALOG_PATH,
        repo_root=manifest.parent,
    )

    expected_names = {
        f"{PROFILE_LAYOUTS[profile_id]['destination_prefix']}{scenario_id}.png"
        for profile_id, scenario_ids in STOREFRONT_SELECTIONS["app-store"].items()
        for scenario_id in scenario_ids
    }
    assert len(exported) == 18
    assert {path.name for path in (output / "en-US").glob("*.png")} == expected_names
    assert file_hashes(source) == source_before
    assert file_hashes(manifest.parent) == run_before


def test_collection_serializes_normalized_validated_manifest(tmp_path: Path) -> None:
    _, manifest_path = collect(tmp_path, "ios")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["status"] == "completed"
    assert manifest["profiles"] == ["ios_phone", "ios_large_tablet"]
    assert len(manifest["images"]) == 18
    assert manifest["images"][0]["path"] == "images/ios_phone/01_NearMe.png"
    assert all(Path(image["path"]).name == f"{image['scenario_id']}.png" for image in manifest["images"])


def test_collection_rejects_incomplete_capture_before_replacing_run(tmp_path: Path) -> None:
    source = tmp_path / "capture"
    make_capture(source, "android")
    missing = source / PROFILE_LAYOUTS["android_phone"]["source_directory"] / "09_PodcastDetail.png"
    missing.unlink()
    run_root = tmp_path / "run"
    marker = run_root / "keep.txt"
    marker.parent.mkdir()
    marker.write_text("unchanged", encoding="utf-8")

    with pytest.raises(ContractError, match="not canonical"):
        collect_run(
            platform="android",
            source_root=source,
            run_root=run_root,
            catalog_path=CATALOG_PATH,
            repo_root=REPO_ROOT,
        )

    assert marker.read_text(encoding="utf-8") == "unchanged"


def test_export_rejects_invalid_manifest_before_touching_projection(tmp_path: Path) -> None:
    _, manifest_path = collect(tmp_path, "android")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["images"].pop()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "projection"
    marker = output / "keep.txt"
    marker.parent.mkdir()
    marker.write_text("unchanged", encoding="utf-8")

    with pytest.raises(ContractError, match="missing="):
        export_projection(
            storefront="play",
            manifest_path=manifest_path,
            output_root=output,
            catalog_path=CATALOG_PATH,
            repo_root=manifest_path.parent,
        )

    assert marker.read_text(encoding="utf-8") == "unchanged"


def test_export_removes_stale_projection_images(tmp_path: Path) -> None:
    _, manifest = collect(tmp_path, "android")
    output = tmp_path / "projection"
    stale = output / PROFILE_LAYOUTS["android_phone"]["destination_directory"] / "stale.png"
    write_png(stale, 10, 20)

    export_projection(
        storefront="play",
        manifest_path=manifest,
        output_root=output,
        catalog_path=CATALOG_PATH,
        repo_root=manifest.parent,
    )

    assert not stale.exists()


def test_export_rejects_raw_run_and_projection_overlap(tmp_path: Path) -> None:
    _, manifest = collect(tmp_path, "ios")

    with pytest.raises(ContractError, match="must not overlap"):
        export_projection(
            storefront="app-store",
            manifest_path=manifest,
            output_root=manifest.parent / "projection",
            catalog_path=CATALOG_PATH,
            repo_root=manifest.parent,
        )
