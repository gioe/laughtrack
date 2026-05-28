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
