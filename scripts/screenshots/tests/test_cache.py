from __future__ import annotations

import json
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

from scripts.screenshots.cache import (
    PROVENANCE_FILENAME,
    plan_cache,
    profile_cache_key,
    store_profile,
)
from scripts.screenshots.export import PROFILE_DIMENSIONS, PROFILE_LAYOUTS, collect_run
from scripts.screenshots.manifest import ContractError, load_catalog

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "screenshots" / "catalog.json"


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _write_png(path: Path, width: int, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IEND", b""))


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "ios").mkdir(parents=True)
    (repo / "android").mkdir()
    (repo / "docs").mkdir()
    (repo / "screenshots").mkdir()
    (repo / "scripts" / "screenshots").mkdir(parents=True)
    (repo / "ios" / "App.swift").write_text("ios one\n", encoding="utf-8")
    (repo / "android" / "App.kt").write_text("android one\n", encoding="utf-8")
    (repo / "docs" / "screenshots.md").write_text("docs one\n", encoding="utf-8")
    shutil.copy2(CATALOG_PATH, repo / "screenshots" / "catalog.json")
    (repo / "scripts" / "screenshots" / "fixture_server.py").write_text("FIXTURE = 1\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.com")
    _git(repo, "config", "user.name", "Screenshot Cache Tests")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "fixtures")
    return repo


def _make_capture(root: Path, profile_id: str) -> None:
    catalog = load_catalog(CATALOG_PATH)
    layout = PROFILE_LAYOUTS[profile_id]
    for scenario in catalog["scenarios"]:
        _write_png(
            root / layout["source_directory"] / f"{layout['source_prefix']}{scenario['id']}.png",
            *PROFILE_DIMENSIONS[profile_id],
        )


def _config(profile_id: str, device: str = "default") -> dict[str, dict[str, str]]:
    platform = "ios" if profile_id.startswith("ios_") else "android"
    catalog = load_catalog(CATALOG_PATH)
    return {
        profile["id"]: {"device": device, "locale": "en-US"}
        for profile in catalog["profiles"]
        if profile["platform"] == platform
    }


def _environment(platform: str) -> dict[str, object]:
    if platform == "ios":
        return {
            "xcode": {"version": "26.3", "build": "17C519"},
            "simulator_runtime": {
                "identifier": "com.apple.CoreSimulator.SimRuntime.iOS-18-3",
                "version": "18.3.1",
                "build": "22D8075",
            },
        }
    return {
        "jdk": {
            "version": "17.0.19",
            "vendor": "Homebrew",
            "vm_name": "OpenJDK 64-Bit Server VM",
            "arch": "aarch64",
        },
        "build_tools": {"path": "build-tools;35.0.0", "revision": "35.0.0"},
        "system_image": {
            "path": "system-images;android-35;google_apis;arm64-v8a",
            "revision": "9",
            "api": "35",
            "tag": "google_apis",
            "abi": "arm64-v8a",
        },
    }


def _expected_key(repo: Path, platform: str, profile_id: str) -> str:
    key, _ = profile_cache_key(
        repo_root=repo,
        platform=platform,
        profile_id=profile_id,
        profile_config=_config(profile_id)[profile_id],
        native_environment=_environment(platform),
    )
    return key


def test_unchanged_profile_is_reused_and_materialized_with_capture_provenance(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    capture = tmp_path / "capture"
    cache = tmp_path / "cache"
    _make_capture(capture, "ios_phone")
    stored = store_profile(
        platform="ios",
        profile_id="ios_phone",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_config=_config("ios_phone")["ios_phone"],
        native_environment=_environment("ios"),
        expected_key=_expected_key(repo, "ios", "ios_phone"),
    )
    shutil.rmtree(capture)

    result = plan_cache(
        platform="ios",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_configs=_config("ios_phone"),
        native_environment=_environment("ios"),
    )

    assert result["reused_profiles"] == ["ios_phone"]
    assert result["pending_profiles"] == ["ios_large_tablet"]
    assert all(path.is_file() for _, path in _profile_paths(capture, "ios_phone"))
    provenance = json.loads((capture / PROVENANCE_FILENAME).read_text(encoding="utf-8"))
    record = provenance["profiles"]["ios_phone"]
    assert record["source"] == "cache"
    assert record["cache_key"] == stored["key"]
    assert record["captured_at"] <= record["materialized_at"]
    assert record["capture_git_dirty"] is False


def test_cache_and_capture_provenance_schema_versions_are_decoupled(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    capture = tmp_path / "capture"
    cache = tmp_path / "cache"
    _make_capture(capture, "ios_phone")

    stored = store_profile(
        platform="ios",
        profile_id="ios_phone",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_config=_config("ios_phone")["ios_phone"],
        native_environment=_environment("ios"),
        expected_key=_expected_key(repo, "ios", "ios_phone"),
    )

    metadata = json.loads(
        (Path(stored["cache_entry"]) / "metadata.json").read_text(encoding="utf-8")
    )
    provenance = json.loads((capture / PROVENANCE_FILENAME).read_text(encoding="utf-8"))

    assert stored["schema_version"] == 2
    assert metadata["schema_version"] == 2
    assert provenance["schema_version"] == 1


def test_cache_generated_provenance_collects_manifest_for_capture_and_reuse(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path)
    capture = tmp_path / "capture"
    cache = tmp_path / "cache"
    _make_capture(capture, "ios_phone")
    store_profile(
        platform="ios",
        profile_id="ios_phone",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_config=_config("ios_phone")["ios_phone"],
        native_environment=_environment("ios"),
        expected_key=_expected_key(repo, "ios", "ios_phone"),
    )
    shutil.rmtree(capture)

    planned = plan_cache(
        platform="ios",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_configs=_config("ios_phone"),
        native_environment=_environment("ios"),
    )
    _make_capture(capture, "ios_large_tablet")
    store_profile(
        platform="ios",
        profile_id="ios_large_tablet",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_config=_config("ios_large_tablet")["ios_large_tablet"],
        native_environment=_environment("ios"),
        expected_key=_expected_key(repo, "ios", "ios_large_tablet"),
    )

    manifest_path = collect_run(
        platform="ios",
        source_root=capture,
        run_root=tmp_path / "run",
        catalog_path=CATALOG_PATH,
        repo_root=repo,
        provenance_path=Path(planned["provenance_path"]),
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provenance_by_profile = {
        image["profile_id"]: image["provenance"] for image in manifest["images"]
    }

    assert planned["reused_profiles"] == ["ios_phone"]
    assert planned["pending_profiles"] == ["ios_large_tablet"]
    assert provenance_by_profile == {
        "ios_phone": "cache",
        "ios_large_tablet": "capture",
    }


def _profile_paths(root: Path, profile_id: str) -> list[tuple[str, Path]]:
    catalog = load_catalog(CATALOG_PATH)
    layout = PROFILE_LAYOUTS[profile_id]
    return [
        (
            scenario["id"],
            root / layout["source_directory"] / f"{layout['source_prefix']}{scenario['id']}.png",
        )
        for scenario in catalog["scenarios"]
    ]


def test_relevant_modified_untracked_deleted_and_profile_config_inputs_change_key(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    base, _ = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config={"device": "A"},
        native_environment=_environment("ios"),
    )
    (repo / "ios" / "App.swift").chmod(0o755)
    executable, _ = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config={"device": "A"},
        native_environment=_environment("ios"),
    )
    (repo / "ios" / "App.swift").chmod(0o644)
    (repo / "ios" / "App.swift").write_text("ios two\n", encoding="utf-8")
    modified, _ = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config={"device": "A"},
        native_environment=_environment("ios"),
    )
    (repo / "ios" / "NewView.swift").write_text("new\n", encoding="utf-8")
    untracked, _ = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config={"device": "A"},
        native_environment=_environment("ios"),
    )
    (repo / "ios" / "App.swift").unlink()
    deleted, inputs = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config={"device": "A"},
        native_environment=_environment("ios"),
    )
    configured, _ = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config={"device": "B"},
        native_environment=_environment("ios"),
    )

    assert len({base, executable, modified, untracked, deleted, configured}) == 6
    assert {item["path"]: item["state"] for item in inputs}["ios/App.swift"] == "deleted"
    assert {item["path"] for item in inputs} >= {"ios/NewView.swift", "screenshots/catalog.json"}


def test_store_rejects_inputs_that_changed_after_planning(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    capture = tmp_path / "capture"
    cache = tmp_path / "cache"
    planned_key = _expected_key(repo, "ios", "ios_phone")
    (repo / "ios" / "App.swift").write_text("changed during capture\n", encoding="utf-8")
    _make_capture(capture, "ios_phone")

    with pytest.raises(ContractError, match="changed while capturing ios_phone"):
        store_profile(
            platform="ios",
            profile_id="ios_phone",
            capture_root=capture,
            cache_root=cache,
            repo_root=repo,
            catalog_path=CATALOG_PATH,
            profile_config=_config("ios_phone")["ios_phone"],
            native_environment=_environment("ios"),
            expected_key=planned_key,
        )

    assert not cache.exists()


def test_docs_storefront_outputs_and_other_platform_do_not_invalidate_profile(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    config = {"device": "A"}
    ios_key, _ = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config=config,
        native_environment=_environment("ios"),
    )
    (repo / "docs" / "screenshots.md").write_text("docs two\n", encoding="utf-8")
    (repo / "android" / "App.kt").write_text("android two\n", encoding="utf-8")
    output = repo / "ios" / "fastlane" / "screenshots" / "en-US" / "output.png"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"storefront")

    unchanged, _ = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config=config,
        native_environment=_environment("ios"),
    )
    android_key, _ = profile_cache_key(
        repo_root=repo,
        platform="android",
        profile_id="android_phone",
        profile_config=config,
        native_environment=_environment("android"),
    )
    (repo / "ios" / "App.swift").write_text("ios two\n", encoding="utf-8")
    android_unchanged, _ = profile_cache_key(
        repo_root=repo,
        platform="android",
        profile_id="android_phone",
        profile_config=config,
        native_environment=_environment("android"),
    )

    assert unchanged == ios_key
    assert android_unchanged == android_key


def test_xcode_and_selected_simulator_runtime_invalidate_only_ios_profiles(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    config = {"device": "A"}
    ios_environment = _environment("ios")
    baseline, _ = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config=config,
        native_environment=ios_environment,
    )
    android_baseline, _ = profile_cache_key(
        repo_root=repo,
        platform="android",
        profile_id="android_phone",
        profile_config=config,
        native_environment=_environment("android"),
    )

    changed_keys = []
    for section, field, value in (
        ("xcode", "build", "17C520"),
        ("simulator_runtime", "identifier", "com.apple.CoreSimulator.SimRuntime.iOS-26-2"),
        ("simulator_runtime", "version", "26.2"),
        ("simulator_runtime", "build", "23C54"),
    ):
        changed = json.loads(json.dumps(ios_environment))
        changed[section][field] = value
        key, _ = profile_cache_key(
            repo_root=repo,
            platform="ios",
            profile_id="ios_phone",
            profile_config=config,
            native_environment=changed,
        )
        changed_keys.append(key)

    android_unchanged, _ = profile_cache_key(
        repo_root=repo,
        platform="android",
        profile_id="android_phone",
        profile_config=config,
        native_environment=_environment("android"),
    )
    assert all(key != baseline for key in changed_keys)
    assert android_unchanged == android_baseline


def test_jdk_build_tools_and_system_image_invalidate_only_android_profiles(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    config = {"device": "A"}
    android_environment = _environment("android")
    baseline, _ = profile_cache_key(
        repo_root=repo,
        platform="android",
        profile_id="android_phone",
        profile_config=config,
        native_environment=android_environment,
    )
    ios_baseline, _ = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config=config,
        native_environment=_environment("ios"),
    )

    changed_keys = []
    for section, field, value in (
        ("jdk", "version", "17.0.20"),
        ("build_tools", "revision", "35.0.1"),
        ("system_image", "revision", "10"),
        ("system_image", "path", "system-images;android-36;google_apis;arm64-v8a"),
    ):
        changed = json.loads(json.dumps(android_environment))
        changed[section][field] = value
        key, _ = profile_cache_key(
            repo_root=repo,
            platform="android",
            profile_id="android_phone",
            profile_config=config,
            native_environment=changed,
        )
        changed_keys.append(key)

    ios_unchanged, _ = profile_cache_key(
        repo_root=repo,
        platform="ios",
        profile_id="ios_phone",
        profile_config=config,
        native_environment=_environment("ios"),
    )
    assert all(key != baseline for key in changed_keys)
    assert ios_unchanged == ios_baseline


def test_corrupt_cached_image_is_rejected_instead_of_materialized(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    capture = tmp_path / "capture"
    cache = tmp_path / "cache"
    _make_capture(capture, "android_phone")
    stored = store_profile(
        platform="android",
        profile_id="android_phone",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_config=_config("android_phone")["android_phone"],
        native_environment=_environment("android"),
        expected_key=_expected_key(repo, "android", "android_phone"),
    )
    entry = Path(stored["cache_entry"])
    next((entry / "capture").rglob("*.png")).write_bytes(b"corrupt")
    shutil.rmtree(capture)

    result = plan_cache(
        platform="android",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_configs=_config("android_phone"),
        native_environment=_environment("android"),
    )

    assert result["reused_profiles"] == []
    assert result["pending_profiles"] == ["android_phone", "android_small_tablet", "android_large_tablet"]
    assert not capture.exists()

    _make_capture(capture, "android_phone")
    repaired = store_profile(
        platform="android",
        profile_id="android_phone",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_config=_config("android_phone")["android_phone"],
        native_environment=_environment("android"),
        expected_key=_expected_key(repo, "android", "android_phone"),
    )
    assert repaired["cache_entry"] == str(entry)


def test_force_fresh_bypasses_valid_cache_without_materializing(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    capture = tmp_path / "capture"
    cache = tmp_path / "cache"
    _make_capture(capture, "ios_phone")
    store_profile(
        platform="ios",
        profile_id="ios_phone",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_config=_config("ios_phone")["ios_phone"],
        native_environment=_environment("ios"),
        expected_key=_expected_key(repo, "ios", "ios_phone"),
    )
    shutil.rmtree(capture)

    result = plan_cache(
        platform="ios",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_configs=_config("ios_phone"),
        native_environment=_environment("ios"),
        force_fresh=True,
    )

    assert result["force_fresh"] is True
    assert result["reused_profiles"] == []
    assert result["pending_profiles"] == ["ios_phone", "ios_large_tablet"]
    assert not capture.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 1),
        ("captured_at", "not-a-timestamp"),
        ("profile_config", {"device": "wrong"}),
        ("native_environment", {"xcode": {"version": "wrong"}}),
        ("inputs", []),
    ],
)
def test_invalid_cached_provenance_is_rejected(tmp_path: Path, field: str, value: object) -> None:
    repo = _make_repo(tmp_path)
    capture = tmp_path / "capture"
    cache = tmp_path / "cache"
    _make_capture(capture, "ios_phone")
    stored = store_profile(
        platform="ios",
        profile_id="ios_phone",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_config=_config("ios_phone")["ios_phone"],
        native_environment=_environment("ios"),
        expected_key=_expected_key(repo, "ios", "ios_phone"),
    )
    metadata_path = Path(stored["cache_entry"]) / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata[field] = value
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    shutil.rmtree(capture)

    result = plan_cache(
        platform="ios",
        capture_root=capture,
        cache_root=cache,
        repo_root=repo,
        catalog_path=CATALOG_PATH,
        profile_configs=_config("ios_phone"),
        native_environment=_environment("ios"),
    )

    assert result["reused_profiles"] == []
    assert result["pending_profiles"] == ["ios_phone", "ios_large_tablet"]
    assert not capture.exists()
