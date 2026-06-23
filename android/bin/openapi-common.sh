#!/usr/bin/env bash
#
# Shared helpers for the Android OpenAPI client generation + drift check.
# Sourced by regen-openapi.sh and check-openapi-regen-drift.sh.
#
# The Kotlin client under android/core/network/.../generated is generated from
# the SHARED spec at ios/Sources/LaughTrackAPIClient/openapi.json — the same
# contract the iOS swift-openapi client is generated from. Any /api/v1 change
# must regenerate BOTH clients in lockstep (convention #220).
#
# Generator version pin: deterministic CI requires an exact pin — different
# openapi-generator versions emit different formatting and produce large diffs
# from the same spec. Override via OPENAPI_GENERATOR_VERSION when re-baselining.

set -euo pipefail

ANDROID_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANDROID_DIR="$(cd "$ANDROID_BIN_DIR/.." && pwd)"
REPO_ROOT="$(cd "$ANDROID_DIR/.." && pwd)"

SPEC="$REPO_ROOT/ios/Sources/LaughTrackAPIClient/openapi.json"
CONFIG="$ANDROID_DIR/openapi/openapi-generator-config.yaml"

# Package path of the generated sources within the network module.
GENERATED_PKG_PATH="app/laughtrack/android/core/network/generated"
COMMITTED_GENERATED_DIR="$ANDROID_DIR/core/network/src/main/kotlin/$GENERATED_PKG_PATH"

GENERATOR_VERSION="${OPENAPI_GENERATOR_VERSION:-7.11.0}"
GEN_CACHE="${OPENAPI_GEN_CACHE:-$HOME/.cache/openapi-generator}"
GEN_JAR="$GEN_CACHE/openapi-generator-cli-$GENERATOR_VERSION.jar"
MAVEN_BASE="https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli"

require_files() {
    for f in "$SPEC" "$CONFIG"; do
        if [[ ! -f "$f" ]]; then
            echo "ERROR: required file does not exist: $f" >&2
            exit 2
        fi
    done
    if ! command -v java >/dev/null 2>&1; then
        echo "ERROR: java (JDK 17+) is required to run openapi-generator." >&2
        exit 2
    fi
}

ensure_generator() {
    mkdir -p "$GEN_CACHE"
    if [[ ! -f "$GEN_JAR" ]]; then
        echo "Downloading openapi-generator-cli $GENERATOR_VERSION ..." >&2
        curl -fsSL "$MAVEN_BASE/$GENERATOR_VERSION/openapi-generator-cli-$GENERATOR_VERSION.jar" \
            -o "$GEN_JAR" || {
            echo "ERROR: failed to download openapi-generator-cli $GENERATOR_VERSION" >&2
            exit 2
        }
    fi
}

# generate_generated_dir <dest_parent>
# Runs the generator into a temp dir and copies ONLY the generated Kotlin package
# (api/model/infrastructure/auth) to <dest_parent>/<GENERATED_PKG_PATH>. The
# generator's project scaffolding (build.gradle, docs, wrapper, etc.) is dropped.
generate_generated_dir() {
    local dest_parent="$1"
    local tmp
    tmp="$(mktemp -d)"
    # shellcheck disable=SC2064
    trap "rm -rf '$tmp'" RETURN

    echo "Running openapi-generator $GENERATOR_VERSION on $SPEC ..." >&2
    java -jar "$GEN_JAR" generate -i "$SPEC" -c "$CONFIG" -o "$tmp" >/dev/null

    local src="$tmp/src/main/kotlin/$GENERATED_PKG_PATH"
    if [[ ! -d "$src" ]]; then
        echo "ERROR: generator did not produce $src" >&2
        exit 2
    fi
    rm -rf "${dest_parent:?}/$GENERATED_PKG_PATH"
    mkdir -p "$(dirname "$dest_parent/$GENERATED_PKG_PATH")"
    cp -R "$src" "$dest_parent/$GENERATED_PKG_PATH"
}
