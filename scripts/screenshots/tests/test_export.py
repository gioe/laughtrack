from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

from scripts.screenshots.export import (
    PROFILE_DIMENSIONS,
    PROFILE_LAYOUTS,
    STOREFRONT_SELECTIONS,
    collect_run,
    export_projection,
    main as export_main,
    reusable_capture_profiles,
    validate_capture_profile,
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


def make_capture(
    root: Path,
    platform: str,
    profile_ids: set[str] | None = None,
    scenario_ids: set[str] | None = None,
) -> None:
    catalog = load_catalog(CATALOG_PATH)
    for profile in catalog["profiles"]:
        if profile["platform"] != platform or (profile_ids is not None and profile["id"] not in profile_ids):
            continue
        layout = PROFILE_LAYOUTS[profile["id"]]
        for scenario in catalog["scenarios"]:
            if scenario_ids is not None and scenario["id"] not in scenario_ids:
                continue
            write_png(
                root / layout["source_directory"] / f"{layout['source_prefix']}{scenario['id']}.png",
                *PROFILE_DIMENSIONS[profile["id"]],
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
    assert manifest["mode"] == "complete"
    assert manifest["profiles"] == ["ios_phone", "ios_large_tablet"]
    assert manifest["scenarios"] == [scenario["id"] for scenario in load_catalog(CATALOG_PATH)["scenarios"]]
    assert len(manifest["images"]) == 34
    assert manifest["images"][0]["path"] == "images/ios_phone/01_NearMe.png"
    assert all(Path(image["path"]).name == f"{image['scenario_id']}.png" for image in manifest["images"])


def test_verification_collection_materializes_only_selected_matrix(tmp_path: Path) -> None:
    source = tmp_path / "ios-capture"
    scenarios = ["02_SearchShows", "03_SearchComedians", "04_SearchClubs"]
    make_capture(source, "ios", {"ios_phone"}, set(scenarios))

    manifest_path = collect_run(
        platform="ios",
        source_root=source,
        run_root=tmp_path / "ios-run",
        catalog_path=CATALOG_PATH,
        repo_root=REPO_ROOT,
        profile_ids=["ios_phone"],
        scenario_ids=scenarios,
        mode="verification",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["mode"] == "verification"
    assert manifest["profiles"] == ["ios_phone"]
    assert manifest["scenarios"] == scenarios
    assert [image["scenario_id"] for image in manifest["images"]] == scenarios
    assert [path.name for path in sorted((manifest_path.parent / "images/ios_phone").glob("*.png"))] == [
        f"{scenario}.png" for scenario in scenarios
    ]

    with pytest.raises(ContractError, match="complete canonical run"):
        export_projection(
            storefront="app-store",
            manifest_path=manifest_path,
            output_root=tmp_path / "projection",
            catalog_path=CATALOG_PATH,
            repo_root=manifest_path.parent,
        )


def test_verification_collection_rejects_out_of_order_selection(tmp_path: Path) -> None:
    source = tmp_path / "ios-capture"
    make_capture(source, "ios", {"ios_phone"}, {"02_SearchShows", "04_SearchClubs"})

    with pytest.raises(ContractError, match="scenarios must be unique and follow catalog order"):
        collect_run(
            platform="ios",
            source_root=source,
            run_root=tmp_path / "ios-run",
            catalog_path=CATALOG_PATH,
            repo_root=REPO_ROOT,
            profile_ids=["ios_phone"],
            scenario_ids=["04_SearchClubs", "02_SearchShows"],
            mode="verification",
        )


def test_collection_preserves_capture_time_separately_from_cache_materialization(
    tmp_path: Path,
) -> None:
    source = tmp_path / "ios-capture"
    make_capture(source, "ios")
    revision = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    provenance_path = source / ".screenshot-cache-provenance.json"
    provenance_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profiles": {
                    "ios_phone": {
                        "source": "cache",
                        "cache_key": "a" * 64,
                        "captured_at": "2026-06-01T12:00:00Z",
                        "capture_git_revision": "f" * 40,
                        "capture_git_dirty": False,
                        "materialized_at": "2026-07-20T12:00:00Z",
                    },
                    "ios_large_tablet": {
                        "source": "capture",
                        "cache_key": "b" * 64,
                        "captured_at": "2026-07-20T12:00:00Z",
                        "capture_git_revision": revision,
                        "capture_git_dirty": True,
                        "materialized_at": "2026-07-20T12:00:01Z",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    manifest_path = collect_run(
        platform="ios",
        source_root=source,
        run_root=tmp_path / "ios-run",
        catalog_path=CATALOG_PATH,
        repo_root=REPO_ROOT,
        provenance_path=provenance_path,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    phone = next(image for image in manifest["images"] if image["profile_id"] == "ios_phone")
    tablet = next(
        image for image in manifest["images"] if image["profile_id"] == "ios_large_tablet"
    )

    assert phone["captured_at"] == "2026-06-01T12:00:00Z"
    assert phone["materialized_at"] != phone["captured_at"]
    assert phone["capture_git_revision"] == "f" * 40
    assert phone["provenance"] == "cache"
    assert tablet["capture_git_revision"] == revision
    assert tablet["provenance"] == "capture"


def test_collection_rejects_incomplete_cache_provenance(tmp_path: Path) -> None:
    source = tmp_path / "ios-capture"
    make_capture(source, "ios")
    provenance_path = source / ".screenshot-cache-provenance.json"
    provenance_path.write_text(
        json.dumps({"schema_version": 1, "profiles": {"ios_phone": {}}}),
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="missing profile ios_large_tablet"):
        collect_run(
            platform="ios",
            source_root=source,
            run_root=tmp_path / "ios-run",
            catalog_path=CATALOG_PATH,
            repo_root=REPO_ROOT,
            provenance_path=provenance_path,
        )


def test_collection_rejects_explicit_missing_cache_provenance(tmp_path: Path) -> None:
    source = tmp_path / "ios-capture"
    make_capture(source, "ios")

    with pytest.raises(ContractError, match="does not exist"):
        collect_run(
            platform="ios",
            source_root=source,
            run_root=tmp_path / "ios-run",
            catalog_path=CATALOG_PATH,
            repo_root=REPO_ROOT,
            provenance_path=source / ".missing-provenance.json",
        )


def test_completed_profile_is_reusable_while_later_profiles_are_incomplete(tmp_path: Path) -> None:
    source = tmp_path / "android-capture"
    make_capture(source, "android", {"android_phone"})
    phone_directory = source / PROFILE_LAYOUTS["android_phone"]["source_directory"]
    phone_before = file_hashes(phone_directory)

    assert reusable_capture_profiles(
        platform="android",
        source_root=source,
        catalog_path=CATALOG_PATH,
    ) == ("android_phone",)

    make_capture(source, "android", {"android_small_tablet", "android_large_tablet"})
    manifest_path = collect_run(
        platform="android",
        source_root=source,
        run_root=tmp_path / "android-run",
        catalog_path=CATALOG_PATH,
        repo_root=REPO_ROOT,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert file_hashes(phone_directory) == phone_before
    assert manifest["profiles"] == ["android_phone", "android_small_tablet", "android_large_tablet"]
    assert len(manifest["images"]) == 51


def test_incomplete_or_wrong_sized_profile_is_not_reusable(tmp_path: Path) -> None:
    source = tmp_path / "android-capture"
    make_capture(source, "android", {"android_phone"})
    directory = source / PROFILE_LAYOUTS["android_phone"]["source_directory"]
    missing = directory / "09_PodcastDetail.png"
    missing.unlink()

    assert (
        reusable_capture_profiles(
            platform="android",
            source_root=source,
            catalog_path=CATALOG_PATH,
        )
        == ()
    )
    with pytest.raises(ContractError, match="not canonical"):
        validate_capture_profile(
            profile_id="android_phone",
            source_root=source,
            catalog_path=CATALOG_PATH,
        )

    write_png(missing, 10, 20)
    with pytest.raises(ContractError, match="expected 1320x2868"):
        validate_capture_profile(
            profile_id="android_phone",
            source_root=source,
            catalog_path=CATALOG_PATH,
        )


def test_selected_profile_validation_accepts_only_requested_canonical_frames(tmp_path: Path) -> None:
    source = tmp_path / "android-capture"
    scenarios = ["02_SearchShows", "04_SearchClubs", "08_SearchPodcasts"]
    make_capture(source, "android", {"android_phone"}, set(scenarios))

    validate_capture_profile(
        profile_id="android_phone",
        source_root=source,
        catalog_path=CATALOG_PATH,
        scenario_ids=scenarios,
    )

    with pytest.raises(ContractError, match="catalog order"):
        validate_capture_profile(
            profile_id="android_phone",
            source_root=source,
            catalog_path=CATALOG_PATH,
            scenario_ids=list(reversed(scenarios)),
        )


def test_reusable_profiles_cli_emits_only_complete_profiles(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "android-capture"
    make_capture(source, "android", {"android_phone"})

    assert (
        export_main(
            [
                "--catalog",
                str(CATALOG_PATH),
                "reusable-profiles",
                "android",
                "--source-root",
                str(source),
            ]
        )
        == 0
    )
    assert capsys.readouterr().out == "android_phone\n"


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
