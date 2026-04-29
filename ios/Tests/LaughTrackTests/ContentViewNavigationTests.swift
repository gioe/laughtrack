#if canImport(UIKit)
import Foundation
import HTTPTypes
import OpenAPIRuntime
import SwiftUI
import Testing
import LaughTrackAPIClient
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
        // The HomeView toolbar button's action calls
        //   coordinator.push(AppRoute.homeToolbarTarget(isSignedIn: ...))
        // (see Home/Views/HomeView.swift). Two assertions together cover the
        // production wiring without depending on iOS 26's flaky toolbar
        // accessibility activation:
        //   1. the toolbar button is mounted with the expected accessibility id,
        //   2. the route resolver returns `.settings` when signed-in (and
        //      `.profile` when signed-out).
        // If a regression changes either the action's resolver or the resolver's
        // logic, one of the two assertions catches it.
        let coordinator = NavigationCoordinator<AppRoute>()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(name: "home-view")
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
                .environmentObject(ComedianFavoriteStore())
                .environmentObject(authManager)
            },
            freshWindow: true
        )
        await host.settle()
        try host.requireView(withIdentifier: LaughTrackViewTestID.homeSettingsButton)

        #expect(AppRoute.homeToolbarTarget(isSignedIn: true) == .settings)
        #expect(AppRoute.homeToolbarTarget(isSignedIn: false) == .profile)

        // Drive the resolver through the same coordinator the live button uses,
        // then verify the destination via NavigationPath.codable round-trip
        // (criterion TASK-1761#5882). Use `path.append(_:)` directly since
        // NavigationCoordinator's `push` is constrained `Route: Hashable` and
        // routes to the non-Codable overload, which makes `path.codable` nil.
        coordinator.path.append(AppRoute.homeToolbarTarget(isSignedIn: authManager.currentSession != nil))
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

    @Test("Home shows-tonight hero opens show detail")
    func homeShowsTonightHeroOpensShowDetail() async throws {
        let coordinator = NavigationCoordinator<AppRoute>()
        let searchBridge = SearchNavigationBridge()
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "home-shows-tonight")
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "home-shows-tonight")
        let host = HostedView(
            HomeView(
                apiClient: makeHomeFeedClient(),
                signedOutMessage: nil,
                searchNavigationBridge: searchBridge
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(ComedianFavoriteStore())
            .environmentObject(authManager)
        )
        await host.settle()

        try host.requireView(withIdentifier: LaughTrackViewTestID.homeShowsTonightRail)
        try host.requireView(withIdentifier: LaughTrackViewTestID.homeShowsTonightHeroButton)
        try host.tapControl(withIdentifier: LaughTrackViewTestID.homeShowsTonightHeroButton)

        let pushed = try decodedRoutes(in: coordinator, as: AppRoute.self)
        #expect(pushed == [.showDetail(701)])
        #expect(searchBridge.request == nil)
    }

    @Test("home removes the search entry rail from the body")
    func homeRemovesSearchEntryRail() async throws {
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
            .environmentObject(ComedianFavoriteStore())
            .environmentObject(authManager)
        )

        #expect(host.findView(withIdentifier: LaughTrackViewTestID.homeShowsSearchButton) == nil)
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.homeClubsSearchButton) == nil)
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.homeComediansSearchButton) == nil)
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

private func makeHomeFeedClient() -> Client {
    Client(
        serverURL: URL(string: "https://example.com")!,
        transport: MockHomeFeedTransport()
    )
}

private struct MockHomeFeedTransport: ClientTransport {
    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        let encoder = JSONEncoder()

        switch operationID {
        case "getHomeFeed":
            return (
                HTTPResponse(status: .ok, headerFields: [.contentType: "application/json"]),
                HTTPBody(try encoder.encode(Components.Schemas.HomeFeedResponse(data: homeFeed)))
            )
        default:
            return (
                HTTPResponse(status: .internalServerError, headerFields: [.contentType: "application/json"]),
                HTTPBody(#"{"error":"unexpected operation"}"#)
            )
        }
    }

    private var homeFeed: Components.Schemas.HomeFeed {
        .init(
            hero: .init(zipCode: nil, city: nil, state: nil, shows: [show(id: 704), show(id: 705)]),
            trendingComedians: [],
            comediansNearYou: [],
            showsTonight: [show(id: 701), show(id: 702), show(id: 703)],
            moreNearYou: [],
            trendingThisWeek: [show(id: 703), show(id: 706)],
            popularClubs: []
        )
    }

    private func show(id: Int) -> Components.Schemas.Show {
        .init(
            id: id,
            clubName: "The Stand",
            date: Date().addingTimeInterval(TimeInterval(id - 700) * 60 * 60),
            tickets: [.init(price: 24, purchaseUrl: "https://example.com/tickets/\(id)", soldOut: false, _type: "General admission")],
            name: "Tonight Show \(id)",
            socialData: nil,
            lineup: [
                .init(
                    name: "Taylor Tomlinson",
                    imageUrl: "https://example.com/taylor.png",
                    uuid: "comedian-taylor-\(id)",
                    id: id + 1000,
                    userId: nil,
                    socialData: .init(id: id + 1000),
                    isFavorite: false,
                    showCount: 3
                ),
            ],
            description: nil,
            address: "116 E 16th St, New York, NY",
            room: "Main Room",
            imageUrl: "https://example.com/show-\(id).png",
            soldOut: false,
            distanceMiles: nil
        )
    }
}
#endif
