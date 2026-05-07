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

### iOS Simulator Cold Start Dominates `test_sim` Wall Time

A "test_sim hung" report on a HostedView suite is almost always cold-start
overhead, not a hanging test. Measured for `LaughTrackTests/ContentViewNavigationTests`
on iPhone 17 / iOS 26.1 (15 tests, all settle()-driven HostedView tests):

- Sim cold boot from shutdown:           ~120s
- `xcodebuild build-for-testing` cold:    60-180s (DerivedData empty)
- `xcodebuild build-for-testing` warm:    ~6s    (DerivedData primed)
- App install + test bundle load:         ~30s   (per run, even when warm)
- Test execution (suite-level slice):     ~20s

Cold path easily exceeds 4 minutes — over the XcodeBuildMCP `test_sim` 120s
default tool timeout. Warm path is ~60s end-to-end.

The reliable pattern for iterative work on a HostedView suite:

1. Boot the sim once (XcodeBuildMCP `boot_sim` or `xcrun simctl boot <UDID>`)
   and leave it running. Sim cold boot is the single largest cost.
2. Prime DerivedData once with `xcodebuild build-for-testing` for the scheme.
3. Iterate via raw `xcodebuild test-without-building -only-testing:LaughTrackTests/<SuiteName>`
   with `-resultBundlePath` for failure diagnostics. Skip `test_sim` for slices
   that need more than 90s — the MCP tool's 120s ceiling will cut you off.

When `test_sim` is the right tool for a quick run on a primed sim and prebuilt
DerivedData, it stays well under the timeout.

### Focused Swift Testing Filters Can Match Zero Tests

`swift test --filter <pattern>` can exit 0 even when the filter matches zero
test cases. Treat the process exit code as insufficient by itself: inspect the
reported test count and confirm at least one expected test ran. If the output
reports no matching tests, rerun with a known-matching suite, a broader filter,
or the full `swift test` suite before using the result as verification evidence.

This has caught filters aimed at API client configuration tests and
`HomeShowsTonightModelTests`; the command was green, but it had not exercised
the intended coverage.

### `xcodebuild -only-testing:` Method-Level Selectors Can Run Zero `@Test` Functions

The same zero-tests-but-green failure mode applies to the simulator runner
(`xcodebuild test` directly, or `test_sim` via XcodeBuildMCP, both of which
forward `-only-testing:` selectors). For Swift Testing's `@Test` functions, a
method-level selector of the form `LaughTrackTests/SuiteName/methodName` can
match zero tests while the xcodebuild process still exits 0 and the MCP tool
reports success (TASK-1881 — `HomeFavoriteShowsRailTests` and
`AppShellViewTests` reported green from method-level selectors that executed
nothing).

Root cause is not pinned down — observed symptom is that the test plan
resolver accepts an unmatched method-level selector silently and reports a
clean run. Treat it as a known unreliable selector shape until proven
otherwise.

The mitigation: **never trust a method-level Swift Testing selector by exit
code alone.**

1. Use **class- / suite-level selectors** (`LaughTrackTests/SuiteName`,
   without a method segment). These are matched by the suite type name and
   reliably execute every `@Test` in the suite.
2. Inspect the run output for the Swift Testing run-summary line — it reads
   `Test run with N tests passed after …` (or `0 tests` when nothing
   matched). A `Suite … passed` block with no nested `Test … started`
   lines is the smoking gun. If you cannot find evidence the intended test
   ran, rerun at suite level or against the full target.
3. The unit-test target (`LaughTrackTests`) is pure Swift Testing, so this
   gotcha applies there. The UI-test target (`LaughTrackUITests`) is XCTest,
   where method-level selectors *do* work — the failure mode is specific to
   `@Test` macro selectors.

### `.accessibilityIdentifier` On A Container Clobbers Child Button Identifiers

Under iOS 26, applying `.accessibilityIdentifier(...)` to a container view
that wraps cards using `.accessibilityElement(children: .combine)` propagates
the container's identifier down to every combined-child accessibility node —
the inner Buttons' own `.accessibilityIdentifier(...)` modifiers are masked.

Concrete example from `HomeShowsTonightRail` (TASK-1886 diagnosis):

```swift
VStack(...) {
    ForEach(shows) { show in
        Button { ... } label: { HomeShowsTonightHeroCard(show: show) }
            .accessibilityIdentifier(LaughTrackViewTestID.homeShowsTonightHeroButton)
        // HomeShowsTonightHeroCard ends with .accessibilityElement(children: .combine)
    }
}
.accessibilityIdentifier(LaughTrackViewTestID.homeShowsTonightRail)
```

`dumpAccessibilityTree` shows the hero card surfaces as
`AccessibilityNode id='laughtrack.home.shows-tonight-rail' label='<hero card combined label>'`
— the hero button's identifier never appears, so
`requireView(withIdentifier: homeShowsTonightHeroButton)` and
`tapControl(withIdentifier: homeShowsTonightHeroButton)` cannot find it.

If a HostedView test must drive a button inside a rail/list whose container
already carries an identifier, either drop the container's identifier and
assert the rail's existence by some other means (e.g. `requireText` of the
rail's eyebrow/title), or activate the button by accessibility label rather
than identifier.

### Persistent Caches Bleed Real Production Data Into HostedView Tests

Models reading from a singleton disk-backed cache (`PersistentMainPageCache.shared`,
`DataCache<…>` instances scoped at `.appLevel`) will return whatever was
written to disk by previous launches — including debug-build runs of the
real app against production servers. A HostedView test that constructs a
mock transport will silently never invoke it: the model returns cached
production data first, so the test assertions are evaluated against
whatever the prod API happened to return last time the simulator's app
sandbox was written to.

When you build a HostedView test that depends on the model load path,
either:
- Reset / wipe the persistent store before constructing the view, or
- Plumb a test-specific cache into the model and assert on its contents
  rather than relying on the default `.shared` instance.

A passing test today is no guarantee under this contamination — it might
fail on a colleague's machine with different cache contents and look
flaky.

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

4. **`accessibilityActivate()` on a SwiftUI Button with a complex/combined
   label silently no-ops.** When a Button's `label:` content uses
   `.accessibilityElement(children: .combine)` or otherwise produces its own
   combined accessibility element (e.g. card views that combine artwork +
   metadata into a single VoiceOver-friendly node), HostedView's
   `tapControl(withIdentifier:)` finds the element but the underlying
   `accessibilityActivate?()` call returns without firing the Button's
   trailing closure — even after adding `.accessibilityAction { ... }` on
   the Button or replacing the Button with `.onTapGesture` +
   `.accessibilityAddTraits(.isButton)`. Same bucket as the toolbar gotcha
   above. Don't burn cycles trying to coerce the activate path; switch the
   test to the resolver round-trip pattern: assert (a) the button mounts
   with the expected accessibility identifier, (b) the navigation helper
   resolves to the expected route (e.g.
   `EntityNavigationTarget.show(_:).route == .showDetail(_:)`), and (c)
   drive the route via `coordinator.path.append(_:)` to verify
   `NavigationPath.codable` round-trips. Canonical example: the toolbar
   workaround in `nearMeProfileButtonPushesProfileRoute`
   (`ios/Tests/LaughTrackTests/ContentViewNavigationTests.swift`).

### iOS 26 Accessibility-Tree Wiring Regression (TASK-1921)

As of 2026-05-07, on iPhone 17 / iOS 26.1 and iOS 26.2 simulators, the
HostedView first-window-makeKeyAndVisible mitigation no longer wires
SwiftUI's accessibility tree at all. `dumpAccessibilityTree()` returns just
`<view> _UIHostingView<AnyView>` — zero `accessibilityElements`, zero
identifiers (not even on the root ScrollView). 18 tests across 16 suites
fail: HomeFavoriteShowsRailTests, ContentViewNavigationTests,
AppShellViewTests, ProfileViewTests, SearchRootViewTests,
SettingsViewStateTests, ShowDetailViewTests.

**Bisect** (Xcode 26.3, build 17C519, same source revision, minimal
`HostedViewDumpTreeTests` content tree of `Text` + `Button` in `VStack`):

| Sim runtime | Result |
|---|---|
| iOS 18.3.1 | ✅ 2/2 PASS |
| iOS 26.1 | ❌ 0/2 FAIL |
| iOS 26.2 | ❌ 0/2 FAIL |

Same Xcode toolchain, different sim runtime → confirmed iOS 26 SDK
runtime regression in `_UIHostingView` accessibility wiring under
test-process hosting. Apple has not fixed it in 26.2. Three prior
code-level workaround attempts (UIAccessibilityContainer traversal,
delaying `makeKeyAndVisible` until after `rootViewController` assignment,
reusing the existing app key window) all failed. The mitigation
documented in items 1–4 above remains correct on iOS 18.3.1; it simply
has no effect on iOS 26.x.

**Workaround pattern: model / recorder-layer tests.** When you need to
verify product behavior in a HostedView-style test suite under iOS 26.x,
do NOT assert via `host.requireView` / `host.requireText` — those will
fail unconditionally on the broken wiring. Instead test the underlying
view model or transport recorder directly. Two reference points:

- `AppShellViewTests.authenticatedShellTriggersFavoritesFetch` — uses a
  custom `ClientTransport` (`MockShellFavoritesTransport`) with an
  `@unchecked Sendable` recorder counter. Still hosts the view (so the
  view's `.task(id:)` fires through `host.settle()`) but asserts on
  `recorder.getFavoritesCalls`, not on UIView traversal.
- `HomeFavoriteShowsRailTests.favoriteShowsModelLoadsUpcomingShowsForSavedFavorites`
  (TASK-1921 pilot) — bypasses HostedView entirely; constructs
  `HomeFavoriteShowsModel` directly and asserts `model.phase` is
  `.success([show])` after `await model.refresh(...)`. Use this shape
  when the state under test is a discrete `ObservableObject` that can
  be exercised in isolation.

Prefer model-direct construction (second pattern) when a clean
`ObservableObject` boundary exists; fall back to the transport-recorder
pattern (first) when state is wired through a view hierarchy that's hard
to disentangle.

`findView == nil` assertions still "pass" under broken wiring, but they
pass vacuously — anything is "missing" when nothing is wired. When
migrating a suite, re-shape those negative assertions into model-layer
checks (e.g., assert the model's phase remains `.idle` or its filtered
output is empty under the corresponding inputs).

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
