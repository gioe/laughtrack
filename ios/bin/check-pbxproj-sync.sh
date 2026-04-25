#!/usr/bin/env bash
#
# Verify every Swift file under ios/Sources/ and ios/Tests/ is referenced as a
# PBXFileReference in ios/LaughTrack.xcodeproj/project.pbxproj. Exits non-zero
# with a clear "run xcodegen generate" hint when a file is missing.
#
# This catches the failure mode from TASK-1764 (a new source file was added but
# xcodegen was never re-run, leaving xcodebuild broken on main while
# `swift build` (SPM) still passed locally) and the same gap for new test files
# under ios/Tests/, which would silently skip from xcodebuild test runs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCES_DIR="$IOS_DIR/Sources"
TESTS_DIR="$IOS_DIR/Tests"
PBXPROJ="$IOS_DIR/LaughTrack.xcodeproj/project.pbxproj"

for dir in "$SOURCES_DIR" "$TESTS_DIR"; do
    if [[ ! -d "$dir" ]]; then
        echo "ERROR: $dir does not exist" >&2
        exit 2
    fi
done

if [[ ! -f "$PBXPROJ" ]]; then
    echo "ERROR: $PBXPROJ does not exist" >&2
    exit 2
fi

missing=()
total=0
while IFS= read -r -d '' file; do
    total=$((total + 1))
    bn="$(basename "$file")"
    # PBXFileReference path entries store basenames only, e.g.
    #   path = AuthenticatedUser.swift;
    # Match both quoted and unquoted forms.
    if ! grep -qE "path = \"?${bn//./\\.}\"?[[:space:]]*;" "$PBXPROJ"; then
        # Strip $IOS_DIR/ prefix so the printed path starts with "Sources/" or
        # "Tests/" — naming the affected directory for each missing file.
        missing+=("${file#"$IOS_DIR"/}")
    fi
done < <(find "$SOURCES_DIR" "$TESTS_DIR" -name '*.swift' -print0)

if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: ${#missing[@]} Swift file(s) under ios/Sources/ or ios/Tests/ are not wired into LaughTrack.xcodeproj/project.pbxproj:" >&2
    for f in "${missing[@]}"; do
        echo "  - $f" >&2
    done
    echo "" >&2
    echo "These files build under 'swift build' (SPM) but xcodebuild (build or test) will fail" >&2
    echo "with 'cannot find <Type> in scope' until the Xcode project is regenerated." >&2
    echo "" >&2
    echo "Fix: run 'xcodegen generate' from ios/ and commit the updated project.pbxproj." >&2
    exit 1
fi

echo "OK: all $total Swift file(s) under ios/Sources/ and ios/Tests/ are wired into project.pbxproj"
