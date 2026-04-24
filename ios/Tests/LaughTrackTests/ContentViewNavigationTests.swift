#if canImport(UIKit)
import SwiftUI
import Testing
import LaughTrackBridge
import LaughTrackCore
@testable import LaughTrackApp

@Suite("ContentView navigation")
@MainActor
struct ContentViewNavigationTests {
    @Test("content view routes authenticated users into the app shell")
    func contentViewRendersShell() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "content-shell")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "content-view"))
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.homeScreen)
        try host.requireText("Search")
        try host.requireText("Activity")
        try host.requireText("Profile")
    }

    @Test("Settings entry point from home pushes the expected navigation intent")
    func homeSettingsButtonPushesSettingsRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-view")
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "home")
        let host = HostedView(
            HomeView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                searchNavigationBridge: SearchNavigationBridge()
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.tapControl(withIdentifier: LaughTrackViewTestID.homeSettingsButton)

        #expect(coordinator.path.count == 1)
        #expect(coordinator.path.last == .settings)
    }

    @Test("ContentView switches between the home and settings routes")
    func contentViewSwitchesBetweenRoutes() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "content-view")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "content-view"))
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.homeScreen)

        coordinator.push(.settings)
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsScreen)
    }

    @Test("Home shows search entry seeds the search tab")
    func homeShowsSearchButtonSeedsSearchTab() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let searchBridge = SearchNavigationBridge()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-shows-search")
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "home-shows-search")
        let host = HostedView(
            HomeView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                searchNavigationBridge: searchBridge
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.tapControl(withIdentifier: LaughTrackViewTestID.homeShowsSearchButton)

        #expect(coordinator.path.isEmpty)
        #expect(searchBridge.request?.seed == .init(pivot: .shows, query: "", shortcut: "Near Me"))
    }

    @Test("home uses compact search entry copy instead of dedicated giant cards")
    func homeUsesCompactSearchEntryCopy() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-browse-redesign")
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "home-browse-redesign")
        let host = HostedView(
            HomeView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                searchNavigationBridge: SearchNavigationBridge()
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.requireText("Jump back into Search")
        try host.requireText("Open Search from a head start")
        try host.requireText("Shows")
        try host.requireText("Clubs")
        try host.requireText("Comedians")
    }

    @Test("Home clubs search entry seeds the search tab")
    func homeClubsSearchButtonSeedsSearchTab() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let searchBridge = SearchNavigationBridge()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-clubs-search")
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "home-clubs-search")
        let host = HostedView(
            HomeView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                searchNavigationBridge: searchBridge
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.tapControl(withIdentifier: LaughTrackViewTestID.homeClubsSearchButton)

        #expect(coordinator.path.isEmpty)
        #expect(searchBridge.request?.seed == .init(pivot: .clubs, query: "", shortcut: nil))
    }

    @Test("Home comedians search entry seeds the search tab")
    func homeComediansSearchButtonSeedsSearchTab() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let searchBridge = SearchNavigationBridge()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-comedians-search")
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "home-comedians-search")
        let host = HostedView(
            HomeView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                signedOutMessage: nil,
                searchNavigationBridge: searchBridge
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.tapControl(withIdentifier: LaughTrackViewTestID.homeComediansSearchButton)

        #expect(coordinator.path.isEmpty)
        #expect(searchBridge.request?.seed == .init(pivot: .comedians, query: "", shortcut: nil))
    }

    @Test("ContentView renders the show detail route")
    func contentViewShowsShowDetailRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "show-detail-route")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "content-view"))
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        coordinator.push(.showDetail(301))
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.showDetailScreen)
    }

    @Test("ContentView renders the comedian detail route")
    func contentViewShowsComedianDetailRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "comedian-detail-route")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "content-view"))
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        coordinator.push(.comedianDetail(101))
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.comedianDetailScreen)
    }

    @Test("ContentView renders the club detail route")
    func contentViewShowsClubDetailRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "club-detail-route")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "content-view"))
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        coordinator.push(.clubDetail(201))
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.clubDetailScreen)
    }

    @Test("ContentView routes the shared search route through the shell tab")
    func contentViewShowsSearchShellRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "search-shell-route")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "content-view"))
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        coordinator.push(.search)
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.searchTabScreen)
    }

    @Test("ContentView routes the activity route through the shell tab")
    func contentViewShowsActivityShellRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "activity-shell-route")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "content-view"))
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        coordinator.push(.activity)
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.activityTabScreen)
    }

    @Test("ContentView routes the profile route through the real profile surface")
    func contentViewShowsProfileShellRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "profile-shell-route")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "content-view"))
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        coordinator.push(.profile)
        host.render()

        try host.requireText("Nearby defaults")
        try host.requireView(withIdentifier: LaughTrackViewTestID.settingsFavoritesSection)
    }
}
#endif
