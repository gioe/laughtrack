import Foundation
import LaughTrackAPIClient
import LaughTrackCore
#if canImport(UserNotifications)
import UserNotifications
#endif

protocol OnboardingPushPermissionRequesting: Sendable {
    func requestAuthorization() async -> Bool
}

struct SystemOnboardingPushPermissionRequester: OnboardingPushPermissionRequesting {
    func requestAuthorization() async -> Bool {
        #if canImport(UserNotifications)
        do {
            return try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
        #else
        return false
        #endif
    }
}

@MainActor
final class ComedianOnboardingModel: ObservableObject {
    enum Phase: Equatable {
        case idle
        case loading
        case loaded
        case saving
        case failure(String)
    }

    static let defaultPageSize = 12

    @Published private(set) var comedians: [Components.Schemas.ComedianSearchItem] = []
    @Published private(set) var phase: Phase = .idle
    @Published var searchText = ""
    @Published var emailAlertsEnabled = true
    @Published var pushAlertsEnabled = true

    let suggestedFavoriteTarget = 3
    private let pushPermissionRequester: any OnboardingPushPermissionRequesting

    init(pushPermissionRequester: any OnboardingPushPermissionRequesting = SystemOnboardingPushPermissionRequester()) {
        self.pushPermissionRequester = pushPermissionRequester
    }

    var favoriteCount: Int {
        comedians.filter { $0.isFavorite == true }.count
    }

    var canContinue: Bool {
        phase != .saving
    }

    func loadInitialComedians(
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async {
        await load(query: "", apiClient: apiClient, favorites: favorites)
    }

    func search(
        _ query: String,
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async {
        searchText = query
        await load(query: query, apiClient: apiClient, favorites: favorites)
    }

    func toggleFavorite(
        uuid: String,
        apiClient: Client,
        favorites: ComedianFavoriteStore,
        authManager: AuthManager
    ) async {
        guard let index = comedians.firstIndex(where: { $0.uuid == uuid }) else { return }
        let currentValue = favorites.value(for: uuid, fallback: comedians[index].isFavorite)
        let result = await favorites.toggle(
            uuid: uuid,
            currentValue: currentValue,
            apiClient: apiClient,
            authManager: authManager
        )

        switch result {
        case .updated(let isFavorite):
            comedians[index].isFavorite = isFavorite
        case .signInRequired(let message), .failure(let message):
            phase = .failure(message)
        }
    }

    func setNotificationPreferences(
        emailEnabled: Bool,
        pushEnabled: Bool,
        store: NotificationPreferenceStore,
        syncClient: (any NotificationPreferenceSyncing)? = nil
    ) async {
        let pushGranted = pushEnabled ? await pushPermissionRequester.requestAuthorization() : false
        store.setFavoriteComedianEmailAlertsEnabled(emailEnabled)
        store.setFavoriteComedianPushAlertsEnabled(pushGranted)

        if let syncClient {
            try? await syncClient.setFavoriteComedianAlertsEnabled(emailEnabled, channel: .email)
            try? await syncClient.setFavoriteComedianAlertsEnabled(pushGranted, channel: .push)
        }
    }

    func complete(
        apiClient: Client,
        authManager: AuthManager
    ) async {
        await markServerOnboardingComplete(apiClient: apiClient, authManager: authManager)
    }

    func skip(
        apiClient: Client,
        authManager: AuthManager
    ) async {
        await markServerOnboardingComplete(apiClient: apiClient, authManager: authManager)
    }

    private func load(
        query: String,
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async {
        phase = .loading
        do {
            let output = try await apiClient.searchComedians(
                query: .init(
                    comedian: query.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty,
                    sort: PrimitiveSortOption.mostPopular.rawValue,
                    page: 0,
                    size: Self.defaultPageSize
                ),
                headers: .init(xTimezone: TimeZone.current.identifier)
            )

            guard case .ok(let ok) = output else {
                phase = .failure("LaughTrack could not load comedians right now.")
                return
            }

            comedians = try ok.body.json.data.map { comedian in
                favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
                var item = comedian
                item.isFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)
                return item
            }
            phase = .loaded
        } catch {
            phase = .failure("LaughTrack could not reach the comedians service. Please try again.")
        }
    }

    private func markServerOnboardingComplete(
        apiClient: Client,
        authManager: AuthManager
    ) async {
        phase = .saving
        do {
            let output = try await apiClient.updateMe(
                body: .json(.init(comedianOnboardingCompleted: true))
            )
            guard case .ok = output else {
                phase = .failure("LaughTrack could not save onboarding. Please try again.")
                return
            }

            authManager.markComedianOnboardingCompleted()
            await authManager.refreshCurrentUser()
            phase = .loaded
        } catch {
            phase = .failure("LaughTrack could not save onboarding. Please try again.")
        }
    }
}
