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

@Suite("App shell")
@MainActor
struct AppShellViewTests {
    @Test("shell renders four top-level tabs")
    func shellRendersTabs() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "app-shell-tabs")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "app-shell-tabs")
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: ComedianFavoriteStore()
            )
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, container)
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.homeScreen)
        try host.requireText("Home")
        try host.requireText("Search")
        try host.requireText("Library")
        try host.requireText("Profile")
    }

    @Test("shell can start on the search tab without losing tab chrome")
    func shellCanStartOnSearchTab() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "app-shell-search")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "app-shell-search")
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: ComedianFavoriteStore(),
                initialTab: .search
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.searchTabScreen)
        try host.requireText("Home")
        try host.requireText("Search")
    }

    @Test("home tab keeps the real home affordances inside shell chrome")
    func homeTabKeepsRealHomeAffordances() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-home")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-home")
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: ComedianFavoriteStore()
            )
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, container)
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.homeScreen)
        try host.requireView(withIdentifier: LaughTrackViewTestID.homeShowsSearchButton)
        try host.requireText("Jump back into Search")
        try host.requireText("Open Search from a head start")
        // homeSettingsButton lives inside HomeView's `.toolbar` modifier, which
        // requires an ancestor NavigationStack. Wrapping the test view in
        // NavigationStack works in isolation but doesn't reliably propagate the
        // toolbar item when other tests have already mounted hosting controllers
        // on the shared UIWindow under iOS 26 / Xcode 26. The toolbar surface is
        // exercised end-to-end via ContentViewNavigationTests which uses the real
        // CoordinatedNavigationStack-rooted ContentView.
    }

    @Test("home nearby section remains visible after compact browse redesign")
    func homeNearbySectionSurvivesRedesign() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-home-nearby")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-home-nearby")
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: ComedianFavoriteStore()
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.requireText("Comedy worth noticing nearby")
        try host.requireText("Nearby tonight")
    }

    @Test("home search seed still opens search after browse redesign")
    func homeSearchSeedStillOpensSearch() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-home-search-smoke")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-home-search-smoke")
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: ComedianFavoriteStore()
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.tapControl(withIdentifier: LaughTrackViewTestID.homeShowsSearchButton)
        try host.requireView(withIdentifier: LaughTrackViewTestID.searchTabScreen)
    }

    @Test("authenticated shell triggers favorites fetch without visiting the Library tab")
    func authenticatedShellTriggersFavoritesFetch() async throws {
        // Regression guard for TASK-1762. The favorites load used to live on
        // SettingsView (and briefly on LibraryView), so heart-state on Search and
        // detail surfaces went stale until the user happened to open Library.
        // Hosting the `.task(id:)` on AppShellView means the load fires as soon
        // as the authenticated shell appears, before any tab is opened.
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "shell-favorites-load"
        )
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-favorites-load")
        let recorder = ShellFavoritesRequestRecorder()
        let apiClient = Client(
            serverURL: URL(string: "https://example.com")!,
            transport: MockShellFavoritesTransport(recorder: recorder)
        )
        let host = HostedView(
            AppShellView(
                apiClient: apiClient,
                favorites: ComedianFavoriteStore()
            )
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, container)
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )
        await host.settle()

        #expect(recorder.getFavoritesCalls >= 1)
    }

    @Test("shell can start on the profile tab and shows the profile surface, not Settings")
    func shellCanStartOnProfileTab() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "app-shell-profile")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "app-shell-profile")
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: ComedianFavoriteStore(),
                initialTab: .profile
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        try host.requireView(withIdentifier: LaughTrackViewTestID.profileTabScreen)
        try host.requireLabel("Open Settings")
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.settingsScreen) == nil)
    }
}

private final class ShellFavoritesRequestRecorder: @unchecked Sendable {
    var getFavoritesCalls = 0
}

private struct MockShellFavoritesTransport: ClientTransport {
    let recorder: ShellFavoritesRequestRecorder

    func send(
        _ request: HTTPRequest,
        body: HTTPBody?,
        baseURL: URL,
        operationID: String
    ) async throws -> (HTTPResponse, HTTPBody?) {
        if operationID == "getFavorites" {
            recorder.getFavoritesCalls += 1
        }

        return (
            HTTPResponse(
                status: .internalServerError,
                headerFields: [.contentType: "application/json"]
            ),
            HTTPBody(#"{"error":"unexpected operation"}"#)
        )
    }
}
#endif
