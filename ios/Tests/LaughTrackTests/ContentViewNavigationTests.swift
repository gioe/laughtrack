#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
@testable import LaughTrackApp

@Suite("ContentView navigation")
@MainActor
struct ContentViewNavigationTests {
    @Test("content view routes authenticated users into the app shell")
    func contentViewRendersShell() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "content-shell")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environmentObject(authManager)
        )

        try host.requireText("Search")
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

    @Test("Home shows search entry pushes the shared search route")
    func homeShowsSearchButtonPushesSearchRoute() async throws {
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
        #expect(coordinator.path.last == .search)
    }

    @Test("Home clubs search entry pushes the shared search route")
    func homeClubsSearchButtonPushesSearchRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-clubs-search")
        let host = HostedView(
            HomeView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyPreferenceStore: LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "home-clubs-search")
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.tapControl(withIdentifier: LaughTrackViewTestID.homeClubsSearchButton)

        #expect(coordinator.path.count == 1)
        #expect(coordinator.path.last == .search)
    }

    @Test("Home comedians search entry pushes the shared search route")
    func homeComediansSearchButtonPushesSearchRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-comedians-search")
        let host = HostedView(
            HomeView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                nearbyPreferenceStore: LaughTrackHostedViewTestSupport.makeNearbyPreferenceStore(name: "home-comedians-search")
            )
            .environment(\.appTheme, LaughTrackTheme())
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.tapControl(withIdentifier: LaughTrackViewTestID.homeComediansSearchButton)

        #expect(coordinator.path.count == 1)
        #expect(coordinator.path.last == .search)
    }
}
#endif
