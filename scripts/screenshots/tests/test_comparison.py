from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.screenshots.comparison import (
    PROFILE_ORDER,
    _load_runs,
    build_comparison,
    generate_sheets,
)
from scripts.screenshots.manifest import ContractError, SCENARIO_IDS, load_catalog

REPO_ROOT = Path(__file__).resolve().parents[3]
REGENERATE_SCRIPT = REPO_ROOT / "scripts" / "screenshots" / "regenerate-comparisons"


def _executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _checkout_fixture(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", str(remote)],
        check=True,
        capture_output=True,
    )
    repo = tmp_path / "checkout"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "screenshots@example.com")
    _git(repo, "config", "user.name", "Screenshot Tests")
    script = repo / "scripts" / "screenshots" / "regenerate-comparisons"
    script.parent.mkdir(parents=True)
    shutil.copy2(REGENERATE_SCRIPT, script)
    for helper in ("cache.py", "manifest.py"):
        (script.parent / helper).write_text("", encoding="utf-8")
    (script.parent / "comparison.py").write_text(
        'print("{}")\n',
        encoding="utf-8",
    )
    lane = """#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
for argument in "$@"; do
  case "$argument" in
    run_root:*) run_root="${argument#run_root:}" ;;
  esac
done
mkdir -p "$run_root"
printf '{}\n' > "$run_root/manifest.json"
if [[ "${LAUGHTRACK_TEST_MUTATE_DURING_CAPTURE:-}" == "true" ]]; then
  printf 'changed during capture\n' > "$repo_root/capture-change.txt"
fi
"""
    _executable(repo / "ios" / "bin" / "lane", lane)
    _executable(repo / "android" / "bin" / "lane", lane)
    for command in ("xcrun", "adb", "magick"):
        _executable(repo / "test-bin" / command, "#!/usr/bin/env bash\nexit 0\n")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "branch", "-M", "main")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-qu", "origin", "main")
    return repo, remote


def _run_preflight(
    repo: Path,
    output: Path,
    *,
    audit_mode: str = "current-main",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(repo / "scripts" / "screenshots" / "regenerate-comparisons"),
            "--audit-mode",
            audit_mode,
            "--output-root",
            str(output),
            "--preflight-only",
            "--no-open",
        ],
        capture_output=True,
        text=True,
    )


def _run_capture(
    repo: Path,
    output: Path,
    *,
    mutate_during_capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PATH"] = f"{repo / 'test-bin'}:{environment['PATH']}"
    if mutate_during_capture:
        environment["LAUGHTRACK_TEST_MUTATE_DURING_CAPTURE"] = "true"
    return subprocess.run(
        [
            str(repo / "scripts" / "screenshots" / "regenerate-comparisons"),
            "--audit-mode",
            "explicit-checkout",
            "--output-root",
            str(output),
            "--no-open",
        ],
        capture_output=True,
        text=True,
        env=environment,
    )


def test_current_main_preflight_records_clean_exact_checkout(tmp_path: Path) -> None:
    repo, _ = _checkout_fixture(tmp_path)
    output = tmp_path / "output"

    result = _run_preflight(repo, output)

    assert result.returncode == 0, result.stderr
    provenance = json.loads((output / "checkout-provenance.json").read_text())
    assert provenance["audit_mode"] == "current-main"
    assert provenance["audit_label"] == "CURRENT MAIN"
    assert provenance["branch"] == "main"
    assert provenance["detached"] is False
    assert provenance["dirty"] is False
    assert provenance["origin_main_refreshed"] is True
    assert provenance["relationship"] == "exact"
    assert provenance["ahead_by"] == 0
    assert provenance["behind_by"] == 0
    assert "revision:" in result.stdout
    assert "branch: main" in result.stdout


def test_current_main_preflight_refuses_dirty_checkout(tmp_path: Path) -> None:
    repo, _ = _checkout_fixture(tmp_path)
    (repo / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")

    result = _run_preflight(repo, tmp_path / "output")

    assert result.returncode != 0
    assert "current-main audits require a clean checkout" in result.stderr
    assert "--audit-mode explicit-checkout" in result.stderr
    assert "dirty: true" in result.stdout


def test_current_main_preflight_refuses_divergent_checkout(tmp_path: Path) -> None:
    repo, remote = _checkout_fixture(tmp_path)
    (repo / "local.txt").write_text("local\n", encoding="utf-8")
    _git(repo, "add", "local.txt")
    _git(repo, "commit", "-qm", "local")

    other = tmp_path / "other"
    subprocess.run(
        ["git", "clone", "-q", str(remote), str(other)],
        check=True,
        capture_output=True,
    )
    _git(other, "config", "user.email", "screenshots@example.com")
    _git(other, "config", "user.name", "Screenshot Tests")
    (other / "remote.txt").write_text("remote\n", encoding="utf-8")
    _git(other, "add", "remote.txt")
    _git(other, "commit", "-qm", "remote")
    _git(other, "push", "-q", "origin", "main")

    result = _run_preflight(repo, tmp_path / "output")

    assert result.returncode != 0
    assert "found diverged: ahead 1, behind 1" in result.stderr
    assert "relationship: diverged (ahead 1, behind 1)" in result.stdout


def test_explicit_checkout_preflight_allows_and_labels_dirty_feature_branch(
    tmp_path: Path,
) -> None:
    repo, _ = _checkout_fixture(tmp_path)
    _git(repo, "switch", "-qc", "feature/audit")
    (repo / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
    output = tmp_path / "output"

    result = _run_preflight(repo, output, audit_mode="explicit-checkout")

    assert result.returncode == 0, result.stderr
    provenance = json.loads((output / "checkout-provenance.json").read_text())
    assert provenance["audit_mode"] == "explicit-checkout"
    assert provenance["audit_label"] == "EXPLICIT CHECKOUT (not current-main certified)"
    assert provenance["branch"] == "feature/audit"
    assert provenance["dirty"] is True
    assert provenance["origin_main_refreshed"] is False
    assert "not current-main certified" in result.stdout


def test_dirty_explicit_checkout_rejects_additional_capture_time_changes(
    tmp_path: Path,
) -> None:
    repo, _ = _checkout_fixture(tmp_path)
    (repo / "starting-dirty.txt").write_text("dirty before capture\n", encoding="utf-8")
    output = tmp_path / "output"

    result = _run_capture(repo, output, mutate_during_capture=True)

    assert result.returncode != 0
    assert "checkout changed during screenshot capture" in result.stderr
    provenance = json.loads((output / "checkout-provenance.json").read_text())
    assert provenance["status"] == "preflight_passed"
    assert "checkout_unchanged" not in provenance


def test_generates_18_scenario_labeled_sheets_in_profile_order(tmp_path: Path, monkeypatch) -> None:
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

    assert len(commands) == 18
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
