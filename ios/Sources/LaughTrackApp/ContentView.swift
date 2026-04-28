import SwiftUI
import LaughTrackBridge
import LaughTrackCore
import LaughTrackAPIClient

enum LaughTrackViewTestID {
    static let homeScreen = "laughtrack.home.screen"
    static let searchTabScreen = "laughtrack.search-tab.screen"
    static let libraryTabScreen = "laughtrack.library-tab.screen"
    static let profileTabScreen = "laughtrack.profile-tab.screen"
    static let homeSettingsButton = "laughtrack.home.settings-button"
    static let homeShowsSearchButton = "laughtrack.home.shows-search-button"
    static let homeClubsSearchButton = "laughtrack.home.clubs-search-button"
    static let homeComediansSearchButton = "laughtrack.home.comedians-search-button"
    static let homeTrendingComediansRail = "laughtrack.home.trending-comedians-rail"
    static let settingsScreen = "laughtrack.settings.screen"
    static let showsSearchScreen = "laughtrack.shows-search.screen"
    static let clubsSearchScreen = "laughtrack.clubs-search.screen"
    static let comediansSearchScreen = "laughtrack.comedians-search.screen"
    static let showDetailScreen = "laughtrack.show-detail.screen"
    static let comedianDetailScreen = "laughtrack.comedian-detail.screen"
    static let clubDetailScreen = "laughtrack.club-detail.screen"
    static let settingsNearbyEmptyState = "laughtrack.settings.nearby.empty-state"
    static let settingsNearbySavedState = "laughtrack.settings.nearby.saved-state"
    static let settingsZipField = "laughtrack.settings.zip-field"
    static let settingsDistancePicker = "laughtrack.settings.distance-picker"
    static let settingsSaveButton = "laughtrack.settings.save-button"
    static let settingsClearButton = "laughtrack.settings.clear-button"
    static let libraryFavoritesSection = "laughtrack.library.favorites-section"

    static func showsSearchResultButton(_ id: Int) -> String {
        "laughtrack.shows-search.result-\(id)"
    }

    static func comediansSearchResultButton(_ id: Int) -> String {
        "laughtrack.comedians-search.result-\(id)"
    }

    static func homeTrendingComedianButton(_ id: Int) -> String {
        "laughtrack.home.trending-comedian-\(id)"
    }

    static func clubsSearchResultButton(_ id: Int) -> String {
        "laughtrack.clubs-search.result-\(id)"
    }
}

struct ContentView: View {
    let apiClient: Client

    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var loginModalPresenter: LoginModalPresenter
    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @StateObject private var favorites = ComedianFavoriteStore()

    var body: some View {
        Group {
            switch authManager.state {
            case .restoring:
                AuthLoadingView(message: "Restoring your LaughTrack session…")
            case .signingIn(let provider):
                AuthLoadingView(message: "Finishing \(provider.displayName) sign-in…")
            case .signedOut(let message):
                appShell(signedOutMessage: message)
            case .authenticated:
                appShell(signedOutMessage: nil)
            }
        }
        .tint(theme.colors.primary)
        .task {
            await authManager.restoreSessionIfNeeded()
        }
        .onReceive(authManager.$state) { state in
            guard case .signedOut(let message) = state,
                  message?.localizedCaseInsensitiveContains("session expired") == true
            else { return }

            loginModalPresenter.present()
        }
        .sheet(isPresented: $loginModalPresenter.isPresented) {
            LaughTrackLoginModalView()
        }
    }

    @ViewBuilder
    private func appShell(signedOutMessage: String?) -> some View {
        CoordinatedNavigationStack(coordinator: coordinator) { route in
            switch route {
            case .home:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .home
                )
            case .search:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .search
                )
            case .library:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .library
                )
            case .profile:
                AppShellView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    favorites: favorites,
                    initialTab: .profile
                )
            case .settings:
                SettingsView(
                    signedOutMessage: signedOutMessage,
                    nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self)
                )
            case .showDetail(let id):
                ShowDetailView(showID: id, apiClient: apiClient)
            case .comedianDetail(let id):
                ComedianDetailView(comedianID: id, apiClient: apiClient)
            case .clubDetail(let id):
                ClubDetailView(clubID: id, apiClient: apiClient)
            }
        } root: {
            AppShellView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                favorites: favorites
            )
        }
        .environmentObject(favorites)
    }
}
