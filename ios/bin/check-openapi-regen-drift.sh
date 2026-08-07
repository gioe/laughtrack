#!/usr/bin/env bash
#
# Verify ios/Sources/LaughTrackAPIClient/GeneratedSources/Client.swift and
# Types.swift match a clean regen of openapi.json. Without this guard, edits to
# openapi.json can land without a matching client regen, stranding the iOS app
# behind the server contract (TASK-2549: a regen restored a typed sourceSurface
# enum that broke ShowDetailView.swift because a prior commit had drifted to
# plain Swift.String).
#
# Uses the same shared generator implementation as regen-openapi.sh, then diffs
# its staged output against the committed Client.swift and Types.swift.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ios/bin/openapi-common.sh
source "$SCRIPT_DIR/openapi-common.sh"

require_openapi_inputs

for file in "$COMMITTED_CLIENT" "$COMMITTED_TYPES"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: committed generated file does not exist: $file" >&2
        echo "Run ios/bin/regen-openapi.sh and commit the result." >&2
        exit 2
    fi
done

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
generate_openapi_sources "$STAGE/workspace" "$STAGE/output"

REGEN_CLIENT="$STAGE/output/Client.swift"
REGEN_TYPES="$STAGE/output/Types.swift"

drift=0
if ! diff -q "$REGEN_CLIENT" "$COMMITTED_CLIENT" >/dev/null; then
    echo "DRIFT: $COMMITTED_CLIENT differs from clean regen output" >&2
    diff -u "$COMMITTED_CLIENT" "$REGEN_CLIENT" | head -200 >&2 || true
    drift=1
fi
if ! diff -q "$REGEN_TYPES" "$COMMITTED_TYPES" >/dev/null; then
    echo "DRIFT: $COMMITTED_TYPES differs from clean regen output" >&2
    diff -u "$COMMITTED_TYPES" "$REGEN_TYPES" | head -200 >&2 || true
    drift=1
fi

if [[ $drift -ne 0 ]]; then
    cat >&2 <<EOM

The committed Sources/LaughTrackAPIClient/GeneratedSources/Client.swift or
Types.swift does not match a clean regen from openapi.json using
swift-openapi-generator $GENERATOR_VERSION.

Usually means one of:

  (a) openapi.json was edited but Client.swift / Types.swift were NOT
      regenerated alongside (the TASK-2549 incident pattern), or
  (b) the committed files were regenerated against a different generator
      version than the pinned one ($GENERATOR_VERSION), or
  (c) Client.swift / Types.swift were hand-edited (they should not be).

Fix: run ios/bin/regen-openapi.sh, then commit the updated Client.swift and
Types.swift in the same PR as the openapi.json edit.

EOM
    exit 1
fi

echo "OK: Client.swift and Types.swift match a clean regen with swift-openapi-generator $GENERATOR_VERSION."
