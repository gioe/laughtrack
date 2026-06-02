import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackCore

@Suite("SoftPushPromptCoordinator")
@MainActor
struct SoftPushPromptCoordinatorTests {
    @Test("does nothing when the favorite event happens during onboarding")
    func ignoresOnboardingFavorites() async {
        let env = makeEnvironment(status: .notDetermined)

        for _ in 0..<5 {
            await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: false)
        }

        #expect(!env.coordinator.isPromptPresented)
        #expect(env.stateStore.postOnboardingFavoriteCount == 0)
    }

    @Test("does not present until the engagement trigger threshold is crossed")
    func doesNotPresentBeforeEngagementTrigger() async {
        let env = makeEnvironment(status: .notDetermined)

        await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)
        await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)

        #expect(!env.coordinator.isPromptPresented)
        #expect(env.stateStore.postOnboardingFavoriteCount == 2)
    }

    @Test("presents the sheet on the 3rd post-onboarding favorite when status is notDetermined")
    func presentsSheetOnThirdPostOnboardingFavorite() async {
        let env = makeEnvironment(status: .notDetermined)

        await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)
        await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)
        await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)

        #expect(env.coordinator.isPromptPresented)
        #expect(env.coordinator.hasPresentedThisSession)
        #expect(env.stateStore.postOnboardingFavoriteCount == 3)
    }

    @Test("does not present when push alerts are already enabled in app preferences")
    func doesNotPresentWhenPushAlreadyEnabled() async {
        let env = makeEnvironment(status: .notDetermined)
        env.preferenceStore.setFavoriteComedianPushAlertsEnabled(true)

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(!env.coordinator.isPromptPresented)
    }

    @Test("does not present when the deferral cap has been reached")
    func doesNotPresentWhenDeferralCapReached() async {
        let env = makeEnvironment(status: .notDetermined)
        env.stateStore.recordDeferral()
        env.stateStore.recordDeferral()
        env.stateStore.recordDeferral()

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(!env.coordinator.isPromptPresented)
    }

    @Test("does not present when OS authorization is already denied")
    func doesNotPresentWhenAuthorizationDenied() async {
        let env = makeEnvironment(status: .denied)

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(!env.coordinator.isPromptPresented)
        #expect(!env.coordinator.isDeniedAlertPresented)
    }

    @Test("does not silently flip app preference when status is authorized but pref is off")
    func doesNotFlipPreferenceWhenAuthorizedButPrefOff() async {
        let env = makeEnvironment(status: .authorized)

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(!env.coordinator.isPromptPresented)
        #expect(!env.preferenceStore.preferences.favoriteComedianPushAlertsEnabled)
    }

    @Test("does not re-present within the same session after it was already shown")
    func doesNotRePresentWithinSession() async {
        let env = makeEnvironment(status: .notDetermined)

        await fireFavoriteEvents(env.coordinator, count: 3)
        #expect(env.coordinator.isPromptPresented)

        env.coordinator.isPromptPresented = false
        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(!env.coordinator.isPromptPresented)
    }

    @Test("enableTapped on notDetermined requests authorization and applies pref on grant")
    func enableTappedNotDeterminedGrantApplies() async throws {
        let env = makeEnvironment(status: .notDetermined, requestResult: true)
        env.coordinator.isPromptPresented = true

        await env.coordinator.enableTapped()

        #expect(!env.coordinator.isPromptPresented)
        #expect(!env.coordinator.isDeniedAlertPresented)
        #expect(await env.requester.requestCount == 1)
        #expect(env.preferenceStore.preferences.favoriteComedianPushAlertsEnabled)
    }

    @Test("enableTapped on notDetermined surfaces the Open-Settings alert when authorization is not granted")
    func enableTappedNotDeterminedDenyShowsAlert() async throws {
        // requestAuthorization returns false both when the user taps Don't
        // Allow and when the underlying UN call throws — either way the
        // coordinator presents the same TASK-2587 Open Settings alert.
        let env = makeEnvironment(status: .notDetermined, requestResult: false)
        env.coordinator.isPromptPresented = true

        await env.coordinator.enableTapped()

        #expect(env.coordinator.isDeniedAlertPresented)
        #expect(!env.preferenceStore.preferences.favoriteComedianPushAlertsEnabled)
    }

    @Test("enableTapped when status is already denied surfaces the Open-Settings alert immediately")
    func enableTappedDeniedShowsAlertImmediately() async {
        let env = makeEnvironment(status: .denied)
        env.coordinator.isPromptPresented = true

        await env.coordinator.enableTapped()

        #expect(env.coordinator.isDeniedAlertPresented)
        #expect(await env.requester.requestCount == 0)
        #expect(!env.preferenceStore.preferences.favoriteComedianPushAlertsEnabled)
    }

    @Test("enableTapped when status is already authorized applies pref without prompting and without alert")
    func enableTappedAuthorizedAppliesPrefWithoutPrompting() async {
        let env = makeEnvironment(status: .authorized)
        env.coordinator.isPromptPresented = true

        await env.coordinator.enableTapped()

        #expect(env.preferenceStore.preferences.favoriteComedianPushAlertsEnabled)
        #expect(await env.requester.requestCount == 0)
        #expect(!env.coordinator.isDeniedAlertPresented)
    }

    @Test("deferTapped records a deferral and dismisses the prompt")
    func deferTappedRecordsDeferralAndDismisses() {
        let env = makeEnvironment(status: .notDetermined)
        env.coordinator.isPromptPresented = true

        env.coordinator.deferTapped()

        #expect(!env.coordinator.isPromptPresented)
        #expect(env.stateStore.deferralCount == 1)
    }

    @Test("swipe-to-dismiss (handleSheetDismissed without an explicit response) records a deferral so the cap binds across sessions")
    func sheetDismissedWithoutExplicitResponseRecordsDeferral() async {
        let env = makeEnvironment(status: .notDetermined)
        await fireFavoriteEvents(env.coordinator, count: 3)
        #expect(env.coordinator.isPromptPresented)
        env.coordinator.isPromptPresented = false

        env.coordinator.handleSheetDismissed()

        #expect(env.stateStore.deferralCount == 1)
    }

    @Test("handleSheetDismissed after deferTapped does not double-count the deferral")
    func sheetDismissedAfterDeferDoesNotDoubleCount() async {
        let env = makeEnvironment(status: .notDetermined)
        await fireFavoriteEvents(env.coordinator, count: 3)

        env.coordinator.deferTapped()
        env.coordinator.handleSheetDismissed()

        #expect(env.stateStore.deferralCount == 1)
    }

    @Test("handleSheetDismissed after enableTapped does not record a deferral")
    func sheetDismissedAfterEnableDoesNotRecordDeferral() async {
        let env = makeEnvironment(status: .notDetermined, requestResult: true)
        await fireFavoriteEvents(env.coordinator, count: 3)

        await env.coordinator.enableTapped()
        env.coordinator.handleSheetDismissed()

        #expect(env.stateStore.deferralCount == 0)
    }

    @Test("post-onboarding favorite counter stops growing once the sheet has been shown this session")
    func postOnboardingFavoriteCounterStopsAfterPresentation() async {
        let env = makeEnvironment(status: .notDetermined)
        await fireFavoriteEvents(env.coordinator, count: 3)
        #expect(env.stateStore.postOnboardingFavoriteCount == 3)

        await fireFavoriteEvents(env.coordinator, count: 10)

        #expect(env.stateStore.postOnboardingFavoriteCount == 3)
    }

    @Test("post-onboarding favorite counter stops growing once push is already enabled")
    func postOnboardingFavoriteCounterStopsAfterPushEnabled() async {
        let env = makeEnvironment(status: .notDetermined)
        env.preferenceStore.setFavoriteComedianPushAlertsEnabled(true)

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(env.stateStore.postOnboardingFavoriteCount == 0)
    }

    @Test("openSystemSettings forwards to the injected opener")
    func openSystemSettingsForwardsToOpener() {
        let env = makeEnvironment(status: .denied)

        env.coordinator.openSystemSettings()

        #expect(env.opener.openCount == 1)
    }

    // MARK: - Cadence wiring (criterion 8456/8457 end-to-end)

    @Test("after a deferral, the coordinator suppresses the sheet while sessionCountSinceLastDeferral is still 0 (post-deferral session gate is wired)")
    func suppressesAfterDeferralWhenSessionGateNotMet() async {
        // recordDeferral stamps lastDeferredAt at the deferral instant; the
        // mutable clock is then advanced 30 days forward so the backoff gate
        // can never bind — only the session-count gate (0 cold launches
        // recorded) can suppress here. If a future refactor drops
        // sessionCountSinceLastDeferral from the coordinator's Cadence.Inputs
        // construction, this test catches it.
        let clock = MutableClock(Self.fixedNow)
        let env = makeEnvironment(status: .notDetermined, now: { clock.now })
        env.stateStore.recordDeferral()
        clock.advance(by: 30 * 86_400)

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(!env.coordinator.isPromptPresented)
    }

    @Test("after a deferral, the coordinator suppresses the sheet inside the 3-day backoff window (recency gate is wired)")
    func suppressesInsideBackoffWindowAfterFirstDeferral() async {
        // Enough cold-launch sessions to clear the session-count gate, but
        // the wall clock advances only 1 day past the deferral — well inside
        // the 3-day backoff after a single decline. The deferral instant is
        // stamped by the store using the same clock, so lastDeferredAt =
        // Self.fixedNow and the cadence sees elapsed = 1 day. If a future
        // refactor drops lastDeferredAt or `now` from the coordinator's
        // Cadence.Inputs construction, this test catches it.
        let clock = MutableClock(Self.fixedNow)
        let env = makeEnvironment(status: .notDetermined, now: { clock.now })
        env.stateStore.recordDeferral()
        env.stateStore.recordColdLaunchSession()
        env.stateStore.recordColdLaunchSession()
        env.stateStore.recordColdLaunchSession()
        clock.advance(by: 1 * 86_400)

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(!env.coordinator.isPromptPresented)
    }

    private static let fixedNow = Date(timeIntervalSince1970: 1_700_000_000)

    private func fireFavoriteEvents(
        _ coordinator: SoftPushPromptCoordinator,
        count: Int
    ) async {
        for _ in 0..<count {
            await coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)
        }
    }

    private func makeEnvironment(
        status: PushAuthorizationStatus,
        requestResult: Bool = true,
        now: @escaping () -> Date = { Date() }
    ) -> Environment {
        makeEnvironment(statusSequence: [status], requestResult: requestResult, now: now)
    }

    private func makeEnvironment(
        statusSequence: [PushAuthorizationStatus],
        requestResult: Bool = true,
        now: @escaping () -> Date = { Date() }
    ) -> Environment {
        let suiteName = "SoftPushPromptCoordinatorTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let storage = AppStateStorage(userDefaults: defaults)
        let stateStore = PushPermissionStateStore(appStateStorage: storage, now: now)
        let preferenceStore = NotificationPreferenceStore(appStateStorage: storage)
        let statusProvider = ScriptedPushAuthorizationStatusProvider(sequence: statusSequence)
        let requester = RecordingPushAuthorizationRequester(result: requestResult)
        let opener = RecordingSystemSettingsOpener()
        let coordinator = SoftPushPromptCoordinator(
            stateStore: stateStore,
            notificationPreferenceStore: preferenceStore,
            authorizationStatusProvider: statusProvider,
            authorizationRequester: requester,
            systemSettingsOpener: opener,
            now: now
        )
        return Environment(
            coordinator: coordinator,
            stateStore: stateStore,
            preferenceStore: preferenceStore,
            requester: requester,
            opener: opener
        )
    }

    @MainActor
    private struct Environment {
        let coordinator: SoftPushPromptCoordinator
        let stateStore: PushPermissionStateStore
        let preferenceStore: NotificationPreferenceStore
        let requester: RecordingPushAuthorizationRequester
        let opener: RecordingSystemSettingsOpener
    }
}

private actor ScriptedPushAuthorizationStatusProvider: PushAuthorizationStatusProviding {
    private var sequence: [PushAuthorizationStatus]
    private let fallback: PushAuthorizationStatus

    init(sequence: [PushAuthorizationStatus]) {
        precondition(!sequence.isEmpty)
        self.sequence = sequence
        self.fallback = sequence.last!
    }

    func currentAuthorizationStatus() async -> PushAuthorizationStatus {
        if sequence.count > 1 {
            return sequence.removeFirst()
        }
        return sequence.first ?? fallback
    }
}

private actor RecordingPushAuthorizationRequester: PushAuthorizationRequesting {
    private let result: Bool
    private(set) var requestCount = 0

    init(result: Bool) {
        self.result = result
    }

    func requestAuthorization() async -> Bool {
        requestCount += 1
        return result
    }
}

@MainActor
private final class RecordingSystemSettingsOpener: SystemSettingsOpening {
    private(set) var openCount = 0

    func openAppSystemSettings() {
        openCount += 1
    }
}

@MainActor
private final class MutableClock {
    private var current: Date

    init(_ initial: Date) {
        self.current = initial
    }

    var now: Date { current }

    func advance(by interval: TimeInterval) {
        current = current.addingTimeInterval(interval)
    }
}
