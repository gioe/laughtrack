from __future__ import annotations

import json
import struct
import zlib
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.screenshots.manifest import (
    ContractError,
    PROFILE_IDS,
    SCENARIO_IDS,
    expected_capture_keys,
    load_catalog,
    main,
    png_dimensions,
    validate_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "screenshots" / "catalog.json"
REVISION = "0123456789abcdef0123456789abcdef01234567"


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def write_png(path: Path, width: int, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IEND", b"")
    )


@pytest.fixture
def catalog() -> dict:
    return load_catalog(CATALOG_PATH)


@pytest.fixture
def completed_run(tmp_path: Path, catalog: dict) -> dict:
    profiles = ["android_phone", "android_small_tablet", "android_large_tablet"]
    dimensions = {
        "android_phone": (390, 844),
        "android_small_tablet": (800, 1280),
        "android_large_tablet": (1024, 1366),
    }
    images = []
    for profile_id, scenario_id in expected_capture_keys(catalog, profiles):
        profile = next(item for item in catalog["profiles"] if item["id"] == profile_id)
        width, height = dimensions[profile_id]
        relative_path = f"artifacts/run-1/{profile_id}/{scenario_id}.png"
        write_png(tmp_path / relative_path, width, height)
        images.append(
            {
                "path": relative_path,
                "scenario_id": scenario_id,
                "profile_id": profile_id,
                "platform": profile["platform"],
                "form_factor": profile["form_factor"],
                "width": width,
                "height": height,
                "captured_at": "2026-07-14T14:00:05Z",
                "git_revision": REVISION,
            }
        )
    return {
        "schema_version": 1,
        "status": "completed",
        "run_id": "run-1",
        "started_at": "2026-07-14T14:00:00Z",
        "completed_at": "2026-07-14T14:01:00Z",
        "git_revision": REVISION,
        "git_dirty": False,
        "profiles": profiles,
        "images": images,
    }


def test_checked_in_catalog_defines_exact_canonical_scenarios(catalog: dict) -> None:
    assert [scenario["id"] for scenario in catalog["scenarios"]] == list(SCENARIO_IDS)
    assert all(scenario["locale"] for scenario in catalog["scenarios"])
    assert all(scenario["timezone"] for scenario in catalog["scenarios"])
    assert all(scenario["capture_context"] for scenario in catalog["scenarios"])


def test_checked_in_catalog_defines_capture_profiles(catalog: dict) -> None:
    assert [profile["id"] for profile in catalog["profiles"]] == list(PROFILE_IDS)
    assert {(profile["platform"], profile["form_factor"]) for profile in catalog["profiles"]} == {
        ("ios", "phone"),
        ("ios", "large_tablet"),
        ("android", "phone"),
        ("android", "small_tablet"),
        ("android", "large_tablet"),
    }


def test_completed_platform_run_records_and_validates_every_image(
    tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    validate_manifest(completed_run, catalog, repo_root=tmp_path)
    assert len(completed_run["images"]) == 51


def test_png_dimensions_reads_ihdr(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    write_png(image, 390, 844)
    assert png_dimensions(image) == (390, 844)


def test_manifest_must_cover_the_exact_selected_corpus(
    tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    completed_run["images"].pop()
    with pytest.raises(ContractError, match="missing="):
        validate_manifest(completed_run, catalog, repo_root=tmp_path)


def test_manifest_requires_every_form_factor_for_selected_platform(
    tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    completed_run["profiles"] = ["android_phone"]
    completed_run["images"] = completed_run["images"][:18]
    with pytest.raises(ContractError, match="every form factor"):
        validate_manifest(completed_run, catalog, repo_root=tmp_path)


def test_manifest_rejects_duplicate_capture_key(
    tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    completed_run["images"][-1] = deepcopy(completed_run["images"][0])
    completed_run["images"][-1]["path"] = "artifacts/run-1/duplicate/01_NearMe.png"
    write_png(tmp_path / completed_run["images"][-1]["path"], 390, 844)
    with pytest.raises(ContractError, match="duplicates="):
        validate_manifest(completed_run, catalog, repo_root=tmp_path)


@pytest.mark.parametrize("field", ["profile_id", "scenario_id"])
def test_manifest_reports_non_string_capture_ids_without_crashing(
    field: str, tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    completed_run["images"][0][field] = 123
    with pytest.raises(ContractError, match=rf"{field} must be a string"):
        validate_manifest(completed_run, catalog, repo_root=tmp_path, require_files=False)


def test_manifest_rejects_noncanonical_image_order(
    tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    completed_run["images"][0], completed_run["images"][1] = (
        completed_run["images"][1],
        completed_run["images"][0],
    )
    with pytest.raises(ContractError, match="not in canonical order"):
        validate_manifest(completed_run, catalog, repo_root=tmp_path)


@pytest.mark.parametrize("field", ["platform", "form_factor"])
def test_manifest_identity_must_match_catalog_profile(
    field: str, tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    completed_run["images"][0][field] = "wrong"
    with pytest.raises(ContractError, match=rf"{field} does not match profile"):
        validate_manifest(completed_run, catalog, repo_root=tmp_path)


def test_manifest_rejects_dimension_mismatch(
    tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    completed_run["images"][0]["width"] = 391
    with pytest.raises(ContractError, match="do not match PNG"):
        validate_manifest(completed_run, catalog, repo_root=tmp_path)


def test_manifest_rejects_missing_or_non_png_file(
    tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    image = completed_run["images"][0]
    (tmp_path / image["path"]).write_text("not a PNG", encoding="utf-8")
    with pytest.raises(ContractError, match="not a readable PNG"):
        validate_manifest(completed_run, catalog, repo_root=tmp_path)


@pytest.mark.parametrize("path", ["/tmp/01_NearMe.png", "../01_NearMe.png", "bad\\01_NearMe.png"])
def test_manifest_rejects_unsafe_paths(
    path: str, tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    completed_run["images"][0]["path"] = path
    with pytest.raises(ContractError, match="safe repository-relative POSIX path"):
        validate_manifest(completed_run, catalog, repo_root=tmp_path)


def test_manifest_path_filename_must_match_scenario(
    tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    completed_run["images"][0]["path"] = "artifacts/run-1/android_phone/wrong.png"
    with pytest.raises(ContractError, match="filename must be 01_NearMe.png"):
        validate_manifest(completed_run, catalog, repo_root=tmp_path, require_files=False)


def test_manifest_rejects_mismatched_image_revision(
    tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    completed_run["images"][0]["git_revision"] = "f" * 40
    with pytest.raises(ContractError, match="does not match the run revision"):
        validate_manifest(completed_run, catalog, repo_root=tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("started_at", "2026-07-14T14:00:00", "must include a timezone offset"),
        ("completed_at", "2026-07-14T13:59:00Z", "must not precede"),
    ],
)
def test_manifest_rejects_invalid_run_times(
    field: str,
    value: str,
    message: str,
    tmp_path: Path,
    catalog: dict,
    completed_run: dict,
) -> None:
    completed_run[field] = value
    with pytest.raises(ContractError, match=message):
        validate_manifest(completed_run, catalog, repo_root=tmp_path)


def test_manifest_enforces_freshness_boundary(
    tmp_path: Path, catalog: dict, completed_run: dict
) -> None:
    boundary = datetime(2026, 7, 14, 14, 0, 1, tzinfo=timezone.utc)
    with pytest.raises(ContractError, match="freshness boundary"):
        validate_manifest(completed_run, catalog, repo_root=tmp_path, fresh_since=boundary)


def test_cli_validates_catalog(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate-catalog", "--catalog", str(CATALOG_PATH)]) == 0
    assert "valid catalog: 17 scenarios" in capsys.readouterr().out


def test_cli_plan_emits_canonical_profile_scenario_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(
            [
                "plan",
                "--catalog",
                str(CATALOG_PATH),
                "--profile",
                "ios_phone",
                "--profile",
                "ios_large_tablet",
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert len(plan) == 34
    assert plan[0] == {"profile_id": "ios_phone", "scenario_id": "01_NearMe"}
    assert plan[-1] == {
        "profile_id": "ios_large_tablet",
        "scenario_id": "19_FirstEntryAuthChoice",
    }


def test_catalog_keeps_valid_guest_authenticated_and_auth_prompt_scenarios_distinct(catalog: dict) -> None:
    contexts = {scenario["id"]: scenario["capture_context"] for scenario in catalog["scenarios"]}

    assert "10_Favorites" not in contexts
    assert contexts["15_AuthenticatedFavorites"] == {
        "screen": "favorites",
        "auth_state": "authenticated",
        "persona": "screenshot-persona",
    }
    assert "12_Notifications" not in contexts
    assert contexts["17_AuthenticatedNotifications"] == {
        "screen": "notifications",
        "auth_state": "authenticated",
        "persona": "screenshot-persona",
    }

    assert contexts["11_Profile"]["auth_state"] == "guest"
    assert contexts["16_AuthenticatedProfile"] == {
        "screen": contexts["11_Profile"]["screen"],
        "auth_state": "authenticated",
        "persona": "screenshot-persona",
    }

    assert contexts["18_AuthPrompt"] == {
        "screen": "auth_prompt",
        "auth_state": "guest",
        "presentation": "in_app_modal",
    }
    assert contexts["19_FirstEntryAuthChoice"] == {
        "screen": "first_entry_auth_choice",
        "auth_state": "guest",
        "presentation": "full_screen",
        "state": "unresolved",
    }


def test_cli_plan_rejects_partial_platform_matrix(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(
            [
                "plan",
                "--catalog",
                str(CATALOG_PATH),
                "--profile",
                "ios_phone",
            ]
        )
        == 1
    )
    assert "every form factor" in capsys.readouterr().err
