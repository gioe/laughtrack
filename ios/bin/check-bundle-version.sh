#!/usr/bin/env bash
#
# Verify that ios/project.yml's CURRENT_PROJECT_VERSION (the LaughTrack app
# target's build number — the value that ends up in CFBundleVersion via the
# $(CURRENT_PROJECT_VERSION) substitution in Info.plist) has not decreased
# relative to a base ref. TestFlight rejects uploads whose CFBundleVersion is
# not strictly greater than the last accepted upload, so a silent decrease
# breaks the next release.
#
# Catches the failure mode from TASK-1902: xcodegen used to silently rewrite
# Info.plist's literal CFBundleVersion back to the project.yml default on
# every regen. The TASK-1902 fix moves the value into project.yml as the
# source of truth, but a manual decrement (bad merge resolution, accidental
# revert, etc.) would still slip through without this guard.
#
# Usage:
#   check-bundle-version.sh           # compares against origin/main (or BASE_REF)
#   BASE_REF=v1.1-3 check-bundle-version.sh
#
# Env:
#   BASE_REF  Git ref to compare against. Defaults to origin/main if it exists,
#             otherwise main, otherwise HEAD~1.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_YML="$IOS_DIR/project.yml"

if [[ ! -f "$PROJECT_YML" ]]; then
    echo "ERROR: $PROJECT_YML does not exist" >&2
    exit 2
fi

# Extract the LaughTrack app target's CURRENT_PROJECT_VERSION. project.yml today
# only defines this key under one target (LaughTrack), so a simple grep is
# sufficient — no YAML parser needed in CI. Scan every occurrence so a future
# engineer who adds CURRENT_PROJECT_VERSION to another target above LaughTrack
# can't silently shift this script onto the wrong target's value: collapse to
# unique values, accept iff exactly one, otherwise return non-zero so the caller
# can surface a clear "values diverged" error.
extract_version() {
    local content="$1"
    local values
    values="$(echo "$content" | grep -E '^\s*CURRENT_PROJECT_VERSION:' | sed -E 's/.*CURRENT_PROJECT_VERSION:[[:space:]]*"?([^"]*)"?.*/\1/' | sort -u)"
    if [[ -z "$values" ]]; then
        return 1
    fi
    if (( $(echo "$values" | wc -l) > 1 )); then
        echo "ERROR: multiple distinct CURRENT_PROJECT_VERSION values found in project.yml:" >&2
        echo "$values" | sed 's/^/  /' >&2
        echo "Reconcile manually — the LaughTrack app target's value is the one that ships to TestFlight." >&2
        return 2
    fi
    echo "$values"
}

extract_rc=0
current="$(extract_version "$(cat "$PROJECT_YML")")" || extract_rc=$?
if [[ $extract_rc -eq 1 ]]; then
    echo "ERROR: could not find CURRENT_PROJECT_VERSION in $PROJECT_YML" >&2
    exit 2
elif [[ $extract_rc -ne 0 ]]; then
    # extract_version already wrote its own diagnostic to stderr
    exit 2
fi

# Resolve the base ref to compare against.
if [[ -n "${BASE_REF:-}" ]]; then
    base_ref="$BASE_REF"
elif git -C "$IOS_DIR" rev-parse --verify --quiet origin/main >/dev/null; then
    base_ref="origin/main"
elif git -C "$IOS_DIR" rev-parse --verify --quiet main >/dev/null; then
    base_ref="main"
else
    base_ref="HEAD~1"
fi

if ! git -C "$IOS_DIR" rev-parse --verify --quiet "$base_ref" >/dev/null; then
    echo "WARNING: base ref '$base_ref' not resolvable — skipping check" >&2
    exit 0
fi

base_yml="$(git -C "$IOS_DIR" show "$base_ref:ios/project.yml" 2>/dev/null || true)"
if [[ -z "$base_yml" ]]; then
    echo "WARNING: ios/project.yml does not exist at $base_ref — skipping check" >&2
    exit 0
fi

base_extract_rc=0
base="$(extract_version "$base_yml")" || base_extract_rc=$?
if [[ $base_extract_rc -eq 1 ]]; then
    echo "WARNING: could not find CURRENT_PROJECT_VERSION at $base_ref — skipping check" >&2
    exit 0
elif [[ $base_extract_rc -ne 0 ]]; then
    # extract_version already wrote its own diagnostic; treat divergence at base
    # as a non-fatal warning so the comparison can still complete on HEAD.
    echo "WARNING: divergent CURRENT_PROJECT_VERSION values at $base_ref — skipping check" >&2
    exit 0
fi

# CFBundleVersion is a dotted-integer string. Compare numerically by splitting on
# dots and comparing component-wise; a non-integer component is a hard error.
version_compare() {
    local a="$1" b="$2"
    local IFS=.
    read -ra a_parts <<<"$a"
    read -ra b_parts <<<"$b"
    local n=${#a_parts[@]}
    if (( ${#b_parts[@]} > n )); then n=${#b_parts[@]}; fi
    for ((i = 0; i < n; i++)); do
        local ai="${a_parts[i]:-0}" bi="${b_parts[i]:-0}"
        if ! [[ "$ai" =~ ^[0-9]+$ && "$bi" =~ ^[0-9]+$ ]]; then
            echo "ERROR: CURRENT_PROJECT_VERSION must be a dotted-integer string, got '$a' vs '$b'" >&2
            exit 2
        fi
        if (( ai > bi )); then echo gt; return; fi
        if (( ai < bi )); then echo lt; return; fi
    done
    echo eq
}

cmp="$(version_compare "$current" "$base")"

case "$cmp" in
    lt)
        echo "ERROR: CURRENT_PROJECT_VERSION decreased: $base ($base_ref) -> $current (HEAD)" >&2
        echo "" >&2
        echo "TestFlight rejects uploads whose CFBundleVersion is not strictly greater than the" >&2
        echo "last accepted build. If this decrease is intentional (e.g. a fresh app record)," >&2
        echo "skip this check by editing the workflow or running with a later base ref." >&2
        exit 1
        ;;
    eq)
        echo "OK: CURRENT_PROJECT_VERSION unchanged at $current (vs $base_ref)"
        ;;
    gt)
        echo "OK: CURRENT_PROJECT_VERSION bumped $base ($base_ref) -> $current (HEAD)"
        ;;
esac
