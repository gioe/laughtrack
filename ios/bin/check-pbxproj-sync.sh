#!/usr/bin/env bash
#
# Two drift checks against ios/LaughTrack.xcodeproj/project.pbxproj:
#
# 1. Every Swift file under ios/Sources/ and ios/Tests/ is referenced as a
#    PBXFileReference. Catches the TASK-1764 failure mode where a new source
#    file built under `swift build` (SPM) but xcodebuild was missing it after
#    a forgotten `xcodegen generate`. Same gap exists for new test files under
#    ios/Tests/, which would silently skip from xcodebuild test runs.
#
# 2. The LaughTrack app target's CURRENT_PROJECT_VERSION in the pbxproj agrees
#    with the value in ios/project.yml. The bundle-version guard at
#    .github/workflows/ios-bundle-version.yml only watches project.yml +
#    Info.plist + check-bundle-version.sh — a hand-edited pbxproj or a stale
#    pbxproj from a regen against an older project.yml can desync from
#    project.yml without that workflow firing, and xcodebuild reads
#    CURRENT_PROJECT_VERSION from the pbxproj at archive time.
#
# Both checks emit a "run xcodegen generate" hint on failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCES_DIR="$IOS_DIR/Sources"
TESTS_DIR="$IOS_DIR/Tests"
PROJECT_YML="$IOS_DIR/project.yml"
PBXPROJ="$IOS_DIR/LaughTrack.xcodeproj/project.pbxproj"

for dir in "$SOURCES_DIR" "$TESTS_DIR"; do
    if [[ ! -d "$dir" ]]; then
        echo "ERROR: $dir does not exist" >&2
        exit 2
    fi
done

if [[ ! -f "$PROJECT_YML" ]]; then
    echo "ERROR: $PROJECT_YML does not exist" >&2
    exit 2
fi

if [[ ! -f "$PBXPROJ" ]]; then
    echo "ERROR: $PBXPROJ does not exist" >&2
    exit 2
fi

fail_rc=0

# ----------------------------------------------------------------------------
# Check 1: Swift source/test files referenced in pbxproj
# ----------------------------------------------------------------------------
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
    fail_rc=1
else
    echo "OK: all $total Swift file(s) under ios/Sources/ and ios/Tests/ are wired into project.pbxproj"
fi

# ----------------------------------------------------------------------------
# Check 2: CURRENT_PROJECT_VERSION agrees between project.yml and pbxproj
# (LaughTrack app target only)
# ----------------------------------------------------------------------------
# project.yml today only declares CURRENT_PROJECT_VERSION under the LaughTrack
# app target; sort -u across all hits accepts that and rejects a future
# multi-target divergence.
yml_version="$(grep -E '^[[:space:]]*CURRENT_PROJECT_VERSION:' "$PROJECT_YML" \
    | sed -E 's/.*CURRENT_PROJECT_VERSION:[[:space:]]*"?([^"]*)"?.*/\1/' \
    | sort -u)"

if [[ -z "$yml_version" ]]; then
    echo "ERROR: could not find CURRENT_PROJECT_VERSION in $PROJECT_YML" >&2
    exit 2
fi
if (( $(echo "$yml_version" | wc -l) > 1 )); then
    echo "ERROR: multiple distinct CURRENT_PROJECT_VERSION values in project.yml:" >&2
    echo "$yml_version" | sed 's/^/  /' >&2
    echo "Reconcile manually — the LaughTrack app target's value is the one that ships to TestFlight." >&2
    fail_rc=1
else
    # XCBuildConfiguration blocks for the LaughTrack app target are uniquely
    # identified by `PRODUCT_MODULE_NAME = LaughTrackApp;` (framework targets
    # don't set this). For each such block, capture CURRENT_PROJECT_VERSION.
    # Framework configs default to CURRENT_PROJECT_VERSION = 1 from xcodegen
    # (project.yml doesn't override them) and are intentionally skipped — only
    # the app target's value ships to TestFlight as CFBundleVersion.
    pbx_versions="$(awk '
    /isa = XCBuildConfiguration;/ { in_block=1; is_app=0; version=""; next }
    in_block && /PRODUCT_MODULE_NAME = LaughTrackApp;/ { is_app=1 }
    in_block && /CURRENT_PROJECT_VERSION = / {
        v = $0
        sub(/^[^=]*= /, "", v)
        sub(/;.*$/, "", v)
        gsub(/"/, "", v)
        version = v
    }
    in_block && /^[[:space:]]*};[[:space:]]*$/ {
        if (is_app && version != "") print version
        in_block=0
    }
    ' "$PBXPROJ" | sort -u)"

    if [[ -z "$pbx_versions" ]]; then
        echo "ERROR: could not find CURRENT_PROJECT_VERSION on the LaughTrack app target in project.pbxproj" >&2
        echo "Expected an XCBuildConfiguration block containing both PRODUCT_MODULE_NAME = LaughTrackApp; and CURRENT_PROJECT_VERSION = ...;" >&2
        fail_rc=1
    elif (( $(echo "$pbx_versions" | wc -l) > 1 )); then
        echo "ERROR: Debug and Release CURRENT_PROJECT_VERSION values disagree on the LaughTrack app target in project.pbxproj:" >&2
        echo "$pbx_versions" | sed 's/^/  /' >&2
        echo "Fix: run 'xcodegen generate' from ios/ and commit the updated project.pbxproj." >&2
        fail_rc=1
    elif [[ "$yml_version" != "$pbx_versions" ]]; then
        echo "ERROR: CURRENT_PROJECT_VERSION drift between project.yml and project.pbxproj on the LaughTrack app target:" >&2
        echo "  project.yml:     $yml_version" >&2
        echo "  project.pbxproj: $pbx_versions" >&2
        echo "" >&2
        echo "The bundle-version guard at .github/workflows/ios-bundle-version.yml only watches" >&2
        echo "project.yml + Info.plist + check-bundle-version.sh; a stale pbxproj would not trip" >&2
        echo "it, but xcodebuild reads CURRENT_PROJECT_VERSION from the pbxproj at archive time." >&2
        echo "" >&2
        echo "Fix: run 'xcodegen generate' from ios/ and commit the updated project.pbxproj." >&2
        fail_rc=1
    else
        echo "OK: CURRENT_PROJECT_VERSION matches in project.yml and project.pbxproj (LaughTrack app target = $yml_version)"
    fi
fi

exit $fail_rc
