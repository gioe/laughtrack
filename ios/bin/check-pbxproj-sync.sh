#!/usr/bin/env bash
#
# Verify every Swift file under ios/Sources/ is referenced as a PBXFileReference
# in ios/LaughTrack.xcodeproj/project.pbxproj. Exits non-zero with a clear
# "run xcodegen generate" hint when a file is missing.
#
# This catches the failure mode from TASK-1764: a new source file was added but
# xcodegen was never re-run, leaving xcodebuild broken on main while
# `swift build` (SPM) still passed locally.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCES_DIR="$IOS_DIR/Sources"
PBXPROJ="$IOS_DIR/LaughTrack.xcodeproj/project.pbxproj"

if [[ ! -d "$SOURCES_DIR" ]]; then
    echo "ERROR: $SOURCES_DIR does not exist" >&2
    exit 2
fi

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
        missing+=("${file#"$IOS_DIR"/}")
    fi
done < <(find "$SOURCES_DIR" -name '*.swift' -print0)

if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: ${#missing[@]} Swift file(s) under ios/Sources/ are not wired into LaughTrack.xcodeproj/project.pbxproj:" >&2
    for f in "${missing[@]}"; do
        echo "  - $f" >&2
    done
    echo "" >&2
    echo "These files build under 'swift build' (SPM) but xcodebuild will fail" >&2
    echo "with 'cannot find <Type> in scope' until the Xcode project is regenerated." >&2
    echo "" >&2
    echo "Fix: run 'xcodegen generate' from ios/ and commit the updated project.pbxproj." >&2
    exit 1
fi

echo "OK: all $total Swift file(s) under ios/Sources/ are wired into project.pbxproj"
