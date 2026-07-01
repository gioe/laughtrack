#!/usr/bin/env python3
"""Smoke-test Tusk review-size filtering for generated review-noise files."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / ".claude" / "bin" / "tusk-git-helpers.py"


def _load_helpers():
    spec = importlib.util.spec_from_file_location("tusk_git_helpers", HELPERS)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import {HELPERS}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    helpers = _load_helpers()
    diff = """diff --git a/src/app.py b/src/app.py
+hand authored
diff --git a/package-lock.json b/package-lock.json
+lock noise
diff --git a/ios/Sources/LaughTrackAPIClient/GeneratedSources/Client.swift b/ios/Sources/LaughTrackAPIClient/GeneratedSources/Client.swift
+swift generated
diff --git a/ios/Sources/LaughTrackAPIClient/Extensions.swift b/ios/Sources/LaughTrackAPIClient/Extensions.swift
+swift hand authored
diff --git a/android/core/network/src/main/kotlin/app/laughtrack/android/core/network/generated/api/HomeApi.kt b/android/core/network/src/main/kotlin/app/laughtrack/android/core/network/generated/api/HomeApi.kt
+kotlin generated
diff --git a/android/core/network/src/main/kotlin/app/laughtrack/android/core/network/profile/ProfileSettingsApi.kt b/android/core/network/src/main/kotlin/app/laughtrack/android/core/network/profile/ProfileSettingsApi.kt
+kotlin hand authored
"""
    filtered = helpers.filter_generated_review_noise_diff_sections(diff)
    assert "+hand authored" in filtered
    assert "+swift hand authored" in filtered
    assert "+kotlin hand authored" in filtered
    assert "lock noise" not in filtered
    assert "swift generated" not in filtered
    assert "kotlin generated" not in filtered
    assert helpers.filter_lockfile_diff_sections(diff) == filtered
    print("generated review-noise filter smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
