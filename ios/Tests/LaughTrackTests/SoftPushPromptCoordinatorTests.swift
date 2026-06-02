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

    @Test("enableTapped when the OS prompt resolves to denied surfaces the same Open-Settings alert pattern as TASK-2587")
    func enableTappedNotDeterminedDenyShowsAlert() async throws {
        // After the user taps Don't Allow on the OS prompt, the system status
        // flips from .notDetermined to .denied. The coordinator should detect
        // that and present the same alert TASK-2587 ships in Settings.
        let env = makeEnvironment(
            statusSequence: [.notDetermined, .denied],
            requestResult: false
        )
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

    @Test("deferTapped records a deferral and dismisses the prompt")
    func deferTappedRecordsDeferralAndDismisses() {
        let env = makeEnvironment(status: .notDetermined)
        env.coordinator.isPromptPresented = true

        env.coordinator.deferTapped()

        #expect(!env.coordinator.isPromptPresented)
        #expect(env.stateStore.deferralCount == 1)
    }

    @Test("openSystemSettings forwards to the injected opener")
    func openSystemSettingsForwardsToOpener() {
        let env = makeEnvironment(status: .denied)

        env.coordinator.openSystemSettings()

        #expect(env.opener.openCount == 1)
    }

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
        requestResult: Bool = true
    ) -> Environment {
        makeEnvironment(statusSequence: [status], requestResult: requestResult)
    }

    private func makeEnvironment(
        statusSequence: [PushAuthorizationStatus],
        requestResult: Bool = true
    ) -> Environment {
        let suiteName = "SoftPushPromptCoordinatorTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let storage = AppStateStorage(userDefaults: defaults)
        let stateStore = PushPermissionStateStore(appStateStorage: storage)
        let preferenceStore = NotificationPreferenceStore(appStateStorage: storage)
        let statusProvider = ScriptedPushAuthorizationStatusProvider(sequence: statusSequence)
        let requester = RecordingPushAuthorizationRequester(result: requestResult)
        let opener = RecordingSystemSettingsOpener()
        let coordinator = SoftPushPromptCoordinator(
            stateStore: stateStore,
            notificationPreferenceStore: preferenceStore,
            authorizationStatusProvider: statusProvider,
            authorizationRequester: requester,
            systemSettingsOpener: opener
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
