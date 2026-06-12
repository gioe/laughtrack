import Foundation
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

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

    /// How many fresh suggestion draws to attempt before concluding the
    /// eligible pool has been dealt out. Each draw is an independent
    /// weighted-random sample, so near exhaustion a single all-duplicate
    /// batch is not yet proof there's nobody left.
    static let maxLoadMoreAttempts = 3

    @Published private(set) var comedians: [Components.Schemas.ComedianSearchItem] = []
    @Published private(set) var phase: Phase = .idle
    @Published private(set) var isLoadingMoreSuggestions = false
    @Published private(set) var suggestionsExhausted = false

    /// Bumped whenever `comedians` is wholesale replaced (fresh deal or
    /// search) so an in-flight load-more started against the previous list
    /// aborts instead of appending into the new one.
    private var listGeneration = 0
    @Published var searchText = ""
    @Published var emailAlertsEnabled = true
    @Published var pushAlertsEnabled = true
    @Published var isPushDeniedAlertPresented: Bool = false

    let suggestedFavoriteTarget = 3
    private let pushPermissionRequester: any PushAuthorizationRequesting
    private let pushAuthorizationStatusProvider: any PushAuthorizationStatusProviding
    private let systemSettingsOpener: any SystemSettingsOpening
    private let pushTokenManager: (any PushDeviceTokenManaging)?
    private let analytics: (any AnalyticsManagerProtocol)?

    init(
        pushPermissionRequester: (any PushAuthorizationRequesting)? = nil,
        pushAuthorizationStatusProvider: (any PushAuthorizationStatusProviding)? = nil,
        systemSettingsOpener: (any SystemSettingsOpening)? = nil,
        pushTokenManager: (any PushDeviceTokenManaging)? = nil,
        analytics: (any AnalyticsManagerProtocol)? = nil
    ) {
        self.pushPermissionRequester = pushPermissionRequester ?? SystemPushAuthorizationRequester()
        self.pushAuthorizationStatusProvider = pushAuthorizationStatusProvider
            ?? SystemPushAuthorizationStatusProvider()
        self.systemSettingsOpener = systemSettingsOpener ?? SystemSettingsOpener()
        self.pushTokenManager = pushTokenManager
        self.analytics = analytics
    }

    func openSystemSettings() {
        systemSettingsOpener.openAppSystemSettings()
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
        await loadSuggestions(apiClient: apiClient, favorites: favorites)
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
        let pushGranted = pushEnabled ? await resolvePushPermission() : false
        store.setFavoriteComedianEmailAlertsEnabled(emailEnabled)
        store.setFavoriteComedianPushAlertsEnabled(pushGranted)

        if let syncClient {
            try? await syncClient.setFavoriteComedianAlertsEnabled(emailEnabled, channel: .email)
            try? await syncClient.setFavoriteComedianAlertsEnabled(pushGranted, channel: .push)
        }
        if pushGranted {
            await pushTokenManager?.registerForRemoteNotifications()
        }
    }

    private func resolvePushPermission() async -> Bool {
        let status = await pushAuthorizationStatusProvider.currentAuthorizationStatus()
        switch status {
        case .authorized:
            return true
        case .notDetermined:
            let granted = await pushPermissionRequester.requestAuthorization()
            analytics?.track(
                PushAnalyticsEvents.osPromptResult,
                parameters: [
                    PushAnalyticsEvents.Param.granted: granted,
                    PushAnalyticsEvents.Param.trigger: PushAnalyticsEvents.Trigger.onboarding.rawValue
                ]
            )
            return granted
        case .denied:
            isPushDeniedAlertPresented = true
            return false
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

    // Initial onboarding load: a fresh popularity-weighted random sample so the
    // favorite-a-comedian grid varies between sessions instead of always showing
    // the same fixed top-N that a deterministic popularity sort would return.
    private func loadSuggestions(
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async {
        listGeneration += 1
        suggestionsExhausted = false
        phase = .loading
        do {
            let output = try await apiClient.getComedianSuggestions()

            guard case .ok(let ok) = output else {
                phase = .failure("LaughTrack could not load comedians right now.")
                return
            }

            comedians = try ok.body.json.data.map { resolveFavorite($0, favorites: favorites) }
            phase = .loaded
        } catch {
            phase = .failure("LaughTrack could not reach the comedians service. Please try again.")
        }
    }

    // The suggestions endpoint redraws its weighted-random sample on every
    // call, so the swipe deck refills by drawing again and appending only
    // comedians not already dealt. Exhaustion is declared only after
    // `maxLoadMoreAttempts` consecutive draws add nothing new (a failed draw
    // counts too, so an empty deck never waits forever — "Deal them again"
    // resets the flag via a fresh load).
    func loadMoreSuggestions(
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async {
        guard !isLoadingMoreSuggestions, !suggestionsExhausted, phase == .loaded else { return }
        let generation = listGeneration
        isLoadingMoreSuggestions = true
        defer { isLoadingMoreSuggestions = false }

        for _ in 0..<Self.maxLoadMoreAttempts {
            guard
                let output = try? await apiClient.getComedianSuggestions(),
                case .ok(let ok) = output,
                let batch = try? ok.body.json.data
            else { break }

            guard generation == listGeneration else { return }

            let dealt = Set(comedians.map(\.uuid))
            let fresh = batch.filter { !dealt.contains($0.uuid) }
            guard !fresh.isEmpty else { continue }

            comedians.append(contentsOf: fresh.map { resolveFavorite($0, favorites: favorites) })
            return
        }

        guard generation == listGeneration else { return }
        suggestionsExhausted = true
    }

    // Explicit search box query: a deterministic popularity sort is the right
    // behavior here, so this path stays on searchComedians.
    private func load(
        query: String,
        apiClient: Client,
        favorites: ComedianFavoriteStore
    ) async {
        listGeneration += 1
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

            comedians = try ok.body.json.data.map { resolveFavorite($0, favorites: favorites) }
            phase = .loaded
        } catch {
            phase = .failure("LaughTrack could not reach the comedians service. Please try again.")
        }
    }

    // Seed the favorite store from the server-reported flag, then echo back the
    // store's resolved value so locally-toggled favorites win over stale server data.
    private func resolveFavorite(
        _ comedian: Components.Schemas.ComedianSearchItem,
        favorites: ComedianFavoriteStore
    ) -> Components.Schemas.ComedianSearchItem {
        favorites.seed(uuid: comedian.uuid, value: comedian.isFavorite)
        var item = comedian
        item.isFavorite = favorites.value(for: comedian.uuid, fallback: comedian.isFavorite)
        return item
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
