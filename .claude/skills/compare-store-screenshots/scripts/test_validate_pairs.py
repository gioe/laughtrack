from __future__ import annotations

import json
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from validate_pairs import build_view, main

from scripts.screenshots.manifest import ContractError, expected_capture_keys, load_catalog


REPO_ROOT = Path(__file__).resolve().parents[4]
CATALOG_PATH = REPO_ROOT / "screenshots" / "catalog.json"
REVISION = "0123456789abcdef0123456789abcdef01234567"


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def write_png(path: Path, width: int = 390, height: int = 844) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IEND", b"")
    )


def make_run(tmp_path: Path, platform: str) -> Path:
    catalog = load_catalog(CATALOG_PATH)
    root = tmp_path / platform
    profiles = [profile for profile in catalog["profiles"] if profile["platform"] == platform]
    profile_ids = [profile["id"] for profile in profiles]
    by_id = {profile["id"]: profile for profile in profiles}
    images = []
    for profile_id, scenario_id in expected_capture_keys(catalog, profile_ids):
        profile = by_id[profile_id]
        relative_path = f"images/{profile_id}/{scenario_id}.png"
        width = 390 if profile["form_factor"] == "phone" else 800
        height = 844 if profile["form_factor"] == "phone" else 1280
        write_png(root / relative_path, width, height)
        images.append(
            {
                "path": relative_path,
                "scenario_id": scenario_id,
                "profile_id": profile_id,
                "platform": platform,
                "form_factor": profile["form_factor"],
                "width": width,
                "height": height,
                "captured_at": "2026-07-15T14:00:05Z",
                "git_revision": REVISION,
            }
        )
    manifest = {
        "schema_version": 1,
        "status": "completed",
        "run_id": f"{platform}-run",
        "started_at": "2026-07-15T14:00:00Z",
        "completed_at": "2026-07-15T14:01:00Z",
        "git_revision": REVISION,
        "git_dirty": False,
        "profiles": profile_ids,
        "images": images,
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


@pytest.fixture
def manifests(tmp_path: Path) -> tuple[Path, Path]:
    return make_run(tmp_path, "ios"), make_run(tmp_path, "android")


def view(manifests: tuple[Path, Path], name: str, scenario: str | None = None) -> dict:
    ios, android = manifests
    return build_view(
        ios_manifest_path=ios,
        android_manifest_path=android,
        catalog_path=CATALOG_PATH,
        fresh_since=datetime(2026, 7, 15, 13, 59, tzinfo=timezone.utc),
        view=name,
        scenario=scenario,
    )


@pytest.mark.parametrize(
    ("name", "profiles"),
    [
        ("phone", ["ios_phone", "android_phone"]),
        ("tablet", ["ios_large_tablet", "android_large_tablet", "android_small_tablet"]),
        (
            "all",
            [
                "ios_phone",
                "android_phone",
                "ios_large_tablet",
                "android_large_tablet",
                "android_small_tablet",
            ],
        ),
    ],
)
def test_views_group_every_scenario_with_matched_profiles_adjacent(
    manifests: tuple[Path, Path], name: str, profiles: list[str]
) -> None:
    result = view(manifests, name)
    assert len(result["groups"]) == 9
    assert [image["profile_id"] for image in result["groups"][0]["images"]] == profiles
    assert all(Path(image["path"]).is_absolute() for image in result["groups"][0]["images"])


def test_single_scenario_view_returns_only_requested_match(manifests: tuple[Path, Path]) -> None:
    result = view(manifests, "all", "05_ClubDetail")
    assert [group["scenario_id"] for group in result["groups"]] == ["05_ClubDetail"]
    assert len(result["groups"][0]["images"]) == 5


def test_missing_capture_fails_validation(manifests: tuple[Path, Path]) -> None:
    manifest_path = manifests[1]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["images"].pop()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ContractError, match="missing="):
        view(manifests, "phone")


def test_duplicate_capture_fails_validation(manifests: tuple[Path, Path]) -> None:
    manifest_path = manifests[1]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["images"][-1] = dict(manifest["images"][0])
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ContractError, match="duplicates="):
        view(manifests, "phone")


def test_stale_run_fails_validation(manifests: tuple[Path, Path]) -> None:
    ios, android = manifests
    with pytest.raises(ContractError, match="freshness boundary"):
        build_view(
            ios_manifest_path=ios,
            android_manifest_path=android,
            catalog_path=CATALOG_PATH,
            fresh_since=datetime(2026, 7, 15, 14, 0, 1, tzinfo=timezone.utc),
            view="phone",
            scenario=None,
        )


def test_unreadable_capture_fails_validation(manifests: tuple[Path, Path]) -> None:
    manifest_path = manifests[0]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (manifest_path.parent / manifest["images"][0]["path"]).write_text("not a PNG", encoding="utf-8")
    with pytest.raises(ContractError, match="not a readable PNG"):
        view(manifests, "phone")


def test_unexpected_orphan_capture_fails_validation(manifests: tuple[Path, Path]) -> None:
    write_png(manifests[1].parent / "images/android_phone/unexpected.png")
    with pytest.raises(ContractError, match="unexpected captures"):
        view(manifests, "phone")


def test_cli_prints_selected_view(manifests: tuple[Path, Path], capsys: pytest.CaptureFixture[str]) -> None:
    ios, android = manifests
    assert (
        main(
            [
                "--ios-manifest",
                str(ios),
                "--android-manifest",
                str(android),
                "--catalog",
                str(CATALOG_PATH),
                "--fresh-since",
                "2026-07-15T13:59:00Z",
                "--view",
                "tablet",
                "--scenario",
                "01_NearMe",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["view"] == "tablet"
    assert len(result["groups"]) == 1
