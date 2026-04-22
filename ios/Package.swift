// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "LaughTrack",
    platforms: [
        .iOS(.v16),
        .macOS(.v13)
    ],
    dependencies: [
        .package(url: "https://github.com/gioe/ios-libs.git", branch: "main"),
        .package(url: "https://github.com/apple/swift-openapi-runtime", from: "1.9.0"),
        .package(url: "https://github.com/apple/swift-openapi-urlsession", from: "1.3.0"),
        .package(url: "https://github.com/apple/swift-http-types", from: "1.0.0")
    ],
    targets: [
        .target(
            name: "LaughTrackCore",
            dependencies: [
                "LaughTrackBridge",
                "LaughTrackAPIClient",
                .product(name: "OpenAPIURLSession", package: "swift-openapi-urlsession"),
            ]
        ),
        .target(
            name: "LaughTrackApp",
            dependencies: [
                "LaughTrackCore",
                "LaughTrackBridge",
                "LaughTrackAPIClient",
            ],
            exclude: [
                "Info.plist"
            ]
        ),
        .target(
            name: "LaughTrackBridge",
            dependencies: [
                .product(name: "SharedKit", package: "ios-libs")
            ]
        ),
        .target(
            name: "LaughTrackAPIClient",
            dependencies: [
                .product(name: "APIClient", package: "ios-libs"),
                .product(name: "OpenAPIRuntime", package: "swift-openapi-runtime"),
                .product(name: "HTTPTypes", package: "swift-http-types")
            ],
            exclude: [
                "openapi.json",
                "openapi-generator-config.yaml"
            ]
        ),
        .testTarget(
            name: "LaughTrackTests",
            dependencies: [
                "LaughTrackApp",
                "LaughTrackCore",
                "LaughTrackBridge",
                "LaughTrackAPIClient",
                .product(name: "OpenAPIRuntime", package: "swift-openapi-runtime"),
                .product(name: "HTTPTypes", package: "swift-http-types"),
            ]
        ),
    ]
)
