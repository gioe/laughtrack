#!/usr/bin/env bash
#
# Verify ios/Sources/LaughTrackAPIClient/GeneratedSources/Client.swift and
# Types.swift match a clean regen of openapi.json. Without this guard, edits to
# openapi.json can land without a matching client regen, stranding the iOS app
# behind the server contract (TASK-2549: a regen restored a typed sourceSurface
# enum that broke ShowDetailView.swift because a prior commit had drifted to
# plain Swift.String).
#
# Mirrors the regen flow documented in ios/CLAUDE.md ("To regenerate, stand up
# a throwaway SPM package..."): stand up a temp SPM package that wires the
# swift-openapi-generator plugin, copy openapi.json + openapi-generator-config.yaml
# into it, build the OpenAPIRegen target, then diff the plugin's GeneratedSources
# output against the committed Client.swift / Types.swift.
#
# Generator version pin: deterministic CI requires an exact pin (per ios/CLAUDE.md
# "Generator-version drift", different generator versions emit different argument-
# list formatting and produce ~600-line diffs from the same spec). Override via
# OPENAPI_GENERATOR_VERSION when re-baselining against a newer release.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

API_CLIENT_DIR="$IOS_DIR/Sources/LaughTrackAPIClient"
COMMITTED_CLIENT="$API_CLIENT_DIR/GeneratedSources/Client.swift"
COMMITTED_TYPES="$API_CLIENT_DIR/GeneratedSources/Types.swift"
SPEC="$API_CLIENT_DIR/openapi.json"
CONFIG="$API_CLIENT_DIR/openapi-generator-config.yaml"

GENERATOR_VERSION="${OPENAPI_GENERATOR_VERSION:-1.9.0}"
RUNTIME_VERSION="${OPENAPI_RUNTIME_VERSION:-1.9.0}"
HTTPTYPES_VERSION="${OPENAPI_HTTPTYPES_VERSION:-1.0.0}"

for f in "$COMMITTED_CLIENT" "$COMMITTED_TYPES" "$SPEC" "$CONFIG"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: required file does not exist: $f" >&2
        exit 2
    fi
done

REGEN_DIR="$(mktemp -d)"
trap 'rm -rf "$REGEN_DIR"' EXIT

mkdir -p "$REGEN_DIR/Sources/OpenAPIRegen"

cat > "$REGEN_DIR/Package.swift" <<EOF
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
touch "$REGEN_DIR/Sources/OpenAPIRegen/empty.swift"
cp "$SPEC"   "$REGEN_DIR/Sources/OpenAPIRegen/"
cp "$CONFIG" "$REGEN_DIR/Sources/OpenAPIRegen/"

echo "Running swift-openapi-generator $GENERATOR_VERSION on $SPEC..."
(cd "$REGEN_DIR" && swift build --target OpenAPIRegen)

# The plugin output path is .build/plugins/outputs/<package-id>/<target>/destination/OpenAPIGenerator/GeneratedSources/
# but the exact <package-id> casing depends on the SPM version. Locate the output by content.
REGEN_CLIENT="$(find "$REGEN_DIR/.build/plugins/outputs" -type f -name Client.swift -path '*GeneratedSources*' | head -1 || true)"
REGEN_TYPES="$(find "$REGEN_DIR/.build/plugins/outputs" -type f -name Types.swift  -path '*GeneratedSources*' | head -1 || true)"

if [[ -z "$REGEN_CLIENT" || -z "$REGEN_TYPES" ]]; then
    echo "ERROR: regen did not produce Client.swift and Types.swift in .build/plugins/outputs" >&2
    find "$REGEN_DIR/.build/plugins/outputs" -type f -name '*.swift' >&2 || true
    exit 2
fi

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

Fix: follow the regen flow in ios/CLAUDE.md ("To regenerate, stand up a
throwaway SPM package...") using swift-openapi-generator $GENERATOR_VERSION,
then commit the updated Client.swift / Types.swift in the same PR as the
openapi.json edit.

EOM
    exit 1
fi

echo "OK: Client.swift and Types.swift match a clean regen with swift-openapi-generator $GENERATOR_VERSION."
