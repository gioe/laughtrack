import XCTest

/// End-to-end coverage of the soft push-prompt cadence's defer → cold-launch →
/// no-reprompt flow against a real iOS simulator. The unit tests in
/// `SoftPushPromptCoordinatorTests` cover the algorithm and the coordinator's
/// post-deferral session / backoff gates, but they construct
/// `PushPermissionPromptCadence.Inputs` directly, so a regression in
/// `SoftPushPromptCoordinator.handleComedianFavoriteAdded`'s Inputs
/// construction (a dropped field, a stale snapshot, a wrong source) is
/// invisible to them. This suite drives the real coordinator under the real
/// `PushPermissionStateStore` (backed by `UserDefaults.standard` on the sim)
/// and asserts the visible UI behavior.
///
/// The favorite-tap path in production requires a signed-in user and a live
/// `POST /favorites` round-trip; neither is feasible in a 90s test_sim run,
/// so the favorite signals are synthesized at app start via
/// `DebugSimulatedFavoriteHook` (DEBUG-only seam wired into `ContentView`'s
/// `appShell`). The seam still goes through the coordinator, which is the
/// part of the wiring this test is here to defend.
@MainActor
final class PushPromptCadenceUITests: XCTestCase {
    // Test-isolation contract for this suite: XCTest runs the suite's
    // methods in the same process, and the cadence state under test is
    // persisted to `UserDefaults.standard` (via PushPermissionStateStore),
    // which survives `XCUIApplication.terminate()` + `launch()`. Every test
    // method added here MUST pass `UITEST_RESET_STATE` on its first
    // `app.launch()` — otherwise it silently inherits the previous method's
    // deferralCount / sessionCountSinceLastDeferral and becomes
    // alphabetic-ordering-dependent. There is no shared setUp() because
    // each test owns its own multi-launch sequence and a baseline launch
    // would just be discarded.

    // Accessibility identifier from `LaughTrackViewTestID`. Duplicated as a
    // literal because the UI-testing target doesn't import the app module —
    // XCUITest queries the cross-process accessibility tree by string.
    private static let softPushDeferButton = "laughtrack.soft-push-prompt.defer-button"

    // Env-var key from `DebugSimulatedFavoriteHook.environmentKey`. Same
    // module-boundary reason as above.
    private static let synthesizedFavoriteCountKey = "UITEST_SIMULATE_POST_ONBOARDING_FAVORITE_COUNT"

    func testDeferThenColdLaunchSuppressesRePrompt() {
        let app = XCUIApplication()

        // First launch — UITEST_RESET_STATE wipes prior cadence residue
        // (including laughtrack.notifications.softPushPermissionState).
        // UITEST_GUEST_BROWSING seeds the first-entry choice so the shell
        // mounts directly past the auth gate. The env var arms
        // `DebugSimulatedFavoriteHook` to fire 3 synthetic
        // `handleComedianFavoriteAdded(isPostOnboarding: true)` calls once
        // the shell's `.task` runs.
        app.launchArguments = ["UITEST_RESET_STATE", "UITEST_GUEST_BROWSING"]
        app.launchEnvironment = [Self.synthesizedFavoriteCountKey: "3"]
        app.launch()

        let deferButton = app.buttons[Self.softPushDeferButton]
        XCTAssertTrue(
            deferButton.waitForExistence(timeout: 20),
            "Soft push-prompt sheet's Maybe-later button did not appear after 3 synthesized favorites. The cadence wiring in handleComedianFavoriteAdded likely regressed."
        )

        deferButton.tap()

        XCTAssertTrue(
            waitForElementGone(deferButton, timeout: 5),
            "Maybe-later button should disappear after defer tap; sheet dismissal stalled."
        )

        // Cold launch. Terminating and relaunching reinvokes
        // `LaughTrackApp.init`, which calls `recordColdLaunchSession()` — that
        // is the only signal that ticks `sessionCountSinceLastDeferral`. Do
        // NOT pass UITEST_RESET_STATE on this launch — the deferral state must
        // persist for the suppression assertion below to be meaningful.
        app.terminate()
        app.launchArguments = ["UITEST_GUEST_BROWSING"]
        app.launchEnvironment = [Self.synthesizedFavoriteCountKey: "3"]
        app.launch()

        // After one defer + one cold launch:
        //   sessionCountSinceLastDeferral = 1 (< requiredSessionsSinceDeferral=3)
        //   lastDeferredAt = within backoffDays[1]=3 days
        // Either gate alone would suppress the prompt; both being active is
        // belt-and-braces. Re-firing the synthesized favorite signals must NOT
        // bring the sheet back.
        XCTAssertFalse(
            deferButton.waitForExistence(timeout: 6),
            "Cadence must suppress the prompt after a single defer + one cold launch — session and backoff gates have not had time to clear."
        )
    }

    /// XCUITest has `waitForExistence(timeout:)` but no symmetric
    /// "wait for the element to vanish" helper. Poll the existence flag
    /// directly so a sheet-dismiss animation that takes longer than a
    /// runloop tick doesn't false-fail the test.
    private func waitForElementGone(_ element: XCUIElement, timeout: TimeInterval) -> Bool {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if !element.exists { return true }
            usleep(150_000)
        }
        return !element.exists
    }
}
