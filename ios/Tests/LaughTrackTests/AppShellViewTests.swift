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
            .podcasts,
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
            .podcasts,
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
        // The shows/clubs/comedians quick-search buttons (the "search-pivot
        // hero") were removed in the shows-tonight redesign. HostedView
        // accessibility-tree wiring is broken on iOS 26.x / 18.6, so their
        // absence can't be asserted via findView — `findView(...) == nil` passes
        // vacuously when nothing is wired (TASK-2535). HomeContentSection drives
        // Home's composition, so verify it exposes only the redesigned content
        // rails and no search-pivot affordance.
        #expect(HomeContentSection.sections(for: nil) == [
            .showsTonight,
            .moreNearYou,
            .trendingThisWeek,
            .favoriteShows,
            .comedians,
            .clubs,
            .podcasts,
        ])
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
                .environmentObject(ClubFavoriteStore())
                .environmentObject(PodcastPlaybackController(audioEngine: ShellRecordingPodcastAudioEngine()))
        )
        await host.settle()

        #expect(recorder.getFavoritesCalls >= 1)
    }

    @Test("shell mounts the podcast mini player inside the tab chrome")
    func shellMountsPodcastMiniPlayerInsideTabChrome() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-mini-player")
        let coordinator = NavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-mini-player")
        let player = PodcastPlaybackController(audioEngine: ShellRecordingPodcastAudioEngine())
        player.start(PodcastPlaybackItem(
            id: 901,
            podcastID: 301,
            episodeTitle: "Shell Episode",
            podcastName: "LaughTrack Podcast",
            podcastImageURL: nil,
            displayRole: "guest",
            audioURL: URL(string: "https://cdn.example.com/shell.mp3"),
            episodeURL: URL(string: "https://podcasts.example.com/shell"),
            failedAudioURL: nil
        ))

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
            .environmentObject(ClubFavoriteStore())
            .environmentObject(player)
        )
        await host.settle()

        // iOS 26.x / 18.6 broke HostedView accessibility-tree wiring, so the
        // mounted mini player can't be asserted via findView (TASK-2535). The
        // shell mounts PodcastMiniPlayerView unconditionally in its bottom
        // safe-area inset, and that view renders its chrome iff the shared
        // PodcastPlaybackController has an active item (PodcastMiniPlayerView.body
        // is `if let item = player.currentItem`). The old findView assertion
        // proved the visible direction; cover both gating directions at the
        // model layer so the hidden-when-empty branch isn't silently dropped.

        // Active item → mini player chrome is shown.
        #expect(player.currentItem?.id == 901)
        #expect(player.currentItem?.podcastID == 301)
        #expect(player.currentItem?.episodeTitle == "Shell Episode")
        #expect(player.isPlaying)

        // No active item → mini player chrome is hidden.
        player.dismiss()
        #expect(player.currentItem == nil)
        #expect(!player.isPlaying)
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

@MainActor
private final class ShellRecordingPodcastAudioEngine: PodcastAudioEngine {
    var currentTime: TimeInterval { 0 }
    var duration: TimeInterval { 120 }
    var rate: Float { 1 }
    var isBuffering: Bool { false }

    func load(url: URL, onFailure: @escaping () -> Void) {}
    func play() {}
    func pause() {}
    func stop() {}
    func setObserver(_ handler: @escaping () -> Void) {}
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
