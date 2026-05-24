#!/usr/bin/env bash
#
# Three drift checks against ios/LaughTrack.xcodeproj/project.pbxproj and
# ios/Sources/LaughTrackApp/Info.plist:
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
# 3. ios/Sources/LaughTrackApp/Info.plist matches what `xcodegen generate`
#    materializes from ios/project.yml info.properties. Catches the TASK-2420
#    failure mode where UIBackgroundModes/audio was added directly to
#    Info.plist without a matching entry in project.yml; xcodegen silently
#    stripped it on every regen, dirtying the working tree until TASK-2430
#    backfilled the YAML.
#
# Checks 1 and 2 emit a "run xcodegen generate" hint on failure; check 3
# emits a "declare the key in project.yml info.properties" hint.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCES_DIR="$IOS_DIR/Sources"
TESTS_DIR="$IOS_DIR/Tests"
PROJECT_YML="$IOS_DIR/project.yml"
PBXPROJ="$IOS_DIR/LaughTrack.xcodeproj/project.pbxproj"
INFO_PLIST="$IOS_DIR/Sources/LaughTrackApp/Info.plist"

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

if [[ ! -f "$INFO_PLIST" ]]; then
    echo "ERROR: $INFO_PLIST does not exist" >&2
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

# ----------------------------------------------------------------------------
# Check 3: Info.plist matches what xcodegen materializes from project.yml
# ----------------------------------------------------------------------------
# project.yml's `info: properties:` block under the LaughTrack target is the
# source of truth for every Info.plist key that doesn't come from a build
# setting. `xcodegen generate` rewrites Info.plist from that block on every
# run; any key added directly to Info.plist without a matching entry in
# info.properties is silently stripped on the next regen.
#
# Snapshot Info.plist and project.pbxproj before invoking xcodegen, then
# restore both on exit so the check is non-destructive — running it never
# leaves the working tree dirty regardless of whether drift was detected.
#
# xcodegen is required to make this check meaningful, but the existing CI
# runner (ubuntu-latest, ios-pbxproj-sync.yml) does not install it. Skip
# with a WARN rather than hard-failing so the check is opt-in based on
# environment until CI is updated.
if ! command -v xcodegen >/dev/null 2>&1; then
    echo "WARN: xcodegen not found on PATH — skipping Info.plist drift check"
    echo "      install via 'brew install xcodegen' to enable this check"
else
    plist_snapshot="$(mktemp)"
    pbxproj_snapshot="$(mktemp)"
    xcodegen_log="$(mktemp)"
    cp "$INFO_PLIST" "$plist_snapshot"
    cp "$PBXPROJ" "$pbxproj_snapshot"

    restore_snapshots() {
        cp "$plist_snapshot" "$INFO_PLIST"
        cp "$pbxproj_snapshot" "$PBXPROJ"
        rm -f "$plist_snapshot" "$pbxproj_snapshot" "$xcodegen_log"
    }
    trap restore_snapshots EXIT

    if ! (cd "$IOS_DIR" && xcodegen generate) >"$xcodegen_log" 2>&1; then
        echo "ERROR: xcodegen generate failed while running Info.plist drift check:" >&2
        sed 's/^/  /' "$xcodegen_log" >&2
        fail_rc=1
    else
        if ! diff -q "$plist_snapshot" "$INFO_PLIST" >/dev/null; then
            echo "ERROR: Info.plist drift between ios/project.yml info.properties and ios/Sources/LaughTrackApp/Info.plist:" >&2
            # Show xcodegen output on the LEFT and on-disk on the RIGHT so '+' lines
            # name keys present on-disk but missing from project.yml info.properties —
            # that's exactly what the user needs to add to YAML.
            diff -u -L "Info.plist (xcodegen output from project.yml)" -L "Info.plist (on-disk)" "$INFO_PLIST" "$plist_snapshot" | sed 's/^/  /' >&2
            echo "" >&2
            echo "xcodegen rewrote Info.plist from project.yml info.properties. Any key only present" >&2
            echo "in the on-disk Info.plist (or with a different value) was added/edited without a" >&2
            echo "matching entry in info.properties, and would be silently stripped on the next" >&2
            echo "'xcodegen generate' (the TASK-2420 footgun: UIBackgroundModes/audio was added to" >&2
            echo "Info.plist directly, then dropped on every regen until TASK-2430 backfilled YAML)." >&2
            echo "" >&2
            echo "Fix: declare the key in ios/project.yml info.properties (under the LaughTrack" >&2
            echo "target's 'info: properties:' block), then run 'xcodegen generate' from ios/ and" >&2
            echo "commit the updated project.pbxproj and Info.plist." >&2
            fail_rc=1
        else
            echo "OK: Info.plist matches xcodegen output from project.yml info.properties"
        fi
    fi
fi

exit $fail_rc
