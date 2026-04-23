import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge
import LaughTrackCore

struct AppShellView: View {
    let apiClient: Client
    let signedOutMessage: String?
    let nearbyPreferenceStore: NearbyPreferenceStore

    @Environment(\.appTheme) private var theme
    @State private var selectedTab: AppTab

    init(
        apiClient: Client,
        signedOutMessage: String? = nil,
        nearbyPreferenceStore: NearbyPreferenceStore,
        initialTab: AppTab = .home
    ) {
        self.apiClient = apiClient
        self.signedOutMessage = signedOutMessage
        self.nearbyPreferenceStore = nearbyPreferenceStore
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

            AppShellPlaceholderView(
                title: "Profile",
                accessibilityID: LaughTrackViewTestID.profileTabScreen
            )
                .tabItem { Label("Profile", systemImage: "person.crop.circle") }
                .tag(AppTab.profile)
        }
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
