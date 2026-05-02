import Combine
import Foundation
import LaughTrackBridge

public enum NotificationPreferenceChannel: String, Codable, Equatable, Sendable {
    case email
    case push
}

public protocol NotificationPreferenceSyncing: Sendable {
    func setFavoriteComedianAlertsEnabled(
        _ enabled: Bool,
        channel: NotificationPreferenceChannel
    ) async throws
}

public final class ProfileNotificationPreferenceSyncClient: NotificationPreferenceSyncing, @unchecked Sendable {
    private let baseURL: URL
    private let tokenManager: AuthTokenManager
    private let urlSession: URLSession

    public init(
        baseURL: URL = AppConfiguration.apiBaseURL,
        tokenManager: AuthTokenManager,
        urlSession: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.tokenManager = tokenManager
        self.urlSession = urlSession
    }

    public func setFavoriteComedianAlertsEnabled(
        _ enabled: Bool,
        channel: NotificationPreferenceChannel
    ) async throws {
        let accessToken = await MainActor.run { tokenManager.retrieveAccessToken() }
        guard let accessToken else {
            throw URLError(.userAuthenticationRequired)
        }

        var request = URLRequest(url: baseURL.appendingPathComponent("api/v1/me/notifications"))
        request.httpMethod = "PATCH"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try JSONSerialization.data(
            withJSONObject: [Self.payloadKey(for: channel): enabled],
            options: []
        )

        let (_, response) = try await urlSession.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode)
        else {
            throw URLError(.badServerResponse)
        }
    }

    private static func payloadKey(for channel: NotificationPreferenceChannel) -> String {
        switch channel {
        case .email:
            return "email_show_notifications"
        case .push:
            return "push_show_notifications"
        }
    }
}

public struct NotificationPreferences: Codable, Equatable {
    public var favoriteComedianEmailAlertsEnabled: Bool
    public var favoriteComedianPushAlertsEnabled: Bool

    public init(
        favoriteComedianEmailAlertsEnabled: Bool = false,
        favoriteComedianPushAlertsEnabled: Bool = false
    ) {
        self.favoriteComedianEmailAlertsEnabled = favoriteComedianEmailAlertsEnabled
        self.favoriteComedianPushAlertsEnabled = favoriteComedianPushAlertsEnabled
    }

    public init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let legacyFavoriteAlerts = try container.decodeIfPresent(
            Bool.self,
            forKey: .favoriteComedianAlertsEnabled
        )

        self.init(
            favoriteComedianEmailAlertsEnabled: try container.decodeIfPresent(
                Bool.self,
                forKey: .favoriteComedianEmailAlertsEnabled
            ) ?? legacyFavoriteAlerts ?? false,
            favoriteComedianPushAlertsEnabled: try container.decodeIfPresent(
                Bool.self,
                forKey: .favoriteComedianPushAlertsEnabled
            ) ?? false
        )
    }

    public func encode(to encoder: any Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(favoriteComedianEmailAlertsEnabled, forKey: .favoriteComedianEmailAlertsEnabled)
        try container.encode(favoriteComedianPushAlertsEnabled, forKey: .favoriteComedianPushAlertsEnabled)
    }

    public static let `default` = NotificationPreferences()

    public var hasEnabledChannel: Bool {
        favoriteComedianEmailAlertsEnabled || favoriteComedianPushAlertsEnabled
    }

    private enum CodingKeys: String, CodingKey {
        case favoriteComedianEmailAlertsEnabled
        case favoriteComedianPushAlertsEnabled
        case favoriteComedianAlertsEnabled
    }
}

@MainActor
public final class NotificationPreferenceStore: ObservableObject {
    @Published public private(set) var preferences: NotificationPreferences

    private let appStateStorage: AppStateStorageProtocol

    public convenience init() {
        self.init(appStateStorage: AppStateStorage())
    }

    public init(appStateStorage: AppStateStorageProtocol) {
        self.appStateStorage = appStateStorage
        self.preferences = appStateStorage.getValue(
            forKey: StorageKey.preferences,
            as: NotificationPreferences.self
        ) ?? .default
    }

    public func setFavoriteComedianEmailAlertsEnabled(_ enabled: Bool) {
        update { $0.favoriteComedianEmailAlertsEnabled = enabled }
    }

    public func setFavoriteComedianPushAlertsEnabled(_ enabled: Bool) {
        update { $0.favoriteComedianPushAlertsEnabled = enabled }
    }

    public func replaceServerBackedPreferences(
        favoriteComedianEmailAlertsEnabled: Bool,
        favoriteComedianPushAlertsEnabled: Bool
    ) {
        update { preferences in
            preferences.favoriteComedianEmailAlertsEnabled = favoriteComedianEmailAlertsEnabled
            preferences.favoriteComedianPushAlertsEnabled = favoriteComedianPushAlertsEnabled
        }
    }

    public func reset() {
        preferences = .default
        appStateStorage.removeValue(forKey: StorageKey.preferences)
    }

    private func update(_ mutate: (inout NotificationPreferences) -> Void) {
        var nextPreferences = preferences
        mutate(&nextPreferences)
        preferences = nextPreferences
        appStateStorage.setValue(nextPreferences, forKey: StorageKey.preferences)
    }

    private enum StorageKey {
        static let preferences = "laughtrack.notifications.preferences"
    }
}

@MainActor
public final class SettingsNotificationPreferenceModel: ObservableObject {
    @Published public private(set) var preferences: NotificationPreferences
    @Published public private(set) var syncMessage: String?

    private let store: NotificationPreferenceStore
    private let syncClient: (any NotificationPreferenceSyncing)?
    private var preferencesCancellable: AnyCancellable?

    public init(
        store: NotificationPreferenceStore,
        syncClient: (any NotificationPreferenceSyncing)? = nil
    ) {
        self.store = store
        self.syncClient = syncClient
        self.preferences = store.preferences
        preferencesCancellable = store.$preferences
            .sink { [weak self] preferences in
                self?.preferences = preferences
            }
    }

    public func setFavoriteComedianEmailAlertsEnabled(_ enabled: Bool) {
        store.setFavoriteComedianEmailAlertsEnabled(enabled)
        syncFavoriteComedianAlerts(enabled, channel: .email)
    }

    public func setFavoriteComedianPushAlertsEnabled(_ enabled: Bool) {
        store.setFavoriteComedianPushAlertsEnabled(enabled)
        syncFavoriteComedianAlerts(enabled, channel: .push)
    }

    public func replaceServerBackedPreferences(from user: AuthenticatedUser) {
        store.replaceServerBackedPreferences(
            favoriteComedianEmailAlertsEnabled: user.emailShowNotifications,
            favoriteComedianPushAlertsEnabled: user.pushShowNotifications
        )
        syncMessage = nil
    }

    private func syncFavoriteComedianAlerts(
        _ enabled: Bool,
        channel: NotificationPreferenceChannel
    ) {
        syncMessage = nil
        guard let syncClient else { return }

        Task { [weak self] in
            do {
                try await syncClient.setFavoriteComedianAlertsEnabled(enabled, channel: channel)
            } catch {
                self?.handleSyncFailure(enabled: enabled, channel: channel)
            }
        }
    }

    private func handleSyncFailure(enabled: Bool, channel: NotificationPreferenceChannel) {
        switch channel {
        case .email:
            store.setFavoriteComedianEmailAlertsEnabled(!enabled)
        case .push:
            store.setFavoriteComedianPushAlertsEnabled(!enabled)
        }
        syncMessage = "LaughTrack could not save that alert preference. Please try again."
    }
}
