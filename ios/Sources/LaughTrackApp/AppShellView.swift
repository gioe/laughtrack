import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct AppShellView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let favorites: ComedianFavoriteStore

    @Environment(\.appTheme) private var theme
    @Environment(\.serviceContainer) private var serviceContainer
    @EnvironmentObject private var coordinator: NavigationCoordinator<AppRoute>
    @State private var selectedTab: AppTab
    @StateObject private var searchNavigationBridge = SearchNavigationBridge()

    init(
        apiClient: Client,
        signedOutMessage: String? = nil,
        favorites: ComedianFavoriteStore,
        initialTab: AppTab = .home
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.favorites = favorites
        _selectedTab = State(initialValue: initialTab)
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                searchNavigationBridge: searchNavigationBridge
            )
                .tabItem { Label("Home", systemImage: "house.fill") }
                .tag(AppTab.home)

            SearchRootView(
                apiClient: apiClient,
                favorites: favorites,
                coordinator: coordinator,
                searchNavigationBridge: searchNavigationBridge,
                nearbyLocationController: serviceContainer.resolve(NearbyLocationController.self)
            )
                .tabItem { Label("Search", systemImage: "magnifyingglass") }
                .tag(AppTab.search)

            ActivityView()
                .tabItem { Label("Activity", systemImage: "bell.fill") }
                .tag(AppTab.activity)

            ProfileView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage
            )
                .tabItem { Label("Profile", systemImage: "person.crop.circle") }
                .tag(AppTab.profile)
        }
        .environmentObject(favorites)
        .tint(theme.colors.primary)
        .onReceive(searchNavigationBridge.$request.compactMap { $0 }) { _ in
            selectedTab = .search
        }
    }
}
