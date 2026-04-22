#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
@testable import LaughTrackApp

@Suite("ContentView navigation")
@MainActor
struct ContentViewNavigationTests {
    @Test("ContentView switches between the home and settings routes")
    func contentViewSwitchesBetweenRoutes() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "content-view")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.homeScreen)

        coordinator.push(.settings)
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsScreen)
    }

    @Test("Settings entry point from home pushes the expected navigation intent")
    func homeSettingsButtonPushesSettingsRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-view")
        let host = HostedView(
            HomeView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyPreferenceStore: LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "home")
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.tapControl(withIdentifier: LaughTrackViewTestID.homeSettingsButton)

        #expect(coordinator.path.count == 1)
    }

    @Test("Home shows search entry pushes the dedicated shows search route")
    func homeShowsSearchButtonPushesShowsSearchRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-shows-search")
        let host = HostedView(
            HomeView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyPreferenceStore: LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "home-shows-search")
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.tapControl(withIdentifier: LaughTrackViewTestID.homeShowsSearchButton)

        #expect(coordinator.path.count == 1)
        #expect(coordinator.path.last == .showsSearch)
    }

    @Test("ContentView renders the show detail route")
    func contentViewShowsShowDetailRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "show-detail-route")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        coordinator.push(.showDetail(301))
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.showDetailScreen)
    }

    @Test("ContentView renders the dedicated shows search route")
    func contentViewShowsDedicatedShowsSearchRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shows-search-route")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        coordinator.push(.showsSearch)
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.showsSearchScreen)
    }

}
#endif
