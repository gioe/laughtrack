# CLAUDE.md

## Commands

```bash
swift build                            # Build all targets
swift build --target LaughTrackApp     # Build app target only
swift build --target LaughTrackBridge  # Build bridge target only
make -C ios check-pbxproj              # Verify every Sources/*.swift is wired into LaughTrack.xcodeproj (run before push)
make -C ios check-ios-libs-pin         # Verify ios-libs revision pins agree across project.yml + both Package.resolved files (run before push)
```

## Testing

iOS tests split across two runners:

- **`swift test`** — runs pure Swift unit tests on macOS. Fast (~0.1s), but silently
  skips any file guarded by `#if canImport(UIKit)` (e.g. `AppShellViewTests`,
  `ContentViewNavigationTests`, and anything using `HostedView` from
  `HostedViewTestSupport.swift`). A green `swift test` run does NOT prove those
  test files were exercised.
- **`test_sim`** via XcodeBuildMCP — runs the full Xcode test plan against an iOS
  simulator. Required to cover HostedView integration tests, UI tests, and
  anything depending on UIKit at runtime. Slower (~45s) but authoritative.

For a refactor that touches code reachable from a HostedView test, always run
`test_sim` before declaring the change verified. When UI-test failures appear,
confirm pre-existing vs regression via `git stash push -u` + re-run against
HEAD + `git stash pop` — `tusk test-precheck` doesn't cover MCP-invoked tests.

### Focused Swift Testing Filters Can Match Zero Tests

`swift test --filter <pattern>` can exit 0 even when the filter matches zero
test cases. Treat the process exit code as insufficient by itself: inspect the
reported test count and confirm at least one expected test ran. If the output
reports no matching tests, rerun with a known-matching suite, a broader filter,
or the full `swift test` suite before using the result as verification evidence.

This has caught filters aimed at API client configuration tests and
`HomeShowsTonightModelTests`; the command was green, but it had not exercised
the intended coverage.

### Debugging SwiftUI Rendering — Start With `dumpAccessibilityTree`

When a `requireView` / `requireText` / `tapControl` assertion fails in a way
the source doesn't immediately explain, the **first step** is to dump the
hosted view's accessibility tree:

```swift
let host = HostedView(MyView())
print(host.dumpAccessibilityTree())
// or persist for inspection from outside the test process:
host.dumpAccessibilityTree(writingTo: "/tmp/dump.txt")
```

The dump walks both `subviews` and `accessibilityElements` at every level,
showing the underlying type, `accessibilityIdentifier`, and
`accessibilityLabel` for each node. Under iOS 26 SwiftUI surfaces `Text()`
and `Button` labels as synthetic accessibility-element nodes that never
appear as UIView subviews — any debugging approach that walks only
`subviews` (e.g. `po hostingController.view.recursiveDescription`) will
miss them and produce a misleading picture. Reach for
`dumpAccessibilityTree` before writing throw-away inline probes.

### HostedView Quirks Under iOS 26 / Xcode 26

SwiftUI's accessibility-tree wiring under iOS 26 has three behaviors that catch
HostedView-based UI tests by surprise (TASK-1761). HostedView already mitigates
them, but tests built on top of it inherit the constraints.

1. **Only the *first* `UIWindow.makeKeyAndVisible()` per process wires the
   SwiftUI accessibility tree.** Subsequent fresh windows render visually but
   their hosting controller never exposes `accessibilityIdentifier` or
   `accessibilityElements` to UIView traversal. HostedView reuses a static
   `UIWindow` across instances and swaps in a fresh `UIHostingController` per
   test. Tests that need a clean window (toolbar-driven assertions, etc.) can
   pass `freshWindow: true` to opt out at the cost of losing the accessibility
   wiring on subsequent suite tests.

2. **`Text()` and `Button` labels surface as `AccessibilityNode` in the parent
   UIView's `accessibilityElements`, not as `UILabel` / `UIButton` subviews.**
   `findText` / `requireLabel` traverse `accessibilityElements` at every level
   to find them. Buttons that wrap multiple `Text()` children produce a single
   comma-joined accessibility label (e.g. `"Taylor Tomlinson, 5 tracked show
   appearances"`), so per-segment matching is part of the contract.

3. **`.toolbar` items don't activate reliably via `accessibilityActivate()`
   once the test process has hosted other controllers** — `tapControl` returns
   `false` and the SwiftUI Button action never fires. The workaround pattern
   is to extract the toolbar action's decision logic into a pure helper
   (e.g. `AppRoute.homeToolbarTarget(isSignedIn:)`) and unit-test that
   directly. The integration test still asserts the button exists with its
   accessibility identifier, but does not depend on tap activation.

### Async Lifecycle in HostedView Tests

SwiftUI's `.task` / `.task(id:)` modifiers don't fire reliably while
`HostedView` is pumping the run loop synchronously — the Swift Concurrency
runtime needs explicit yields to schedule the work. Use `await host.settle()`
after construction in any test whose view loads data via `.task`. If the test
fixture can be pre-populated (e.g. an `@EnvironmentObject` store), prefer
pre-loading: it both avoids the lifecycle dependency and makes the rendering
assertion stand alone.

### NavigationPath Route Inspection

`NavigationPath` erases element types and has no `.last`. To assert *which*
route was pushed (not just the depth), routes must be Codable and the
pushed-by-coordinator path must round-trip through `NavigationPath.codable`.

Two gotchas:
- `NavigationCoordinator.push(_:)` is constrained `Route: Hashable` (not
  `Hashable & Codable`), so it routes to `NavigationPath.append`'s non-Codable
  overload and `path.codable` returns nil. Tests verifying a destination must
  call `coordinator.path.append(_:)` directly with a statically-Codable value.
- The `decodedRoutes(in:as:)` helper in `HostedViewTestSupport.swift` reverses
  the codable representation back into `[Route]` in push order.

## Launch Screen Iteration

iOS caches the launch screen on the simulator (and on devices). After editing
`UILaunchScreen` plist values, `LaunchBackground.colorset`, or
`LaunchLogo.imageset`, a fresh build + relaunch is **not** sufficient — the
simulator keeps serving the cached splash. To verify launch-screen changes,
wipe the simulator first:

```bash
xcrun simctl shutdown <UDID>
xcrun simctl erase <UDID>
xcrun simctl boot <UDID>
# then install + launch as usual
```

TASK-1823 burned ~10 minutes diagnosing a "blank logo" splash that was
actually a stale cache — the new asset was correctly in `Assets.car` (verify
via `xcrun assetutil --info <app>/Assets.car`), but the simulator kept
serving the prior PDF-era render until `simctl erase`.

Also: `UILaunchScreen` image lookup does **not** fall back from a dark-mode
device to the light asset when the imageset declares only light variants. If
`LaunchLogo.imageset/Contents.json` lists `.png` files but no
`appearances: [{appearance: luminosity, value: dark}]` entries, dark-mode
cold launch renders the background color with no logo. The
`bin/generate-launch-logo.swift` script writes PNGs but does not manage
Contents.json — keep them aligned by hand.

## OpenAPI Client Regeneration

The generated client lives at `Sources/LaughTrackAPIClient/GeneratedSources/Client.swift`
and `Types.swift`. These files are committed and must be regenerated in lockstep with
any edit to `Sources/LaughTrackAPIClient/openapi.json` — otherwise server contract
changes are invisible to the iOS app (seen in TASK-1724 → TASK-1725, where the
access/refresh token contract landed in the spec but the client kept returning the old
single-`token` shape). Any task that edits `openapi.json` must ship both the spec
edit and the regenerated Client/Types edit in the same PR — splitting them strands the
iOS client behind the server contract.

`swift-openapi-generator` is not a LaughTrack dependency — the build tool plugin was
removed upstream to avoid Xcode validation prompts. To regenerate, stand up a throwaway
SPM package that wires the plugin in, then copy the output back:

```bash
mkdir -p /tmp/openapi-regen/Sources/OpenAPIRegen && cd /tmp/openapi-regen
cat > Package.swift <<'EOF'
// swift-tools-version: 5.9
import PackageDescription
let package = Package(
    name: "OpenAPIRegen",
    platforms: [.macOS(.v13)],
    dependencies: [
        .package(url: "https://github.com/apple/swift-openapi-generator", from: "1.0.0"),
        .package(url: "https://github.com/apple/swift-openapi-runtime", from: "1.9.0"),
        .package(url: "https://github.com/apple/swift-http-types", from: "1.0.0"),
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
touch Sources/OpenAPIRegen/empty.swift   # SPM requires at least one source file
cp <repo>/ios/Sources/LaughTrackAPIClient/openapi.json Sources/OpenAPIRegen/
cp <repo>/ios/Sources/LaughTrackAPIClient/openapi-generator-config.yaml Sources/OpenAPIRegen/
swift build --target OpenAPIRegen
cp .build/plugins/outputs/openapi-regen/OpenAPIRegen/destination/OpenAPIGenerator/GeneratedSources/{Client,Types}.swift \
   <repo>/ios/Sources/LaughTrackAPIClient/GeneratedSources/
```

Then `cd <repo>/ios && swift build --target LaughTrackAPIClient` to verify the
regenerated files compile.

## Architecture

This project uses [ios-libs](https://github.com/gioe/ios-libs) for shared infrastructure.

### Targets

- **LaughTrackApp** — Main app target. Imports `LaughTrackBridge` (not SharedKit directly).
- **LaughTrackBridge** — Bridge target that wraps ios-libs SharedKit. Re-exports selected types via `public typealias`. Add new SharedKit type re-exports here when needed.
- **LaughTrackAPIClient** — API client target wrapping ios-libs APIClient. Add product-specific type extensions here.

### ios-libs Features Integrated

- **Navigation:** CoordinatedNavigationStack with type-safe AppRoute enum
- **API:** OpenAPI Generated via APIClientFactory
- **Auth:** Token-based Bearer (AuthenticationMiddleware + TokenRefreshMiddleware)
- **Services:** NetworkMonitor, KeychainStorage, ToastManager, OfflineOperationQueue, DataCache + ImageCache, AppStateStorage

---

## ios-libs Component Catalog

> **Before creating new UI components, services, or utilities, check this catalog.** ios-libs SharedKit and APIClient provide tested, reusable implementations. Using them avoids duplication and ensures consistency across consumer apps.

### UI Components (`SharedKit/Components/`)

- BiometricLockView
- BottomSheet
- CachedAsyncImage
- ConfirmationModal
- CustomTextField
- EmptyStateView
- ErrorBanner
- ErrorView
- IconButton
- IconContentCard
- IconContentRow
- LoadingOverlay
- LoadingView
- ModalContainer
- NetworkStatusBanner
- PageIndicator
- PaginatedList
- PrimaryButton
- ScrollPositionModifier
- SearchBar
- ToastView

### Services (`SharedKit/Services/`)

- AnalyticsManager
- AppStateStorage
- BiometricAuthManager
- DataCache
- HapticManager
- ImageCache
- KeychainStorage
- NetworkMonitor
- OfflineOperationQueue
- ServiceContainer
- StoredPropertyWrapper
- ToastManager

### Design System (`SharedKit/Design/`)

- ColorPalette
- DesignSystem
- EnvironmentValues+Theme
- Theme
- Typography

### Architecture (`SharedKit/Architecture/`)

- BaseViewModel
- ViewModelProtocol

### Navigation (`SharedKit/Navigation/`)

- CoordinatedNavigationStack
- DeepLinkHandler
- EnvironmentValues+NavigationCoordinator
- NavigationCoordinator

### Utilities (`SharedKit/Utilities/`)

- AnyCodable
- DebugFlags
- TimeProvider
- Validators

### Protocols (`SharedKit/Protocols/`)

- AnalyticsProvider
- ErrorRecorder
- RetryableError

### APIClient Middleware (`APIClient/Middleware/`)

- AuthenticationMiddleware
- LoggingMiddleware
- RetryMiddleware
- TokenRefreshMiddleware

### APIClient Core (`APIClient/`)

- APIClient
- APIClientFactory
- APIError
- EnvironmentValues+APIClient

## Usage Rules

1. **Check ios-libs first.** Before creating a new UI component, service, utility, or middleware, search the catalog above. If ios-libs has it, use it via the bridge target.
2. **Never import SharedKit directly in LaughTrackApp.** Always go through `LaughTrackBridge` to prevent View extension symbol collisions.
3. **Add new re-exports to the bridge when needed.** If you need a SharedKit type not yet exposed:
   1. Open `Sources/LaughTrackBridge/LaughTrackBridge.swift`
   2. Add `public typealias MyType = SharedKit.MyType`
   3. Import from `LaughTrackBridge` in your app code
4. **Extend generated API types in LaughTrackAPIClient.** Product-specific convenience methods (e.g., `displayName` on a User schema) belong in `Sources/LaughTrackAPIClient/`, not in the app target.

## Bridge Target Pattern

### What It Does

The bridge target (`LaughTrackBridge`) sits between your app and ios-libs SharedKit. It re-exports selected SharedKit types via `public typealias` declarations, centralizing the dependency and making it easy to control which symbols the app target uses.

### When You Need It

You need a bridge target whenever:
- Your app defines **its own SwiftUI View extensions** (e.g., `.cardStyle()`, `.themed()`) that could collide with SharedKit's extensions of the same name
- You link **multiple SPM packages** that both extend SwiftUI View — the bridge isolates each package's extensions

### When You Don't Need It

If your app has **no custom View extensions** and only depends on ios-libs (no other extension-heavy packages), you could import SharedKit directly. However, keeping the bridge is recommended — it's zero-cost at runtime and protects against future collisions.

### How It Works

```
LaughTrackApp ──imports──▶ LaughTrackBridge ──import──▶ SharedKit
                           (public typealiases)
```

The bridge centralizes the SharedKit dependency. Add new `public typealias` declarations to the bridge file when you need additional SharedKit types in the app.

## Contributing Back to ios-libs

If you build a component, service, or utility that is **generic enough to be reused across apps**, consider extracting it into ios-libs:

1. Run `/extract-to-libs` from the ios-libs working directory — it will audit your project for extraction candidates
2. Extraction candidates should be app-agnostic (no product-specific logic, no hardcoded config)
3. Good candidates: UI components, design tokens, networking utilities, storage abstractions, validation logic
4. Poor candidates: app-specific screens, product business logic, configuration tied to one backend
