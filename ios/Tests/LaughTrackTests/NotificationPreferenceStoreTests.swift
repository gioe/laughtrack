import Foundation
import HTTPTypes
import OpenAPIRuntime
import Testing
import LaughTrackAPIClient
import LaughTrackBridge
@testable import LaughTrackCore

@Suite("NotificationPreferenceStore")
@MainActor
struct NotificationPreferenceStoreTests {
    @Test("notification preferences persist and reload from app state storage")
    func notificationPreferencesPersistAndReload() {
        let storage = makeStorage(name: "persist")
        let store = NotificationPreferenceStore(appStateStorage: storage)

        store.setFavoriteComedianEmailAlertsEnabled(true)
        store.setFavoriteComedianPushAlertsEnabled(true)

        let reloadedStore = NotificationPreferenceStore(appStateStorage: storage)
        #expect(reloadedStore.preferences.favoriteComedianEmailAlertsEnabled)
        #expect(reloadedStore.preferences.favoriteComedianPushAlertsEnabled)
        #expect(reloadedStore.preferences.hasEnabledChannel)
    }

    @Test("reset clears persisted notification preferences")
    func resetClearsPersistedPreferences() {
        let storage = makeStorage(name: "reset")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        store.setFavoriteComedianEmailAlertsEnabled(true)

        store.reset()

        let reloadedStore = NotificationPreferenceStore(appStateStorage: storage)
        #expect(reloadedStore.preferences == .default)
    }

    @Test("legacy favorite comedian alert payload maps to the email channel")
    func legacyFavoriteComedianAlertPayloadMapsToEmailChannel() throws {
        let data = #"{"favoriteComedianAlertsEnabled":true}"#.data(using: .utf8)!

        let preferences = try JSONDecoder().decode(NotificationPreferences.self, from: data)

        #expect(preferences.favoriteComedianEmailAlertsEnabled)
        #expect(!preferences.favoriteComedianPushAlertsEnabled)
    }

    @Test("settings model syncs favorite comedian email channel through injected API boundary")
    func settingsModelSyncsEmailChannelThroughInjectedBoundary() async throws {
        let storage = makeStorage(name: "sync")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let syncClient = RecordingNotificationPreferenceSync()
        let model = SettingsNotificationPreferenceModel(store: store, syncClient: syncClient)

        model.setFavoriteComedianEmailAlertsEnabled(true)
        try await waitUntil { await syncClient.calls == [.init(enabled: true, channel: .email)] }

        #expect(model.preferences.favoriteComedianEmailAlertsEnabled)
    }

    @Test("settings model deactivates current device token when push channel is disabled")
    func settingsModelDeactivatesCurrentDeviceTokenWhenPushDisabled() async throws {
        let storage = makeStorage(name: "push-disable")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        store.setFavoriteComedianPushAlertsEnabled(true)
        let pushTokenManager = RecordingPushDeviceTokenManager()
        let model = SettingsNotificationPreferenceModel(
            store: store,
            pushTokenManager: pushTokenManager
        )

        model.setFavoriteComedianPushAlertsEnabled(false)
        try await waitUntil { await pushTokenManager.deactivateCalls == 1 }

        #expect(!model.preferences.favoriteComedianPushAlertsEnabled)
    }

    @Test("settings push toggle enables directly when authorization is already granted")
    func settingsPushToggleEnablesWhenAuthorized() async throws {
        let storage = makeStorage(name: "push-authorized")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let pushTokenManager = RecordingPushDeviceTokenManager()
        let statusProvider = SingleStatusPushAuthorizationStatusProvider(status: .authorized)
        let requester = RecordingPushAuthorizationRequester(result: true)
        let model = SettingsNotificationPreferenceModel(
            store: store,
            pushTokenManager: pushTokenManager,
            pushAuthorizationStatusProvider: statusProvider,
            pushAuthorizationRequester: requester
        )

        model.setFavoriteComedianPushAlertsEnabled(true)
        try await waitUntil { await pushTokenManager.registerCalls == 1 }

        #expect(model.preferences.favoriteComedianPushAlertsEnabled)
        #expect(!model.isPushDeniedAlertPresented)
        #expect(await requester.requestCount == 0)
    }

    @Test("settings push toggle requests authorization when status is notDetermined")
    func settingsPushToggleRequestsWhenNotDetermined() async throws {
        let storage = makeStorage(name: "push-notDetermined")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let pushTokenManager = RecordingPushDeviceTokenManager()
        let statusProvider = SingleStatusPushAuthorizationStatusProvider(status: .notDetermined)
        let requester = RecordingPushAuthorizationRequester(result: true)
        let model = SettingsNotificationPreferenceModel(
            store: store,
            pushTokenManager: pushTokenManager,
            pushAuthorizationStatusProvider: statusProvider,
            pushAuthorizationRequester: requester
        )

        model.setFavoriteComedianPushAlertsEnabled(true)
        try await waitUntil { await requester.requestCount == 1 }
        try await waitUntil { await pushTokenManager.registerCalls == 1 }

        #expect(model.preferences.favoriteComedianPushAlertsEnabled)
        #expect(!model.isPushDeniedAlertPresented)
    }

    @Test("settings push toggle shows deep-link alert when authorization is denied")
    func settingsPushToggleShowsDeepLinkAlertWhenDenied() async throws {
        let storage = makeStorage(name: "push-denied")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let pushTokenManager = RecordingPushDeviceTokenManager()
        let statusProvider = SingleStatusPushAuthorizationStatusProvider(status: .denied)
        let requester = RecordingPushAuthorizationRequester(result: false)
        let model = SettingsNotificationPreferenceModel(
            store: store,
            pushTokenManager: pushTokenManager,
            pushAuthorizationStatusProvider: statusProvider,
            pushAuthorizationRequester: requester
        )

        model.setFavoriteComedianPushAlertsEnabled(true)
        try await waitUntil { model.isPushDeniedAlertPresented }

        #expect(!model.preferences.favoriteComedianPushAlertsEnabled)
        #expect(await pushTokenManager.registerCalls == 0)
        #expect(await requester.requestCount == 0)
    }

    @Test("openSystemSettings forwards to the injected settings opener")
    func openSystemSettingsForwardsToOpener() async {
        let storage = makeStorage(name: "open-settings")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let opener = RecordingSystemSettingsOpener()
        let model = SettingsNotificationPreferenceModel(
            store: store,
            systemSettingsOpener: opener
        )

        model.openSystemSettings()

        #expect(opener.openCount == 1)
    }

    @Test("push token manager registers refreshed APNs tokens through the generated client")
    func pushTokenManagerUploadsDeviceToken() async throws {
        let storage = makeStorage(name: "push-upload")
        let transport = StubClientTransport()
        let bodies = PushTokenBodyRecorder()
        transport.setHandler { _, body, _, _ in
            await bodies.record(body)
            return pushTokenJSONResponse(
                status: 200,
                body: #"{"data":{"id":"1","platform":"ios","isActive":true}}"#
            )
        }
        let manager = PushDeviceTokenManager(
            apiClient: makePushTokenClient(transport: transport),
            appStateStorage: storage
        )

        await manager.uploadDeviceToken(Data([0xAB, 0xCD, 0xEF]))

        let captured = try #require(transport.capturedRequests.first)
        #expect(captured.operationID == "registerMePushToken")
        #expect(captured.method == .post)
        #expect(captured.path == "/api/v1/me/push-tokens")
        let json = try #require(await bodies.lastJSON())
        #expect(json["token"] as? String == "abcdef")
        #expect(json["platform"] as? String == "ios")
    }

    @Test("push token manager deactivates the current uploaded token through the generated client")
    func pushTokenManagerDeactivatesCurrentDeviceToken() async throws {
        let storage = makeStorage(name: "push-deactivate")
        let transport = StubClientTransport()
        let bodies = PushTokenBodyRecorder()
        transport.setHandler { request, body, _, _ in
            await bodies.record(body)
            let successBody = request.method == .delete
                ? #"{"data":{"deactivated":true}}"#
                : #"{"data":{"id":"1","platform":"ios","isActive":true}}"#
            return pushTokenJSONResponse(status: 200, body: successBody)
        }
        let manager = PushDeviceTokenManager(
            apiClient: makePushTokenClient(transport: transport),
            appStateStorage: storage
        )

        // Upload first so a device token is persisted for deactivation to send.
        await manager.uploadDeviceToken(Data([0x01, 0x23]))
        await manager.deactivateCurrentDeviceToken()

        let deleteRequest = try #require(
            transport.capturedRequests.first(where: { $0.method == .delete })
        )
        #expect(deleteRequest.operationID == "deleteMePushToken")
        #expect(deleteRequest.path == "/api/v1/me/push-tokens")
        let json = try #require(await bodies.lastJSON())
        #expect(json["token"] as? String == "0123")
        #expect(json["platform"] as? String == "ios")
    }

    @Test("push toggle emits push_settings_toggle_changed for both enable and disable")
    func pushToggleEmitsSettingsToggleChanged() async throws {
        let storage = makeStorage(name: "toggle-changed")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let analytics = RecordingPushAnalyticsManager()
        let statusProvider = SingleStatusPushAuthorizationStatusProvider(status: .authorized)
        let requester = RecordingPushAuthorizationRequester(result: true)
        let pushTokenManager = RecordingPushDeviceTokenManager()
        let model = SettingsNotificationPreferenceModel(
            store: store,
            pushTokenManager: pushTokenManager,
            pushAuthorizationStatusProvider: statusProvider,
            pushAuthorizationRequester: requester,
            analytics: analytics
        )

        model.setFavoriteComedianPushAlertsEnabled(true)
        try await waitUntil { await pushTokenManager.registerCalls == 1 }
        model.setFavoriteComedianPushAlertsEnabled(false)
        try await waitUntil { await pushTokenManager.deactivateCalls == 1 }

        let toggleEvents = analytics.events.filter { $0.name == PushAnalyticsEvents.settingsToggleChanged }
        #expect(toggleEvents.count == 2)
        #expect(toggleEvents[0].bool(PushAnalyticsEvents.Param.enabled) == true)
        #expect(toggleEvents[0].bool(PushAnalyticsEvents.Param.fromDeniedState) == false)
        #expect(toggleEvents[1].bool(PushAnalyticsEvents.Param.enabled) == false)
        #expect(toggleEvents[1].bool(PushAnalyticsEvents.Param.fromDeniedState) == false)
    }

    @Test("push toggle emits push_os_prompt_result with trigger=settings_toggle after notDetermined OS prompt")
    func pushToggleEmitsOSPromptResultOnNotDetermined() async throws {
        let storage = makeStorage(name: "os-prompt-settings")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let analytics = RecordingPushAnalyticsManager()
        let statusProvider = SingleStatusPushAuthorizationStatusProvider(status: .notDetermined)
        let requester = RecordingPushAuthorizationRequester(result: true)
        let pushTokenManager = RecordingPushDeviceTokenManager()
        let model = SettingsNotificationPreferenceModel(
            store: store,
            pushTokenManager: pushTokenManager,
            pushAuthorizationStatusProvider: statusProvider,
            pushAuthorizationRequester: requester,
            analytics: analytics
        )

        model.setFavoriteComedianPushAlertsEnabled(true)
        try await waitUntil { await requester.requestCount == 1 }
        try await waitUntil { analytics.events.contains { $0.name == PushAnalyticsEvents.osPromptResult } }

        let osResult = analytics.events.filter { $0.name == PushAnalyticsEvents.osPromptResult }
        #expect(osResult.count == 1)
        #expect(osResult.first?.bool(PushAnalyticsEvents.Param.granted) == true)
        #expect(osResult.first?.string(PushAnalyticsEvents.Param.trigger) == PushAnalyticsEvents.Trigger.settingsToggle.rawValue)
    }

    @Test("push toggle does NOT emit push_os_prompt_result when status is already authorized")
    func pushToggleAuthorizedDoesNotEmitOSPromptResult() async throws {
        let storage = makeStorage(name: "os-prompt-authorized")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let analytics = RecordingPushAnalyticsManager()
        let statusProvider = SingleStatusPushAuthorizationStatusProvider(status: .authorized)
        let requester = RecordingPushAuthorizationRequester(result: true)
        let pushTokenManager = RecordingPushDeviceTokenManager()
        let model = SettingsNotificationPreferenceModel(
            store: store,
            pushTokenManager: pushTokenManager,
            pushAuthorizationStatusProvider: statusProvider,
            pushAuthorizationRequester: requester,
            analytics: analytics
        )

        model.setFavoriteComedianPushAlertsEnabled(true)
        try await waitUntil { await pushTokenManager.registerCalls == 1 }

        #expect(!analytics.events.contains(where: { $0.name == PushAnalyticsEvents.osPromptResult }))
    }

    @Test("settings_toggle_changed includes from_denied_state=true after the denied alert was shown")
    func settingsToggleChangedReportsFromDeniedStateAfterAlert() async throws {
        let storage = makeStorage(name: "from-denied-state")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let analytics = RecordingPushAnalyticsManager()
        // Status sequence: first toggle attempt sees .denied (surfaces alert);
        // second attempt sees .authorized (user opened Settings, enabled push,
        // came back, and re-tapped the toggle) — exactly the recovery flow
        // from_denied_state is meant to measure.
        let statusProvider = SequencedPushAuthorizationStatusProvider(sequence: [.denied, .authorized])
        let requester = RecordingPushAuthorizationRequester(result: true)
        let pushTokenManager = RecordingPushDeviceTokenManager()
        let model = SettingsNotificationPreferenceModel(
            store: store,
            pushTokenManager: pushTokenManager,
            pushAuthorizationStatusProvider: statusProvider,
            pushAuthorizationRequester: requester,
            analytics: analytics
        )

        model.setFavoriteComedianPushAlertsEnabled(true)
        try await waitUntil { model.isPushDeniedAlertPresented }
        model.setFavoriteComedianPushAlertsEnabled(true)
        try await waitUntil { await pushTokenManager.registerCalls == 1 }

        let toggleEvents = analytics.events.filter { $0.name == PushAnalyticsEvents.settingsToggleChanged }
        #expect(toggleEvents.count == 2)
        #expect(toggleEvents[0].bool(PushAnalyticsEvents.Param.fromDeniedState) == false)
        #expect(toggleEvents[1].bool(PushAnalyticsEvents.Param.fromDeniedState) == true)
    }

    @Test("settings model replaces both server-backed channels from authenticated user")
    func settingsModelReplacesBothServerBackedChannels() {
        let storage = makeStorage(name: "server-backed")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let model = SettingsNotificationPreferenceModel(store: store)

        model.replaceServerBackedPreferences(
            from: AuthenticatedUser(
                userId: "test-user-id",
                displayName: "Ada Lovelace",
                email: "ada@example.com",
                avatarURL: nil,
                emailShowNotifications: true,
                pushShowNotifications: true
            )
        )

        #expect(model.preferences.favoriteComedianEmailAlertsEnabled)
        #expect(model.preferences.favoriteComedianPushAlertsEnabled)
    }

    private func makeStorage(name: String) -> AppStateStorage {
        let suiteName = "NotificationPreferenceStoreTests.\(name).\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return AppStateStorage(userDefaults: defaults)
    }

    private func waitUntil(
        timeout: TimeInterval = 1,
        condition: @escaping () async -> Bool
    ) async throws {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if await condition() {
                return
            }
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        Issue.record("Timed out waiting for notification preference sync")
    }
}

private actor RecordingNotificationPreferenceSync: NotificationPreferenceSyncing {
    struct Call: Equatable {
        let enabled: Bool
        let channel: NotificationPreferenceChannel
    }

    private(set) var calls: [Call] = []

    func setFavoriteComedianAlertsEnabled(
        _ enabled: Bool,
        channel: NotificationPreferenceChannel
    ) async throws {
        calls.append(Call(enabled: enabled, channel: channel))
    }
}

@MainActor
private func makePushTokenClient(transport: any ClientTransport) -> Client {
    Client(
        serverURL: URL(string: "https://test.example.com")!,
        transport: transport,
        middlewares: [APIVersionPathMiddleware()]
    )
}

private func pushTokenJSONResponse(status: Int, body: String) -> (HTTPResponse, HTTPBody?) {
    var response = HTTPResponse(status: .init(code: status))
    response.headerFields[.contentType] = "application/json"
    return (response, HTTPBody(body))
}

/// Collects request bodies from the stub transport so the push-token tests can
/// assert on the JSON payload the generated client serialized.
private actor PushTokenBodyRecorder {
    private var lastBody: Data?

    func record(_ body: HTTPBody?) async {
        guard let body else { return }
        lastBody = try? await Data(collecting: body, upTo: 1024)
    }

    func lastJSON() -> [String: Any]? {
        guard let lastBody else { return nil }
        return (try? JSONSerialization.jsonObject(with: lastBody)) as? [String: Any]
    }
}

private actor RecordingPushDeviceTokenManager: PushDeviceTokenManaging {
    private(set) var registerCalls = 0
    private(set) var deactivateCalls = 0

    func registerForRemoteNotifications() async {
        registerCalls += 1
    }

    func uploadDeviceToken(_ deviceToken: Data) async {}

    func deactivateCurrentDeviceToken() async {
        deactivateCalls += 1
    }
}

@MainActor
private final class RecordingSystemSettingsOpener: SystemSettingsOpening {
    private(set) var openCount = 0

    func openAppSystemSettings() {
        openCount += 1
    }
}
