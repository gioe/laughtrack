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

        #expect(env.coordinator.presentation == .hidden)
        #expect(env.stateStore.postOnboardingFavoriteCount == 0)
    }

    @Test("does not present until the engagement trigger threshold is crossed")
    func doesNotPresentBeforeEngagementTrigger() async {
        let env = makeEnvironment(status: .notDetermined)

        await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)
        await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)

        #expect(env.coordinator.presentation == .hidden)
        #expect(env.stateStore.postOnboardingFavoriteCount == 2)
    }

    @Test("presents the sheet on the 3rd post-onboarding favorite when status is notDetermined")
    func presentsSheetOnThirdPostOnboardingFavorite() async {
        let env = makeEnvironment(status: .notDetermined)

        await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)
        await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)
        await env.coordinator.handleComedianFavoriteAdded(isPostOnboarding: true)

        #expect(env.coordinator.presentation == .promptingSheet)
        #expect(env.coordinator.hasPresentedThisSession)
        #expect(env.stateStore.postOnboardingFavoriteCount == 3)
    }

    @Test("does not present when push alerts are already enabled in app preferences")
    func doesNotPresentWhenPushAlreadyEnabled() async {
        let env = makeEnvironment(status: .notDetermined)
        env.preferenceStore.setFavoriteComedianPushAlertsEnabled(true)

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(env.coordinator.presentation == .hidden)
    }

    @Test("does not present when the deferral cap has been reached")
    func doesNotPresentWhenDeferralCapReached() async {
        let env = makeEnvironment(status: .notDetermined)
        env.stateStore.recordDeferral()
        env.stateStore.recordDeferral()
        env.stateStore.recordDeferral()

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(env.coordinator.presentation == .hidden)
    }

    @Test("does not present when OS authorization is already denied")
    func doesNotPresentWhenAuthorizationDenied() async {
        let env = makeEnvironment(status: .denied)

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(env.coordinator.presentation == .hidden)
    }

    @Test("does not silently flip app preference when status is authorized but pref is off")
    func doesNotFlipPreferenceWhenAuthorizedButPrefOff() async {
        let env = makeEnvironment(status: .authorized)

        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(env.coordinator.presentation == .hidden)
        #expect(!env.preferenceStore.preferences.favoriteComedianPushAlertsEnabled)
    }

    @Test("does not re-present within the same session after it was already shown")
    func doesNotRePresentWithinSession() async {
        let env = makeEnvironment(status: .notDetermined)

        await fireFavoriteEvents(env.coordinator, count: 3)
        #expect(env.coordinator.presentation == .promptingSheet)

        env.coordinator.presentation = .hidden
        await fireFavoriteEvents(env.coordinator, count: 5)

        #expect(env.coordinator.presentation == .hidden)
    }

    @Test("enableTapped on notDetermined requests authorization and applies pref on grant")
    func enableTappedNotDeterminedGrantApplies() async throws {
        let env = makeEnvironment(status: .notDetermined, requestResult: true)
        env.coordinator.presentation = .promptingSheet

        await env.coordinator.enableTapped()
        env.coordinator.handleSheetDismissed()

        #expect(env.coordinator.presentation == .hidden)
        #expect(await env.requester.requestCount == 1)
        #expect(env.preferenceStore.preferences.favoriteComedianPushAlertsEnabled)
    }

    @Test("enableTapped on notDetermined surfaces the Open-Settings alert when authorization is not granted")
    func enableTappedNotDeterminedDenyShowsAlert() async throws {
        // requestAuthorization returns false both when the user taps Don't
        // Allow and when the underlying UN call throws — either way the
        // coordinator presents the same TASK-2587 Open Settings alert via
        // the buffered post-dismiss transition (covers criterion 8489's
        // "Don't-Allow response to the OS prompt" branch).
        let env = makeEnvironment(status: .notDetermined, requestResult: false)
        env.coordinator.presentation = .promptingSheet

        await env.coordinator.enableTapped()
        // The sheet must dismiss before the alert is presented — the view
        // layer flips the binding from .promptingSheet → .hidden first, then
        // SwiftUI fires onDismiss, which is wired to handleSheetDismissed.
        #expect(env.coordinator.presentation == .hidden)
        env.coordinator.handleSheetDismissed()

        #expect(env.coordinator.presentation == .deniedAlert)
        #expect(!env.preferenceStore.preferences.favoriteComedianPushAlertsEnabled)
    }

    @Test("enableTapped when status is already denied surfaces the Open-Settings alert via the buffered onDismiss transition")
    func enableTappedDeniedShowsAlertViaBufferedDismiss() async {
        // Covers criterion 8489's ".denied at sheet entry" branch: the OS
        // status is already .denied when the user lands in the sheet and
        // taps Enable. The coordinator must drive the sheet closed first,
        // then transition into .deniedAlert from handleSheetDismissed —
        // never both at once on the same scene.
        let env = makeEnvironment(status: .denied)
        env.coordinator.presentation = .promptingSheet

        await env.coordinator.enableTapped()
        #expect(env.coordinator.presentation == .hidden)
        env.coordinator.handleSheetDismissed()

        #expect(env.coordinator.presentation == .deniedAlert)
        #expect(await env.requester.requestCount == 0)
        #expect(!env.preferenceStore.preferences.favoriteComedianPushAlertsEnabled)
    }

    @Test("enableTapped when status is already authorized applies pref without prompting and without alert")
    func enableTappedAuthorizedAppliesPrefWithoutPrompting() async {
        let env = makeEnvironment(status: .authorized)
        env.coordinator.presentation = .promptingSheet

        await env.coordinator.enableTapped()
        env.coordinator.handleSheetDismissed()

        #expect(env.preferenceStore.preferences.favoriteComedianPushAlertsEnabled)
        #expect(await env.requester.requestCount == 0)
        #expect(env.coordinator.presentation == .hidden)
    }

    @Test("deferTapped records a deferral and dismisses the prompt")
    func deferTappedRecordsDeferralAndDismisses() {
        let env = makeEnvironment(status: .notDetermined)
        env.coordinator.presentation = .promptingSheet

        env.coordinator.deferTapped()

        #expect(env.coordinator.presentation == .hidden)
        #expect(env.stateStore.deferralCount == 1)
    }

    @Test("swipe-to-dismiss (handleSheetDismissed without an explicit response) records a deferral so the cap binds across sessions")
    func sheetDismissedWithoutExplicitResponseRecordsDeferral() async {
        let env = makeEnvironment(status: .notDetermined)
        await fireFavoriteEvents(env.coordinator, count: 3)
        #expect(env.coordinator.presentation == .promptingSheet)
        env.coordinator.presentation = .hidden

        env.coordinator.handleSheetDismissed()

        #expect(env.stateStore.deferralCount == 1)
        #expect(env.coordinator.presentation == .hidden)
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

        #expect(env.coordinator.presentation == .hidden)
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

        #expect(env.coordinator.presentation == .hidden)
    }

    // MARK: - nextPresentation helper (AppShellView softPushPresentationBinding setter)

    @Test("nextPresentation returns .hidden when the dismissed surface matches the active alert (normal dismiss path)")
    func nextPresentationDismissesActiveAlert() {
        // SwiftUI flips the .alert binding to false when the user dismisses
        // the Open-Settings alert. The setter resolves the next presentation
        // through nextPresentation(after:current:), which must return .hidden
        // so the coordinator transitions out of .deniedAlert.
        let next = SoftPushPromptCoordinator.nextPresentation(
            after: .deniedAlert,
            current: .deniedAlert
        )

        #expect(next == .hidden)
    }

    @Test("nextPresentation rejects cross-surface dismiss (alert binding written false while a sheet is up leaves the sheet state intact)")
    func nextPresentationRejectsCrossSurfaceClobber() {
        // SwiftUI re-evaluates every projected binding on each render pass.
        // If the .alert binding is read while presentation == .promptingSheet
        // and its setter is invoked with `false` (the binding's current
        // value), the setter must NOT flip the coordinator to .hidden —
        // doing so would kill the live sheet. Verifies the cross-surface
        // guard called out in TASK-2594 review #4938 comment #2798.
        let next = SoftPushPromptCoordinator.nextPresentation(
            after: .deniedAlert,
            current: .promptingSheet
        )

        #expect(next == .promptingSheet)
    }

    @Test("presenting the sheet emits push_soft_prompt_shown with trigger=engagement_moment and the current deferral count")
    func presentingSheetEmitsSoftPromptShownEvent() async {
        let analytics = RecordingAnalyticsManager()
        let env = makeEnvironment(status: .notDetermined, analytics: analytics)
        // Don't pre-set a deferral — recordDeferral resets
        // sessionCountSinceLastDeferral to 0, which trips the cadence's
        // post-deferral session gate and would suppress the sheet entirely.
        // The fresh-state path (deferralCount=0) is the canonical first
        // present-time and exercises the same emission code.

        await fireFavoriteEvents(env.coordinator, count: 3)

        #expect(env.coordinator.presentation == .promptingSheet)
        let shown = analytics.events.filter { $0.name == PushAnalyticsEvents.softPromptShown }
        #expect(shown.count == 1)
        #expect(shown.first?.string(PushAnalyticsEvents.Param.trigger) == PushAnalyticsEvents.Trigger.engagementMoment.rawValue)
        #expect(shown.first?.int(PushAnalyticsEvents.Param.deferralCount) == 0)
    }

    @Test("enableTapped emits push_soft_prompt_enable_tapped and push_os_prompt_result on notDetermined grant")
    func enableTappedEmitsEnableTappedAndOSPromptResultEvents() async {
        let analytics = RecordingAnalyticsManager()
        let env = makeEnvironment(status: .notDetermined, requestResult: true, analytics: analytics)
        env.coordinator.presentation = .promptingSheet

        await env.coordinator.enableTapped()

        let enableTapped = analytics.events.filter { $0.name == PushAnalyticsEvents.softPromptEnableTapped }
        #expect(enableTapped.count == 1)
        #expect(enableTapped.first?.string(PushAnalyticsEvents.Param.trigger) == PushAnalyticsEvents.Trigger.engagementMoment.rawValue)
        #expect(enableTapped.first?.int(PushAnalyticsEvents.Param.deferralCount) == 0)

        let osResult = analytics.events.filter { $0.name == PushAnalyticsEvents.osPromptResult }
        #expect(osResult.count == 1)
        #expect(osResult.first?.bool(PushAnalyticsEvents.Param.granted) == true)
        #expect(osResult.first?.string(PushAnalyticsEvents.Param.trigger) == PushAnalyticsEvents.Trigger.engagementMoment.rawValue)
    }

    @Test("enableTapped on notDetermined deny emits push_os_prompt_result with granted=false")
    func enableTappedNotDeterminedDenyEmitsOSPromptResultFalse() async {
        let analytics = RecordingAnalyticsManager()
        let env = makeEnvironment(status: .notDetermined, requestResult: false, analytics: analytics)
        env.coordinator.presentation = .promptingSheet

        await env.coordinator.enableTapped()

        let osResult = analytics.events.filter { $0.name == PushAnalyticsEvents.osPromptResult }
        #expect(osResult.count == 1)
        #expect(osResult.first?.bool(PushAnalyticsEvents.Param.granted) == false)
        #expect(osResult.first?.string(PushAnalyticsEvents.Param.trigger) == PushAnalyticsEvents.Trigger.engagementMoment.rawValue)
    }

    @Test("enableTapped does NOT emit push_os_prompt_result when status is already authorized")
    func enableTappedAuthorizedDoesNotEmitOSPromptResult() async {
        let analytics = RecordingAnalyticsManager()
        let env = makeEnvironment(status: .authorized, analytics: analytics)
        env.coordinator.presentation = .promptingSheet

        await env.coordinator.enableTapped()

        #expect(analytics.events.contains(where: { $0.name == PushAnalyticsEvents.softPromptEnableTapped }))
        #expect(!analytics.events.contains(where: { $0.name == PushAnalyticsEvents.osPromptResult }))
    }

    @Test("deferTapped emits push_soft_prompt_defer_tapped with the pre-increment deferral count")
    func deferTappedEmitsDeferTappedEventWithPreIncrementCount() {
        let analytics = RecordingAnalyticsManager()
        let env = makeEnvironment(status: .notDetermined, analytics: analytics)
        env.stateStore.recordDeferral()
        env.stateStore.recordDeferral()
        env.coordinator.presentation = .promptingSheet

        env.coordinator.deferTapped()

        let deferTapped = analytics.events.filter { $0.name == PushAnalyticsEvents.softPromptDeferTapped }
        #expect(deferTapped.count == 1)
        #expect(deferTapped.first?.string(PushAnalyticsEvents.Param.trigger) == PushAnalyticsEvents.Trigger.engagementMoment.rawValue)
        // deferral_count reflects the cadence state the sheet was shown against, not the post-tap increment.
        #expect(deferTapped.first?.int(PushAnalyticsEvents.Param.deferralCount) == 2)
        #expect(env.stateStore.deferralCount == 3)
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
        analytics: (any AnalyticsManagerProtocol)? = nil,
        now: @escaping () -> Date = { Date() }
    ) -> Environment {
        makeEnvironment(
            statusSequence: [status],
            requestResult: requestResult,
            analytics: analytics,
            now: now
        )
    }

    private func makeEnvironment(
        statusSequence: [PushAuthorizationStatus],
        requestResult: Bool = true,
        analytics: (any AnalyticsManagerProtocol)? = nil,
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
            analytics: analytics,
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
final class RecordingAnalyticsManager: AnalyticsManagerProtocol {
    struct Recorded {
        let name: String
        let parameters: [String: Any]?

        func string(_ key: String) -> String? { parameters?[key] as? String }
        func bool(_ key: String) -> Bool? { parameters?[key] as? Bool }
        func int(_ key: String) -> Int? { parameters?[key] as? Int }
    }

    private(set) var events: [Recorded] = []

    func addProvider(_ provider: AnalyticsProvider) {}

    func track(_ event: AnalyticsEvent) {
        events.append(Recorded(name: event.name, parameters: event.parameters))
    }

    func track(_ name: String, parameters: [String: Any]?) {
        events.append(Recorded(name: name, parameters: parameters))
    }

    func trackScreen(_ name: String, parameters: [String: Any]?) {}
    func setUserProperty(_ value: String?, forName name: String) {}
    func setUserID(_ userID: String?) {}
    func reset() {}
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
