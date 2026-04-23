#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
@testable import LaughTrackApp

@Suite("App shell")
@MainActor
struct AppShellViewTests {
    @Test("shell renders four top-level tabs")
    func shellRendersTabs() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "app-shell-tabs")
        let coordinator = NavigationCoordinator<AppRoute>()
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                nearbyPreferenceStore: LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "app-shell-tabs")
            )
                .environment(\.appTheme, LaughTrackTheme())
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.homeScreen)
        try host.requireText("Home")
        try host.requireText("Search")
        try host.requireText("Activity")
        try host.requireText("Profile")
    }

    @Test("shell can start on the search tab without losing tab chrome")
    func shellCanStartOnSearchTab() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "app-shell-search")
        let coordinator = NavigationCoordinator<AppRoute>()
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                nearbyPreferenceStore: LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "app-shell-search"),
                initialTab: .search
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.searchTabScreen)
        try host.requireText("Home")
        try host.requireText("Search")
    }
}
#endif
