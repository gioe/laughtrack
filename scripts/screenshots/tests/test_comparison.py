from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.screenshots.comparison import PROFILE_ORDER, _load_runs, generate_sheets
from scripts.screenshots.manifest import ContractError, SCENARIO_IDS


def test_generates_17_scenario_labeled_sheets_in_profile_order(tmp_path: Path, monkeypatch) -> None:
    groups = []
    for scenario in SCENARIO_IDS:
        groups.append({
            "scenario_id": scenario,
            "images": [
                {"profile_id": profile, "path": str(tmp_path / profile / f"{scenario}.png")}
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
    assert [value for value in commands[0] if value in PROFILE_ORDER] == list(PROFILE_ORDER)
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
