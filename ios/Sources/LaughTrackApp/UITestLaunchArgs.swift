import Foundation

/// Single source of truth for the UI-test launch-argument and launch-environment
/// keys shared between the producer (LaughTrackApp.swift, DebugSimulatedFavoriteHook)
/// and the consumer (LaughTrackUITests). The XCUITest bundle runs in a separate
/// process and cannot import the LaughTrackApp module, so this file is given
/// **dual target membership** in the Xcode project — added to both the LaughTrack
/// app target and the LaughTrackUITests target. Each binary gets its own
/// internal-scoped copy of the same symbols, so editing a literal here updates
/// producer and consumer in lockstep; a typo at either end becomes a compile
/// error rather than a silent test-time wait-for-element timeout.
///
/// Note: the SPM `LaughTrackApp` target auto-includes this file via its Sources
/// directory; the SPM side has no UITest consumer (LaughTrackUITests is an
/// Xcode-only `com.apple.product-type.bundle.ui-testing` target, intentionally
/// absent from Package.swift). The "or equivalent" wording in TASK-2614's
/// criterion 8546 covers this dual-membership approach in lieu of a brand-new
/// SPM library + paired Xcode framework target for three string constants.
enum UITestLaunchArgs {
    /// Launch argument: wipes UserDefaults keys that drive the auth gate,
    /// first-entry guest choice, session metadata, and soft push-prompt
    /// cadence so the test starts deterministically. Every test method MUST
    /// pass this on its first `XCUIApplication.launch()` — XCTest runs the
    /// suite's methods in one process and UserDefaults.standard survives
    /// terminate+launch.
    static let resetState = "UITEST_RESET_STATE"

    /// Launch argument: seeds the first-entry guest-browsing choice past the
    /// auth gate so tests that have no business with the auth wall (e.g. the
    /// soft push-prompt cadence suite) can mount the shell directly. Re-seeded
    /// after `resetState` wipes it, so argument order is not significant.
    static let guestBrowsing = "UITEST_GUEST_BROWSING"

    /// Launch-environment key (NOT a launch argument): instructs the
    /// `DebugSimulatedFavoriteHook` (DEBUG-only seam) to synthesize N
    /// post-onboarding favorite signals at app start, bypassing the
    /// signed-in-user + live `POST /favorites` round-trip the production
    /// favorite-tap path requires. Value is the integer count as a string.
    static let simulatePostOnboardingFavoriteCount = "UITEST_SIMULATE_POST_ONBOARDING_FAVORITE_COUNT"

    /// Launch-environment key (NOT a launch argument): DEBUG-only developer
    /// seam. When set to `"1"`, `ContentView.shouldPresentComedianOnboarding`
    /// short-circuits to `true` so the comedian-onboarding screen renders on
    /// every relaunch even after the signed-in user's server-side
    /// `comedianOnboardingCompleted` is `true`. Lets a dev iterate on the
    /// onboarding UX without repeatedly `PATCH`-ing `/v1/me` against the
    /// dev account. Centralised here alongside the other launch keys for
    /// discoverability; the gate is `#if DEBUG`-guarded so the env var has
    /// no effect in TestFlight / App Store builds.
    static let forceComedianOnboarding = "FORCE_COMEDIAN_ONBOARDING"

    /// Launch-environment key (NOT a launch argument): DEBUG-only developer
    /// seam. When set to `"1"`, `ContentView.rootSurface` renders the
    /// comedian-onboarding screen directly, before auth and first-entry gates.
    /// This is intentionally stronger than `forceComedianOnboarding`: it is
    /// for visual/screen iteration when no auth session exists on the
    /// simulator. Release builds never read it.
    static let forceComedianOnboardingScreen = "FORCE_COMEDIAN_ONBOARDING_SCREEN"
}
