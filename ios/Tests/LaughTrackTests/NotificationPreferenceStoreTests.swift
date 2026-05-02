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
