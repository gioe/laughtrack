import SwiftUI
import LaughTrackAPIClient
import LaughTrackBridge

struct AppShellView: View {
    let apiClient: Client

    @Environment(\.appTheme) private var theme
    @State private var selectedTab: AppTab = .home
    @StateObject private var homeCoordinator = NavigationCoordinator<AppRoute>()
    @StateObject private var searchCoordinator = NavigationCoordinator<AppRoute>()
    @StateObject private var activityCoordinator = NavigationCoordinator<AppRoute>()
    @StateObject private var profileCoordinator = NavigationCoordinator<AppRoute>()

    var body: some View {
        TabView(selection: $selectedTab) {
            Text("Home")
                .tabItem { Label("Home", systemImage: "house.fill") }
                .tag(AppTab.home)

            Text("Search")
                .tabItem { Label("Search", systemImage: "magnifyingglass") }
                .tag(AppTab.search)

            Text("Activity")
                .tabItem { Label("Activity", systemImage: "bell.fill") }
                .tag(AppTab.activity)

            Text("Profile")
                .tabItem { Label("Profile", systemImage: "person.crop.circle") }
                .tag(AppTab.profile)
        }
        .tint(theme.colors.primary)
    }
}
