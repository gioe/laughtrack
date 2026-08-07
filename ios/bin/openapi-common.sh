#!/usr/bin/env bash
#
# Shared helpers for iOS OpenAPI client generation and drift checking.
# Sourced by regen-openapi.sh and check-openapi-regen-drift.sh so both modes use
# the same paths, dependency pins, and swift-openapi-generator invocation.

set -euo pipefail

OPENAPI_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "$OPENAPI_BIN_DIR/.." && pwd)"

API_CLIENT_DIR="$IOS_DIR/Sources/LaughTrackAPIClient"
COMMITTED_GENERATED_DIR="$API_CLIENT_DIR/GeneratedSources"
COMMITTED_CLIENT="$COMMITTED_GENERATED_DIR/Client.swift"
COMMITTED_TYPES="$COMMITTED_GENERATED_DIR/Types.swift"
SPEC="$API_CLIENT_DIR/openapi.json"
CONFIG="$API_CLIENT_DIR/openapi-generator-config.yaml"

# Centralized dependency versions keep local writes and CI drift checks aligned.
GENERATOR_VERSION="${OPENAPI_GENERATOR_VERSION:-1.9.0}"
RUNTIME_VERSION="${OPENAPI_RUNTIME_VERSION:-1.9.0}"
HTTPTYPES_VERSION="${OPENAPI_HTTPTYPES_VERSION:-1.0.0}"

require_openapi_inputs() {
    for file in "$SPEC" "$CONFIG"; do
        if [[ ! -f "$file" ]]; then
            echo "ERROR: required file does not exist: $file" >&2
            exit 2
        fi
    done

    if ! command -v swift >/dev/null 2>&1; then
        echo "ERROR: swift is required to run swift-openapi-generator." >&2
        exit 2
    fi
}

# generate_openapi_sources <workspace> <output-dir>
# Builds a throwaway Swift package and copies both generated files into a staging
# directory. Callers own workspace cleanup and decide whether to diff or install.
generate_openapi_sources() {
    local workspace="$1"
    local output_dir="$2"
    local target_dir="$workspace/Sources/OpenAPIRegen"

    mkdir -p "$target_dir" "$output_dir"

    cat > "$workspace/Package.swift" <<EOF
// swift-tools-version: 5.9
import PackageDescription
let package = Package(
    name: "OpenAPIRegen",
    platforms: [.macOS(.v13)],
    dependencies: [
        .package(url: "https://github.com/apple/swift-openapi-generator", exact: "$GENERATOR_VERSION"),
        .package(url: "https://github.com/apple/swift-openapi-runtime", exact: "$RUNTIME_VERSION"),
        .package(url: "https://github.com/apple/swift-http-types", from: "$HTTPTYPES_VERSION"),
    ],
    targets: [.target(
        name: "OpenAPIRegen",
        dependencies: [
            .product(name: "OpenAPIRuntime", package: "swift-openapi-runtime"),
            .product(name: "HTTPTypes", package: "swift-http-types"),
        ],
        plugins: [.plugin(name: "OpenAPIGenerator", package: "swift-openapi-generator")],
    )],
)
EOF

    # SPM requires at least one source file in the target.
    touch "$target_dir/empty.swift"
    cp "$SPEC" "$target_dir/"
    cp "$CONFIG" "$target_dir/"

    echo "Running swift-openapi-generator $GENERATOR_VERSION on $SPEC..."
    (cd "$workspace" && swift build --target OpenAPIRegen)

    # SwiftPM's package-id casing varies by version, so locate outputs by content.
    local generated_client
    local generated_types
    generated_client="$(find "$workspace/.build/plugins/outputs" -type f -name Client.swift -path '*GeneratedSources*' | head -1 || true)"
    generated_types="$(find "$workspace/.build/plugins/outputs" -type f -name Types.swift -path '*GeneratedSources*' | head -1 || true)"

    if [[ -z "$generated_client" || -z "$generated_types" ]]; then
        echo "ERROR: regen did not produce Client.swift and Types.swift in .build/plugins/outputs" >&2
        find "$workspace/.build/plugins/outputs" -type f -name '*.swift' >&2 || true
        exit 2
    fi

    cp "$generated_client" "$output_dir/Client.swift"
    cp "$generated_types" "$output_dir/Types.swift"
}
