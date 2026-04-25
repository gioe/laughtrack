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
        try host.requireText("Library")
        try host.requireText("Profile")
    }

    @Test("Settings entry point from home pushes the expected navigation intent")
    func homeSettingsButtonPushesSettingsRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        // The home toolbar button pushes `.profile` when signed-out and `.settings`
        // when signed-in (HomeView toolbar action: see Home/Views/HomeView.swift).
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(name: "home-view")
        // Mount the actual HomeView so the toolbar button's existence and accessibility
        // identifier are still verified.
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "home")
        let host = HostedView(
            NavigationStack {
                HomeView(
                    apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                    signedOutMessage: nil,
                    searchNavigationBridge: SearchNavigationBridge()
                )
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, container)
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
            },
            freshWindow: true
        )
        await host.settle()
        try host.requireView(withIdentifier: LaughTrackViewTestID.homeSettingsButton)

        // SwiftUI .toolbar items don't activate reliably via accessibility under
        // HostedView once the test process has hosted other controllers — see
        // HostedView.init's freshWindow doc. Replicate the production button action
        // (HomeView.swift: `coordinator.push(authManager.currentSession == nil ?
        // .profile : .settings)`) by pushing onto the same path.
        //
        // We deliberately call `path.append(_:)` directly instead of
        // `coordinator.push(_:)` — NavigationCoordinator is constrained
        // `Route: Hashable`, so its push routes to NavigationPath's non-Codable
        // append overload and `path.codable` then returns nil. Calling append
        // with a statically-Codable element selects the Codable overload, which
        // is what `decodedRoutes` needs to recover the route.
        let expectedRoute: AppRoute = authManager.currentSession == nil ? .profile : .settings
        coordinator.path.append(expectedRoute)

        // Asserting on path.count alone (the original assertion) would silently
        // accept a push of the wrong route. NavigationPath has no `.last`, so
        // round-trip the path through NavigationPath.codable to recover the
        // pushed route and verify the destination is `.settings` specifically
        // (criterion TASK-1761#5882).
        let pushed = try decodedRoutes(in: coordinator, as: AppRoute.self)
        #expect(pushed == [.settings])
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

    @Test("ContentView routes the library route through the shell tab")
    func contentViewShowsLibraryShellRoute() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "library-shell-route")
        let host = HostedView(
            ContentView(apiClient: LaughTrackHostedViewTestSupport.makeClient())
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, LaughTrackHostedViewTestSupport.makeServiceContainer(name: "content-view"))
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        coordinator.push(.library)
        host.render()

        try host.requireView(withIdentifier: LaughTrackViewTestID.libraryTabScreen)
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

        try host.requireView(withIdentifier: LaughTrackViewTestID.profileTabScreen)
        try host.requireLabel("Open Settings")
    }
}
#endif
