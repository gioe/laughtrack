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
        #expect(AppTab.allCases == [.nearMe, .search, .favorites])
        #expect(AppTab.allCases.map(\.title) == ["Discover", "Search", "Favorites"])
        #expect(AppRoute.nearMe.shellTab == .nearMe)
        #expect(AppRoute.search.shellTab == .search)
        #expect(AppRoute.library.shellTab == .favorites)
        #expect(AppRoute.profile.shellTab == nil)
    }

    @Test("shell can start on the search tab without losing tab chrome")
    func shellCanStartOnSearchTab() async throws {
        let shellState = AppShellState()

        shellState.selectTab(.search)

        #expect(shellState.selectedTab == .search)
        #expect(shellState.resolvedSearchPrimitive == .shows)
        #expect(!shellState.showsLocationHeader)
        #expect(AppTab.allCases.map(\.title) == ["Discover", "Search", "Favorites"])
    }

    @Test("near me tab keeps the real home affordances inside shell chrome")
    func nearMeTabKeepsRealHomeAffordances() async throws {
        let shellState = AppShellState()

        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.selectedPrimitive == nil)
        #expect(!shellState.showsLocationHeader)
        #expect(HomeContentSection.sections(for: shellState.selectedPrimitive) == [
            .showsTonight,
            .moreNearYou,
            .trendingThisWeek,
            .favoriteShows,
            .comedians,
            .clubs,
        ])
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
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-home-frame")
        let nearbyPreferenceStore = container.resolve(NearbyPreferenceStore.self)
        let preference = try #require(
            nearbyPreferenceStore.setManualZip("10012", distanceMiles: 25, city: "New York", state: "NY")
        )

        #expect(preference.zipCode == "10012")
        #expect(preference.city == "New York")
        #expect(preference.state == "NY")
        #expect(HomeContentSection.sections(for: nil) == [
            .showsTonight,
            .moreNearYou,
            .trendingThisWeek,
            .favoriteShows,
            .comedians,
            .clubs,
        ])
        #expect(HomeContentSection.sections(for: .shows) == [
            .showsTonight,
            .moreNearYou,
            .trendingThisWeek,
            .favoriteShows,
        ])
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
            .environmentObject(PodcastFavoriteStore())
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
                .environmentObject(PodcastFavoriteStore())
        )
        await host.settle()

        #expect(recorder.getFavoritesCalls >= 1)
    }

    @Test("shell account header targets the profile route")
    func shellAccountHeaderTargetsProfileRoute() async throws {
        #expect(AppRoute.accountHeaderTarget() == .profile)
    }

    @Test("shell account header layout trims tall safe area gap while preserving touch target")
    func shellAccountHeaderLayoutTrimsTallSafeAreaGapWhilePreservingTouchTarget() async throws {
        let theme = LaughTrackTheme()
        let compactTop = AccountHeaderLayout.accountHeaderTopPadding(safeAreaTop: 24, theme: theme)
        let tallTop = AccountHeaderLayout.accountHeaderTopPadding(safeAreaTop: 59, theme: theme)

        #expect(compactTop > 24)
        #expect(tallTop - compactTop == 17)
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
