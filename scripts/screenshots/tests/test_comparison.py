from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.screenshots.comparison import (
    PROFILE_ORDER,
    _load_runs,
    build_comparison,
    generate_sheets,
)
from scripts.screenshots.manifest import ContractError, SCENARIO_IDS, load_catalog


def test_generates_17_scenario_labeled_sheets_in_profile_order(tmp_path: Path, monkeypatch) -> None:
    groups = []
    for scenario in SCENARIO_IDS:
        groups.append({
            "scenario_id": scenario,
            "images": [
                {
                    "profile_id": profile,
                    "path": str(tmp_path / profile / f"{scenario}.png"),
                    "comparison_only": profile == "ios_large_tablet",
                    "shipping": profile != "ios_large_tablet",
                }
                for profile in PROFILE_ORDER
            ],
        })
    comparison = {"groups": groups}
    commands: list[list[str]] = []
    monkeypatch.setattr(
        "scripts.screenshots.comparison.subprocess.run",
        lambda command, check: commands.append(command),
    )

    font = tmp_path / "font.ttf"
    font.write_bytes(b"test font placeholder")
    generate_sheets(comparison, tmp_path / "sheets", font=font)

    assert len(commands) == 17
    assert [Path(group["sheet_path"]).stem for group in groups] == list(SCENARIO_IDS)
    expected_labels = [
        (
            "ios_large_tablet\ncomparison-only / non-shipping"
            if profile == "ios_large_tablet"
            else profile
        )
        for profile in PROFILE_ORDER
    ]
    assert [value for value in commands[0] if value in expected_labels] == expected_labels
    assert "ios_large_tablet\ncomparison-only / non-shipping" in commands[0]
    assert SCENARIO_IDS[0] in commands[0]
    assert commands[0][:3] == ["magick", "-font", str(font)]


def test_comparison_loader_requires_complete_manifests(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({}), encoding="utf-8")
    calls = []

    def reject_partial(*args, **kwargs):
        calls.append(kwargs)
        raise ContractError(["verification manifests are not complete runs"])

    monkeypatch.setattr("scripts.screenshots.comparison.validate_manifest", reject_partial)
    with pytest.raises(ContractError, match="not complete"):
        _load_runs(manifest, manifest, Path(__file__).resolve().parents[3] / "screenshots/catalog.json", None)

    assert calls[0]["require_complete"] is True


def test_comparison_json_exposes_normalized_profile_capabilities(
    tmp_path: Path, monkeypatch
) -> None:
    catalog = load_catalog(Path(__file__).resolve().parents[3] / "screenshots/catalog.json")
    profiles = {profile["id"]: profile for profile in catalog["profiles"]}
    captures = [
        {
            "profile_id": profile_id,
            "scenario_id": SCENARIO_IDS[0],
            "platform": profiles[profile_id]["platform"],
            "form_factor": profiles[profile_id]["form_factor"],
            "path": str(tmp_path / profile_id / f"{SCENARIO_IDS[0]}.png"),
            "width": 390,
            "height": 844,
            "comparison_only": profiles[profile_id]["comparison_only"],
            "shipping": profiles[profile_id]["shipping"],
            "audit_caveat": (
                "Comparison-only native iPad geometry; "
                "the shipping iOS target is iPhone-only."
                if profile_id == "ios_large_tablet"
                else None
            ),
        }
        for profile_id in PROFILE_ORDER
    ]
    provenance = {
        "git_revision": "0" * 40,
        "ios_manifest_sha256": "1" * 64,
        "android_manifest_sha256": "2" * 64,
    }
    monkeypatch.setattr(
        "scripts.screenshots.comparison._load_runs",
        lambda *args: (catalog, captures, provenance),
    )

    result = build_comparison(
        ios_manifest_path=tmp_path / "ios.json",
        android_manifest_path=tmp_path / "android.json",
        catalog_path=tmp_path / "catalog.json",
        scenario=SCENARIO_IDS[0],
        decode=lambda path: "3" * 64,
    )

    assert [profile["id"] for profile in result["profiles"]] == list(PROFILE_ORDER)
    ios_tablet = next(
        profile for profile in result["profiles"] if profile["id"] == "ios_large_tablet"
    )
    assert ios_tablet["comparison_only"] is True
    assert ios_tablet["shipping"] is False
    assert "iPhone-only" in ios_tablet["audit_caveat"]
    ios_tablet_image = next(
        image
        for image in result["groups"][0]["images"]
        if image["profile_id"] == "ios_large_tablet"
    )
    assert ios_tablet_image["comparison_only"] is True
    assert ios_tablet_image["shipping"] is False
