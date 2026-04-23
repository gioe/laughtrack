import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct AppShellView: View {
    let apiClient: Client
    let signedOutMessage: String?

    @Environment(\.appTheme) private var theme
    @State private var selectedTab: AppTab
    @StateObject private var favorites: ComedianFavoriteStore
    @StateObject private var nearbyPreferenceStore: NearbyPreferenceStore
    @StateObject private var homeCoordinator = NavigationCoordinator<AppRoute>()
    @StateObject private var profileCoordinator = NavigationCoordinator<AppRoute>()

    init(
        apiClient: Client,
        signedOutMessage: String? = nil,
        favorites: ComedianFavoriteStore? = nil,
        nearbyPreferenceStore: NearbyPreferenceStore? = nil,
        initialTab: AppTab = .home
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        _favorites = StateObject(wrappedValue: favorites ?? ComedianFavoriteStore())
        _nearbyPreferenceStore = StateObject(
            wrappedValue: nearbyPreferenceStore ?? NearbyPreferenceStore()
        )
        _selectedTab = State(initialValue: initialTab)
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            CoordinatedNavigationStack(coordinator: homeCoordinator) { route in
                routeView(for: route, defaultTab: .home)
            } root: {
                HomeView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    nearbyPreferenceStore: nearbyPreferenceStore
                )
            }
                .tabItem { Label("Home", systemImage: "house.fill") }
                .tag(AppTab.home)

            AppShellPlaceholderView(
                title: "Search",
                accessibilityID: LaughTrackViewTestID.searchTabScreen
            )
                .tabItem { Label("Search", systemImage: "magnifyingglass") }
                .tag(AppTab.search)

            AppShellPlaceholderView(
                title: "Activity",
                accessibilityID: LaughTrackViewTestID.activityTabScreen
            )
                .tabItem { Label("Activity", systemImage: "bell.fill") }
                .tag(AppTab.activity)

            CoordinatedNavigationStack(coordinator: profileCoordinator) { route in
                routeView(for: route, defaultTab: .profile)
            } root: {
                ProfileView(
                    apiClient: apiClient,
                    signedOutMessage: signedOutMessage,
                    nearbyPreferenceStore: nearbyPreferenceStore
                )
            }
                .tabItem { Label("Profile", systemImage: "person.crop.circle") }
                .tag(AppTab.profile)
        }
        .environmentObject(favorites)
        .tint(theme.colors.primary)
    }

    @ViewBuilder
    private func routeView(for route: AppRoute, defaultTab: AppTab) -> some View {
        switch route {
        case .home:
            HomeView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                nearbyPreferenceStore: nearbyPreferenceStore
            )
        case .search:
            AppShellPlaceholderView(
                title: "Search",
                accessibilityID: LaughTrackViewTestID.searchTabScreen
            )
        case .activity:
            AppShellPlaceholderView(
                title: "Activity",
                accessibilityID: LaughTrackViewTestID.activityTabScreen
            )
        case .profile:
            ProfileView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                nearbyPreferenceStore: nearbyPreferenceStore
            )
        case .settings:
            SettingsView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                nearbyPreferenceStore: nearbyPreferenceStore
            )
        case .showsSearch:
            ShowsSearchScreen(
                apiClient: apiClient,
                nearbyPreferenceStore: nearbyPreferenceStore
            )
        case .clubsSearch:
            ClubsSearchScreen(apiClient: apiClient)
        case .comediansSearch:
            ComediansSearchScreen(apiClient: apiClient)
        case .showDetail(let id):
            ShowDetailView(showID: id, apiClient: apiClient)
        case .comedianDetail(let id):
            ComedianDetailView(comedianID: id, apiClient: apiClient)
        case .clubDetail(let id):
            ClubDetailView(clubID: id, apiClient: apiClient)
        }
    }
}

private struct AppShellPlaceholderView: View {
    let title: String
    let accessibilityID: String

    var body: some View {
        Text(title)
            .accessibilityIdentifier(accessibilityID)
    }
}
