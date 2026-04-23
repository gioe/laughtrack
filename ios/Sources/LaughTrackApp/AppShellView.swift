import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

@MainActor
struct AppShellView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let favorites: ComedianFavoriteStore
    @ObservedObject var nearbyPreferenceStore: NearbyPreferenceStore

    @Environment(\.appTheme) private var theme
    @State private var selectedTab: AppTab

    init(
        apiClient: Client,
        signedOutMessage: String? = nil,
        favorites: ComedianFavoriteStore,
        nearbyPreferenceStore: NearbyPreferenceStore,
        initialTab: AppTab = .home
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.favorites = favorites
        self._nearbyPreferenceStore = ObservedObject(wrappedValue: nearbyPreferenceStore)
        _selectedTab = State(initialValue: initialTab)
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                nearbyPreferenceStore: nearbyPreferenceStore
            )
                .tabItem { Label("Home", systemImage: "house.fill") }
                .tag(AppTab.home)

            SearchRootView(
                apiClient: apiClient,
                nearbyPreferenceStore: nearbyPreferenceStore
            )
                .tabItem { Label("Search", systemImage: "magnifyingglass") }
                .tag(AppTab.search)

            AppShellPlaceholderView(
                title: "Activity",
                accessibilityID: LaughTrackViewTestID.activityTabScreen
            )
                .tabItem { Label("Activity", systemImage: "bell.fill") }
                .tag(AppTab.activity)

            ProfileView(
                apiClient: apiClient,
                signedOutMessage: signedOutMessage,
                nearbyPreferenceStore: nearbyPreferenceStore
            )
                .tabItem { Label("Profile", systemImage: "person.crop.circle") }
                .tag(AppTab.profile)
        }
        .environmentObject(favorites)
        .tint(theme.colors.primary)
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
