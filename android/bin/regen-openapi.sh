#!/usr/bin/env bash
#
# Regenerate the Android Kotlin OpenAPI client from the shared spec
# (ios/Sources/LaughTrackAPIClient/openapi.json) and write it into the network
# module at android/core/network/.../generated. Run this after any /api/v1 spec
# change, then commit the regenerated sources in the SAME PR as the spec edit
# (convention #220), alongside the regenerated iOS client.
#
# Requires JDK 17+ (downloads a pinned openapi-generator-cli jar on first run).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=android/bin/openapi-common.sh
source "$SCRIPT_DIR/openapi-common.sh"

require_files
ensure_generator

NETWORK_SRC_ROOT="$ANDROID_DIR/core/network/src/main/kotlin"
generate_generated_dir "$NETWORK_SRC_ROOT"

echo "OK: regenerated $COMMITTED_GENERATED_DIR with openapi-generator $GENERATOR_VERSION."
echo "Review the diff and commit it together with the openapi.json change."
