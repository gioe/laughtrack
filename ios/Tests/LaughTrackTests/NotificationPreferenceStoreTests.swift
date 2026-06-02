import Foundation
import Testing
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
        let statusProvider = MockPushAuthorizationStatusProvider(status: .authorized)
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
        let statusProvider = MockPushAuthorizationStatusProvider(status: .notDetermined)
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
        let statusProvider = MockPushAuthorizationStatusProvider(status: .denied)
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

    @Test("push token manager uploads refreshed APNs tokens with bearer auth")
    func pushTokenManagerUploadsDeviceToken() async throws {
        let storage = makeStorage(name: "push-upload")
        let secureStorage = InMemorySecureStorage()
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        try tokenManager.storeTokens(
            accessToken: "access-token",
            refreshToken: "refresh-token"
        )
        let recorder = PushTokenRequestRecorder()
        let manager = PushDeviceTokenManager(
            baseURL: URL(string: "https://example.com")!,
            tokenManager: tokenManager,
            appStateStorage: storage,
            urlSession: StubURLProtocol.makeSession { request in
                recorder.record(request)
                return Self.jsonResponse(for: request, body: #"{"data":{"id":"1"}}"#)
            }
        )

        await manager.uploadDeviceToken(Data([0xAB, 0xCD, 0xEF]))

        let request = try #require(recorder.lastRequest)
        #expect(request.httpMethod == "POST")
        #expect(request.url?.path == "/api/v1/me/push-tokens")
        #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer access-token")
        let body = try #require(requestBodyData(from: request))
        let json = try #require(JSONSerialization.jsonObject(with: body) as? [String: String])
        #expect(json["token"] == "abcdef")
        #expect(json["platform"] == "ios")
    }

    @Test("push token manager deactivates the current uploaded token")
    func pushTokenManagerDeactivatesCurrentDeviceToken() async throws {
        let storage = makeStorage(name: "push-deactivate")
        let secureStorage = InMemorySecureStorage()
        let tokenManager = AuthTokenManager(secureStorage: secureStorage)
        try tokenManager.storeTokens(
            accessToken: "access-token",
            refreshToken: "refresh-token"
        )
        let recorder = PushTokenRequestRecorder()
        let manager = PushDeviceTokenManager(
            baseURL: URL(string: "https://example.com")!,
            tokenManager: tokenManager,
            appStateStorage: storage,
            urlSession: StubURLProtocol.makeSession { request in
                recorder.record(request)
                return Self.jsonResponse(for: request, body: #"{"data":{"deactivated":true}}"#)
            }
        )

        await manager.uploadDeviceToken(Data([0x01, 0x23]))
        await manager.deactivateCurrentDeviceToken()

        let request = try #require(recorder.lastRequest)
        #expect(request.httpMethod == "DELETE")
        #expect(request.url?.path == "/api/v1/me/push-tokens")
        let body = try #require(requestBodyData(from: request))
        let json = try #require(JSONSerialization.jsonObject(with: body) as? [String: String])
        #expect(json["token"] == "0123")
        #expect(json["platform"] == "ios")
    }

    @Test("push toggle emits push_settings_toggle_changed for both enable and disable")
    func pushToggleEmitsSettingsToggleChanged() async throws {
        let storage = makeStorage(name: "toggle-changed")
        let store = NotificationPreferenceStore(appStateStorage: storage)
        let analytics = RecordingAnalyticsManager()
        let statusProvider = MockPushAuthorizationStatusProvider(status: .authorized)
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
        let analytics = RecordingAnalyticsManager()
        let statusProvider = MockPushAuthorizationStatusProvider(status: .notDetermined)
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
        let analytics = RecordingAnalyticsManager()
        let statusProvider = MockPushAuthorizationStatusProvider(status: .authorized)
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
        let analytics = RecordingAnalyticsManager()
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

    private func requestBodyData(from request: URLRequest) -> Data? {
        if let httpBody = request.httpBody {
            return httpBody
        }
        guard let stream = request.httpBodyStream else {
            return nil
        }

        stream.open()
        defer { stream.close() }

        var data = Data()
        var buffer = [UInt8](repeating: 0, count: 1024)
        while stream.hasBytesAvailable {
            let count = stream.read(&buffer, maxLength: buffer.count)
            if count <= 0 {
                break
            }
            data.append(buffer, count: count)
        }
        return data
    }

    nonisolated private static func jsonResponse(for request: URLRequest, body: String) -> (HTTPURLResponse, Data) {
        let response = HTTPURLResponse(
            url: request.url ?? URL(string: "https://example.com")!,
            statusCode: 200,
            httpVersion: nil,
            headerFields: ["Content-Type": "application/json"]
        )!
        return (response, Data(body.utf8))
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

private final class PushTokenRequestRecorder: @unchecked Sendable {
    private let lock = NSLock()
    private var request: URLRequest?

    var lastRequest: URLRequest? {
        lock.withLock { request }
    }

    func record(_ request: URLRequest) {
        lock.withLock {
            self.request = request
        }
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

private struct MockPushAuthorizationStatusProvider: PushAuthorizationStatusProviding {
    let status: PushAuthorizationStatus

    func currentAuthorizationStatus() async -> PushAuthorizationStatus {
        status
    }
}

private actor SequencedPushAuthorizationStatusProvider: PushAuthorizationStatusProviding {
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
