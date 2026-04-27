#!/usr/bin/env bash
#
# Verify the ios-libs revision pin is identical across the three places that
# can independently resolve it:
#
#   1. ios/project.yml                                                  (xcodegen → xcodeproj)
#   2. ios/Package.resolved                                             (swift build)
#   3. ios/LaughTrack.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved
#                                                                       (xcodebuild)
#
# When these drift, xcodebuild and `swift build` resolve different revisions
# of ios-libs and the build silently fails with an unrelated-looking error
# (TASK-1807 → TASK-1819 hit "OfflineOperationError has no member terminal"
# because project.yml stayed on the old commit while both Package.resolved
# files moved forward). This guard catches that drift before push/CI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_YML="$IOS_DIR/project.yml"
SPM_RESOLVED="$IOS_DIR/Package.resolved"
XCODE_RESOLVED="$IOS_DIR/LaughTrack.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"

for f in "$PROJECT_YML" "$SPM_RESOLVED" "$XCODE_RESOLVED"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: $f does not exist" >&2
        exit 2
    fi
done

# Single python3 invocation: parses all three files and prints three lines,
# one revision each, in fixed order (project.yml, spm, xcode). Exits non-zero
# with a descriptive error if any source is missing the ios-libs pin.
read -r project_yml_rev spm_rev xcode_rev < <(python3 - "$PROJECT_YML" "$SPM_RESOLVED" "$XCODE_RESOLVED" <<'PY'
import json
import re
import sys

project_yml_path, spm_path, xcode_path = sys.argv[1:4]


def project_yml_revision(path: str) -> str:
    text = open(path).read()
    # Match the ios-libs package block: a `  ios-libs:` header at indent 2,
    # followed by indented child lines until the next sibling at indent 2 or
    # less. Pulls the `revision:` field from inside that block.
    block = re.search(
        r"^  ios-libs:[ \t]*\n((?:    [^\n]*\n)+)",
        text,
        re.MULTILINE,
    )
    if not block:
        sys.exit(f"ERROR: could not find ios-libs package block in {path}")
    rev = re.search(r"^    revision:[ \t]*(\S+)", block.group(1), re.MULTILINE)
    if not rev:
        sys.exit(f"ERROR: ios-libs in {path} has no revision pin")
    return rev.group(1)


def resolved_revision(path: str) -> str:
    with open(path) as f:
        data = json.load(f)
    for pin in data.get("pins", []):
        if pin.get("identity") == "ios-libs":
            rev = pin.get("state", {}).get("revision")
            if not rev:
                sys.exit(f"ERROR: ios-libs pin in {path} has no state.revision")
            return rev
    sys.exit(f"ERROR: ios-libs pin missing from {path}")


print(project_yml_revision(project_yml_path), resolved_revision(spm_path), resolved_revision(xcode_path))
PY
) || exit $?

if [[ "$project_yml_rev" == "$spm_rev" && "$project_yml_rev" == "$xcode_rev" ]]; then
    echo "OK: ios-libs revision pinned consistently to $project_yml_rev across project.yml and both Package.resolved files."
    exit 0
fi

echo "ERROR: ios-libs revision pin drift detected:" >&2
printf "  %-65s %s\n" "ios/project.yml:"                                                  "$project_yml_rev"  >&2
printf "  %-65s %s\n" "ios/Package.resolved:"                                             "$spm_rev"          >&2
printf "  %-65s %s\n" "ios/LaughTrack.xcodeproj/.../swiftpm/Package.resolved:"            "$xcode_rev"        >&2
echo "" >&2
echo "xcodegen reads project.yml; xcodebuild also reads the xcodeproj's Package.resolved." >&2
echo "swift build reads ios/Package.resolved. A mismatch causes builds to silently resolve" >&2
echo "different ios-libs revisions across tools — the failure mode that broke TASK-1807." >&2
echo "" >&2
echo "Fix: align all three by updating project.yml's revision to match the resolved" >&2
echo "revision, then run 'xcodegen generate' from ios/. Or re-resolve by deleting both" >&2
echo "Package.resolved files and running 'swift package resolve'." >&2
exit 1
