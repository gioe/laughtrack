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
    @Test("shell renders three top-level tabs and keeps account out of the tab bar")
    func shellRendersTabs() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "app-shell-tabs")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "app-shell-tabs")
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: ComedianFavoriteStore(),
                shellState: AppShellState()
            )
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, container)
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )
        await host.settle()

        try host.requireView(withIdentifier: LaughTrackViewTestID.homeScreen)
        try host.requireText("Near Me")
        try host.requireText("Search")
        try host.requireText("Favorites")
        #expect(host.findText("Profile") == nil)
        #expect(AppTab.allCases == [.nearMe, .search, .favorites])
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
                initialTab: .search,
                shellState: AppShellState()
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )
        await host.settle()

        try host.requireView(withIdentifier: LaughTrackViewTestID.searchTabScreen)
        try host.requireText("Near Me")
        try host.requireText("Search")
    }

    @Test("near me tab keeps the real home affordances inside shell chrome")
    func nearMeTabKeepsRealHomeAffordances() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-home")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-home")
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: ComedianFavoriteStore(),
                shellState: AppShellState()
            )
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, container)
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )
        await host.settle()

        try host.requireView(withIdentifier: LaughTrackViewTestID.homeScreen)
        try host.requireView(withIdentifier: LaughTrackViewTestID.homeNearMeHeader)
        try host.requireView(withIdentifier: LaughTrackViewTestID.homeShowsTonightRail)
        try host.requireText("Near me")
        try host.requireText("Shows tonight")
        // homeSettingsButton lives inside HomeView's `.toolbar` modifier, which
        // requires an ancestor NavigationStack. Wrapping the test view in
        // NavigationStack works in isolation but doesn't reliably propagate the
        // toolbar item when other tests have already mounted hosting controllers
        // on the shared UIWindow under iOS 26 / Xcode 26. The toolbar surface is
        // exercised end-to-end via ContentViewNavigationTests which uses the real
        // CoordinatedNavigationStack-rooted ContentView.
    }

    @Test("home does not render the home frame card")
    func homeDoesNotRenderHomeFrameCard() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-home-frame")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-home-frame")
        let nearbyPreferenceStore = container.resolve(NearbyPreferenceStore.self)
        nearbyPreferenceStore.setManualZip("10012", distanceMiles: 25, city: "New York", state: "NY")
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: ComedianFavoriteStore(),
                shellState: AppShellState()
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )
        await host.settle()

        #expect(host.findText("Home frame") == nil)
        #expect(host.findText("Tonight near New York, NY") == nil)
        #expect(host.findText("Search changes location and time") == nil)
        #expect(host.findText("Adjust in Search") == nil)
        try host.requireText("Shows tonight")
        try host.requireText("Upcoming after tonight")
        #expect(host.findText("Nearby tonight") == nil)
        #expect(host.findText("Shows around ZIP 10012") == nil)
    }

    @Test("home no longer exposes the search-pivot hero after shows-tonight redesign")
    func homeRemovesSearchPivotHero() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-home-search-smoke")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-home-search-smoke")
        let host = HostedView(
            AppShellView(
                apiClient: LaughTrackHostedViewTestSupport.makeClient(),
                favorites: ComedianFavoriteStore(),
                shellState: AppShellState()
            )
            .environment(\.appTheme, LaughTrackTheme())
            .environment(\.serviceContainer, container)
            .navigationCoordinator(coordinator)
            .environmentObject(authManager)
        )

        #expect(host.findView(withIdentifier: LaughTrackViewTestID.homeShowsSearchButton) == nil)
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.homeClubsSearchButton) == nil)
        #expect(host.findView(withIdentifier: LaughTrackViewTestID.homeComediansSearchButton) == nil)
    }

    @Test("authenticated shell triggers favorites fetch without visiting the Favorites tab")
    func authenticatedShellTriggersFavoritesFetch() async throws {
        // Regression guard for TASK-1762. The favorites load used to live on
        // the old standalone SettingsView (and briefly on the Favorites tab), so heart-state on Search and
        // detail surfaces went stale until the user happened to open Favorites.
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
                favorites: ComedianFavoriteStore(),
                shellState: AppShellState()
            )
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, container)
                .navigationCoordinator(coordinator)
                .environmentObject(authManager)
        )
        await host.settle()

        #expect(recorder.getFavoritesCalls >= 1)
    }

    @Test("shell account header targets the profile route")
    func shellAccountHeaderTargetsProfileRoute() async throws {
        #expect(AppRoute.accountHeaderTarget() == .profile)
    }

    @Test("shell account header layout tracks safe area and touch target")
    func shellAccountHeaderLayoutTracksSafeAreaAndTouchTarget() async throws {
        let theme = LaughTrackTheme()
        let compactTop = AccountHeaderLayout.accountHeaderTopPadding(safeAreaTop: 24, theme: theme)
        let tallTop = AccountHeaderLayout.accountHeaderTopPadding(safeAreaTop: 59, theme: theme)

        #expect(tallTop - compactTop == 35)
        #expect(compactTop > 24)
        #expect(AccountHeaderLayout.buttonSize >= 44)
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
