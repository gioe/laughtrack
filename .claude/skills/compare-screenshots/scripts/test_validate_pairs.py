from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest

from validate_pairs import PROFILE_ORDER, build_comparison, write_reviewed_baseline
from scripts.screenshots.manifest import SCENARIO_IDS, content_fixture_fingerprint, load_catalog

REPO_ROOT = Path(__file__).resolve().parents[4]
CATALOG = REPO_ROOT / "screenshots/catalog.json"
REVISION = "0123456789abcdef0123456789abcdef01234567"


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _png(path: Path, width: int, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IEND", b""))


def _run(root: Path, platform: str) -> Path:
    catalog = load_catalog(CATALOG)
    profiles = [p for p in catalog["profiles"] if p["platform"] == platform]
    images = []
    for profile in profiles:
        width, height = ((390, 844) if profile["form_factor"] == "phone" else (800, 1280))
        cache_key = ("a" if platform == "ios" else "b") * 64
        for scenario in SCENARIO_IDS:
            relative = f"images/{profile['id']}/{scenario}.png"
            _png(root / relative, width, height)
            images.append({
                "path": relative, "scenario_id": scenario, "profile_id": profile["id"],
                "platform": platform, "form_factor": profile["form_factor"],
                "width": width, "height": height, "captured_at": "2026-07-15T14:00:05Z",
                "materialized_at": "2026-07-15T14:00:06Z", "capture_git_revision": REVISION,
                "capture_git_dirty": False, "provenance": "capture", "cache_key": cache_key,
            })
    manifest = {
        "schema_version": 2, "status": "completed", "run_id": f"{platform}-run",
        "started_at": "2026-07-15T14:00:00Z", "completed_at": "2026-07-15T14:01:00Z",
        "git_revision": REVISION, "git_dirty": False,
        "content_fixture_fingerprint": content_fixture_fingerprint(catalog),
        "profiles": [p["id"] for p in profiles], "images": images,
    }
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


@pytest.fixture
def manifests(tmp_path: Path) -> tuple[Path, Path]:
    return _run(tmp_path / "ios", "ios"), _run(tmp_path / "android", "android")


def _build(manifests: tuple[Path, Path], baseline: Path | None = None, decode=None):
    kwargs = {}
    if decode is not None:
        kwargs["decode"] = decode
    return build_comparison(
        ios_manifest_path=manifests[0], android_manifest_path=manifests[1],
        catalog_path=CATALOG, baseline_path=baseline, **kwargs,
    )


def test_first_audit_requires_all_17_sheets_in_canonical_order(manifests) -> None:
    result = _build(manifests, decode=lambda path: "1" * 64)
    assert [g["scenario_id"] for g in result["groups"]] == list(SCENARIO_IDS)
    assert all(g["review_required"] for g in result["groups"])
    assert [i["profile_id"] for i in result["groups"][0]["images"]] == list(PROFILE_ORDER)


def test_reviewed_baseline_skips_identical_groups_and_reopens_only_delta(manifests, tmp_path) -> None:
    baseline = tmp_path / "reviewed.json"
    initial = _build(manifests, decode=lambda path: "1" * 64)
    write_reviewed_baseline(initial, baseline, "test reviewer")
    unchanged = _build(manifests, baseline, decode=lambda path: "1" * 64)
    assert not any(g["review_required"] for g in unchanged["groups"])

    changed_path = f"{SCENARIO_IDS[3]}.png"
    changed = _build(
        manifests, baseline,
        decode=lambda path: "2" * 64 if path.name == changed_path and "ios_phone" in str(path) else "1" * 64,
    )
    assert [g["scenario_id"] for g in changed["groups"] if g["review_required"]] == [SCENARIO_IDS[3]]


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(status="draft"),
    lambda value: value.update(catalog_sha256="0" * 64),
    lambda value: value["source_provenance"].pop("ios_manifest_sha256"),
    lambda value: value["captures"].pop(),
])
def test_invalid_or_incomplete_baseline_never_silently_skips(manifests, tmp_path, mutation) -> None:
    baseline = tmp_path / "reviewed.json"
    write_reviewed_baseline(_build(manifests, decode=lambda path: "1" * 64), baseline, "reviewer")
    value = json.loads(baseline.read_text())
    mutation(value)
    baseline.write_text(json.dumps(value))
    result = _build(manifests, baseline, decode=lambda path: "1" * 64)
    assert any(g["review_required"] for g in result["groups"])


def test_partial_comparison_cannot_be_approved(manifests, tmp_path) -> None:
    result = build_comparison(
        ios_manifest_path=manifests[0], android_manifest_path=manifests[1],
        catalog_path=CATALOG, scenario=SCENARIO_IDS[0], decode=lambda path: "1" * 64,
    )
    with pytest.raises(Exception, match="complete canonical scenario set"):
        write_reviewed_baseline(result, tmp_path / "baseline.json", "reviewer")
