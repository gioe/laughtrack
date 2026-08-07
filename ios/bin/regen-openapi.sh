#!/usr/bin/env bash
#
# Regenerate the committed iOS Swift OpenAPI client from openapi.json. Run this
# after changing the shared API specification, then commit Client.swift and
# Types.swift in the same change as the specification.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ios/bin/openapi-common.sh
source "$SCRIPT_DIR/openapi-common.sh"

require_openapi_inputs

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

generate_openapi_sources "$STAGE/workspace" "$STAGE/output"

# Generation and staging must succeed for both files before either committed
# output is replaced.
mkdir -p "$COMMITTED_GENERATED_DIR"
cp "$STAGE/output/Client.swift" "$COMMITTED_CLIENT"
cp "$STAGE/output/Types.swift" "$COMMITTED_TYPES"

echo "OK: regenerated $COMMITTED_CLIENT and $COMMITTED_TYPES with swift-openapi-generator $GENERATOR_VERSION."
echo "Review the diff and commit both files together with the openapi.json change."
