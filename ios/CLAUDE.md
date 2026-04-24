# CLAUDE.md

## Commands

```bash
swift build                            # Build all targets
swift build --target LaughTrackApp     # Build app target only
swift build --target LaughTrackBridge  # Build bridge target only
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
