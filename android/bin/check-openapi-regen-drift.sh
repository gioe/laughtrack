#!/usr/bin/env bash
#
# Verify android/core/network/.../generated matches a clean regen of the shared
# openapi.json. Without this guard, a /api/v1 spec edit can land without a
# matching Android client regen, stranding the app behind the server contract
# (the Android mirror of ios/bin/check-openapi-regen-drift.sh).
#
# Runs the pinned openapi-generator into a temp dir and diffs the committed
# generated sources against it. Requires JDK 17+ only (no Android SDK / Gradle).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=android/bin/openapi-common.sh
source "$SCRIPT_DIR/openapi-common.sh"

require_files
ensure_generator

if [[ ! -d "$COMMITTED_GENERATED_DIR" ]]; then
    echo "ERROR: committed generated client not found at $COMMITTED_GENERATED_DIR" >&2
    echo "Run android/bin/regen-openapi.sh and commit the result." >&2
    exit 2
fi

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

generate_generated_dir "$STAGE"
REGEN_DIR="$STAGE/$GENERATED_PKG_PATH"

if diff -rq "$COMMITTED_GENERATED_DIR" "$REGEN_DIR" >/dev/null; then
    echo "OK: generated Kotlin client matches a clean regen with openapi-generator $GENERATOR_VERSION."
    exit 0
fi

echo "DRIFT: $COMMITTED_GENERATED_DIR differs from a clean regen output." >&2
diff -ru "$COMMITTED_GENERATED_DIR" "$REGEN_DIR" | head -200 >&2 || true
cat >&2 <<EOM

The committed Android OpenAPI client does not match a clean regen from
openapi.json using openapi-generator $GENERATOR_VERSION.

Usually means one of:

  (a) openapi.json was edited but the Android client was NOT regenerated
      alongside (run android/bin/regen-openapi.sh), or
  (b) the committed files were generated with a different generator version
      than the pinned one ($GENERATOR_VERSION), or
  (c) the generated files were hand-edited (they must not be).

Fix: run android/bin/regen-openapi.sh and commit the result in the same PR as
the openapi.json edit (and the regenerated iOS client — convention #220).

EOM
exit 1
