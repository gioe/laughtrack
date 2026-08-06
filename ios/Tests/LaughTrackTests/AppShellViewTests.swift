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
    @Test("unit test host does not mount production content")
    func unitTestHostDoesNotMountProductionContent() {
        #expect(!LaughTrackApp.shouldMountProductionContent)
    }

    @Test("shell renders three top-level tabs and keeps account out of the tab bar")
    func shellRendersTabs() async throws {
        #expect(AppTab.allCases == [.nearMe, .search, .favorites])
        #expect(AppTab.allCases.map(\.title) == ["Discover", "Search", "Library"])
        #expect(AppRoute.nearMe.shellTab == .nearMe)
        #expect(AppRoute.search.shellTab == .search)
        #expect(AppRoute.library([]).shellTab == .favorites)
        #expect(AppRoute.profile.shellTab == nil)
    }

    @Test("shell can start on the search tab without losing tab chrome")
    func shellCanStartOnSearchTab() async throws {
        let shellState = AppShellState()

        shellState.selectTab(.search)

        #expect(shellState.selectedTab == .search)
        #expect(shellState.resolvedSearchPrimitive == .shows)
        #expect(!shellState.showsLocationHeader)
        #expect(AppTab.allCases.map(\.title) == ["Discover", "Search", "Library"])
    }

    @Test("Library remains a stable tab across authentication and favorite changes")
    func libraryRemainsAStableTab() throws {
        let source = try String(contentsOf: appShellViewSourceURL(), encoding: .utf8)

        #expect(source.contains("LibraryView("))
        #expect(source.contains(".tabItem { Label(\"Library\", systemImage: \"heart.fill\") }"))
        #expect(!source.contains("private var showFavoritesTab"))
        #expect(!source.contains("if showFavoritesTab"))
        #expect(!source.contains(".onChange(of: showFavoritesTab)"))
    }

    @Test("shell entity pivots render only on Search")
    func shellEntityPivotsRenderOnlyOnSearch() throws {
        let source = try String(contentsOf: appShellViewSourceURL(), encoding: .utf8)

        #expect(source.contains(
            "if shellState.selectedTab == .search {\n                primitiveFilterScroller\n            }"
        ))
        #expect(!source.contains("Home/Favorites (optional category filter)"))
    }

    @Test("debug soft-push launch override presents the prompt sheet")
    func debugSoftPushLaunchOverridePresentsPromptSheet() async throws {
        let coordinator = LaughTrackHostedViewTestSupport.makeSoftPushPromptCoordinator(
            name: "debug-soft-push-launch"
        )

        #expect(DebugSoftPushPromptLaunch.shouldForcePrompt(environment: [:]) == false)
        #expect(DebugSoftPushPromptLaunch.shouldForcePrompt(environment: [
            UITestLaunchArgs.forceSoftPushPrompt: "1",
        ]))

        DebugSoftPushPromptLaunch.fireIfRequested(
            coordinator: coordinator,
            environment: [UITestLaunchArgs.forceSoftPushPrompt: "1"]
        )

        #expect(coordinator.presentation == .promptingSheet)
        #expect(coordinator.hasPresentedThisSession)
    }

    @Test("near me tab keeps the real home affordances inside shell chrome")
    func nearMeTabKeepsRealHomeAffordances() async throws {
        let shellState = AppShellState()

        #expect(shellState.selectedTab == .nearMe)
        #expect(shellState.selectedPrimitive == nil)
        #expect(!shellState.showsLocationHeader)
        #expect(HomeContentSection.sections(for: shellState.selectedPrimitive) == [
            .showsTonight,
            .followedComedianShows,
            .thisWeek,
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
            .followedComedianShows,
            .thisWeek,
            .comedians,
            .clubs,
            .podcasts,
        ])
        #expect(HomeContentSection.sections(for: .shows) == [
            .showsTonight,
            .followedComedianShows,
            .thisWeek,
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
            .followedComedianShows,
            .thisWeek,
            .comedians,
            .clubs,
            .podcasts,
        ])
    }

    @Test("shell header lets the Discover spotlight blend through the safe area")
    func shellHeaderLetsDiscoverSpotlightBlendThroughSafeArea() throws {
        let source = try String(contentsOf: appShellViewSourceURL(), encoding: .utf8)

        #expect(source.contains("LaughTrackAtmosphereBackground()"))
        #expect(source.contains(".background(Color.clear)"))
        #expect(source.contains("shellAlignedTabBackground(safeAreaTop: safeAreaTop)"))
        #expect(source.contains("let headerHeight = AccountHeaderLayout.headerHeight(safeAreaTop: safeAreaTop, theme: theme)"))
        #expect(source.contains("GeometryReader { proxy in"))
        #expect(source.contains(".frame(width: proxy.size.width, height: proxy.size.height + headerHeight)"))
        #expect(source.contains(".offset(y: -headerHeight)"))
        #expect(!source.contains(".background(theme.laughTrackTokens.colors.canvas.opacity(0.97))"))
    }

    @Test("primitive filter maps every category to a stable scroll target")
    func primitiveFilterMapsEveryCategoryToStableScrollTarget() throws {
        let source = try String(contentsOf: appShellViewSourceURL(), encoding: .utf8)

        #expect(PrimitiveFilterScrollLayout.scrollTarget(for: .shows) == .primitive("shows"))
        #expect(PrimitiveFilterScrollLayout.scrollTarget(for: .comedians) == .primitive("comedians"))
        #expect(PrimitiveFilterScrollLayout.scrollTarget(for: .clubs) == .primitive("clubs"))
        #expect(PrimitiveFilterScrollLayout.scrollTarget(for: .podcasts) == .trailingInset)
        #expect(source.contains("ScrollViewReader { proxy in"))
        #expect(source.contains(".id(PrimitiveFilterScrollLayout.pillTarget(for: primitive))"))
        #expect(source.contains(".id(PrimitiveFilterScrollTarget.trailingInset)"))
        #expect(source.contains("scrollToSelectedPrimitive(using: proxy, animated: false)"))
        #expect(source.contains(".onChange(of: shellState.selectedPrimitive)"))
        #expect(source.contains("scrollToSelectedPrimitive(using: proxy, animated: true)"))
        #expect(source.contains("proxy.scrollTo(target, anchor: .trailing)"))
        #expect(source.contains(".font(.system(size: 12, weight: .heavy, design: .rounded))"))
        #expect(source.contains(".tracking(1.4)"))
        #expect(source.contains("Capsule()"))
        #expect(source.contains("dash: [0.5, 5]"))
    }

    @Test("podcasts trailing anchor uses a bounded layout spacer")
    func podcastsTrailingAnchorUsesBoundedLayoutSpacer() throws {
        let source = try String(contentsOf: appShellViewSourceURL(), encoding: .utf8)
        let theme = LaughTrackTheme()

        #expect(
            PrimitiveFilterScrollLayout.trailingInsetWidth(theme: theme) ==
                theme.spacing.xxxl + theme.spacing.sm
        )
        #expect(source.contains(
            "width: PrimitiveFilterScrollLayout.trailingInsetWidth(theme: theme)"
        ))
        #expect(source.contains("height: 1"))
    }

    @Test("generic page backgrounds inherit the shell atmosphere")
    func genericPageBackgroundsInheritShellAtmosphere() throws {
        let source = try String(contentsOf: laughTrackThemeSourceURL(), encoding: .utf8)

        #expect(source.contains("background: .clear,"))
        #expect(source.contains("backgroundGrouped: .clear,"))
        #expect(source.contains("backgroundSecondary: laughTrack.colors.surface,"))
        #expect(source.contains("backgroundTertiary: laughTrack.colors.surfaceMuted,"))
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
        let coordinator = TypedNavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-favorites-load")
        let nearbyStore = container.resolve(NearbyPreferenceStore.self)
        nearbyStore.setManualZip("10012", distanceMiles: 25)
        let recorder = ShellFavoritesRequestRecorder()
        let apiClient = Client(
            serverURL: offlineAppShellBaseURL,
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
                .environmentObject(
                    LaughTrackHostedViewTestSupport.makeSoftPushPromptCoordinator(
                        name: "shell-favorites-load"
                    )
                )
        )
        await host.settle()

        #expect(recorder.getFavoritesCalls >= 1)
        #expect(recorder.getHomeFeedCalls >= 1)
        #expect(recorder.allRequestsUseOfflineBaseURL)
    }

    @Test("authenticated shell immediately reconciles a restored server push opt-in")
    func authenticatedShellReconcilesRestoredPushOptIn() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthenticatedAuthManager(
            name: "shell-restored-push-opt-in"
        )
        authManager.loadUserRequest = {
            AuthenticatedUser(
                userId: "restored-push-user",
                displayName: "Push User",
                email: "push@example.com",
                avatarURL: nil,
                pushShowNotifications: true,
                comedianOnboardingCompleted: true
            )
        }
        await authManager.refreshCurrentUser()

        let navigationCoordinator = TypedNavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(
            name: "shell-restored-push-opt-in"
        )
        container.resolve(NearbyPreferenceStore.self).setManualZip("10012", distanceMiles: 25)
        let requestRecorder = ShellFavoritesRequestRecorder()
        let apiClient = Client(
            serverURL: offlineAppShellBaseURL,
            transport: MockShellFavoritesTransport(recorder: requestRecorder)
        )
        let pushCoordinator = LaughTrackHostedViewTestSupport.makeSoftPushPromptCoordinator(
            name: "shell-restored-push-opt-in"
        )
        let host = HostedView(
            AppShellView(
                apiClient: apiClient,
                favorites: ComedianFavoriteStore(),
                shellState: AppShellState()
            )
                .environment(\.appTheme, LaughTrackTheme())
                .environment(\.serviceContainer, container)
                .navigationCoordinator(navigationCoordinator)
                .environmentObject(authManager)
                .environmentObject(PodcastFavoriteStore())
                .environmentObject(ClubFavoriteStore())
                .environmentObject(PodcastPlaybackController(audioEngine: ShellRecordingPodcastAudioEngine()))
                .environmentObject(pushCoordinator)
        )
        await host.settle()

        #expect(pushCoordinator.presentation == .promptingSheet)
        #expect(pushCoordinator.hasPresentedThisSession)
    }

    private func appShellViewSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/AppShellView.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }

    private func laughTrackThemeSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackBridge/LaughTrackTheme.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }

    @Test("podcast mini player chrome gates on the shared playback controller")
    func podcastMiniPlayerChromeGatesOnPlaybackController() async throws {
        let authManager = await LaughTrackHostedViewTestSupport.makeAuthManager(name: "shell-mini-player")
        let coordinator = TypedNavigationCoordinator<AppRoute>()
        let container = LaughTrackHostedViewTestSupport.makeServiceContainer(name: "shell-mini-player")
        let nearbyStore = container.resolve(NearbyPreferenceStore.self)
        nearbyStore.setManualZip("94108", distanceMiles: 50)
        let recorder = ShellFavoritesRequestRecorder()
        let apiClient = Client(
            serverURL: offlineAppShellBaseURL,
            transport: MockShellFavoritesTransport(recorder: recorder)
        )
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
            .environmentObject(player)
            .environmentObject(
                LaughTrackHostedViewTestSupport.makeSoftPushPromptCoordinator(
                    name: "shell-mini-player"
                )
            )
        )
        await host.settle()

        #expect(recorder.getHomeFeedCalls >= 1)
        #expect(recorder.allRequestsUseOfflineBaseURL)

        // iOS 26.x / 18.6 broke HostedView accessibility-tree wiring, so the
        // mounted mini player can't be asserted via findView (TASK-2535). The
        // mini player itself renders its chrome iff the shared
        // PodcastPlaybackController has an active item (PodcastMiniPlayerView.body
        // is `if let item = player.currentItem`); cover both gating directions
        // at the model layer so the hidden-when-empty branch isn't silently
        // dropped. Note: TASK-2629 moved the mount site from this shell's
        // .safeAreaInset up to ContentView.appShell's CoordinatedNavigationStack
        // so it survives detail-route pushes — see ContentView.swift around
        // the `} root:` builder.

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

    @Test("account drawer header uses profile identity without status copy")
    func accountDrawerHeaderUsesProfileIdentityWithoutStatusCopy() throws {
        let source = try String(contentsOf: appShellViewSourceURL(), encoding: .utf8)

        #expect(source.contains("private var accountDrawerAvatar: some View"))
        #expect(source.contains("LaughTrackAvatar("))
        #expect(source.contains("user?.avatarURL"))
        #expect(source.contains("private var accountDrawerTitle: String"))
        #expect(source.contains("user.displayName?.trimmingCharacters(in: .whitespacesAndNewlines)"))
        #expect(source.contains("return user.email"))
        #expect(source.contains("Text(accountDrawerTitle)"))
        #expect(!source.contains("Text(\"Account\")"))
        #expect(!source.contains("\"Signed in\""))
        #expect(!source.contains("\"Guest browsing\""))
    }

    @Test("shell account header layout trims tall safe area gap while preserving touch target")
    func shellAccountHeaderLayoutTrimsTallSafeAreaGapWhilePreservingTouchTarget() async throws {
        let theme = LaughTrackTheme()
        let compactTop = AccountHeaderLayout.accountHeaderTopPadding(safeAreaTop: 24, theme: theme)
        let tallTop = AccountHeaderLayout.accountHeaderTopPadding(safeAreaTop: 59, theme: theme)
        let tallHeight = AccountHeaderLayout.headerHeight(safeAreaTop: 59, theme: theme)

        #expect(compactTop > 24)
        #expect(tallTop - compactTop == 17)
        #expect(tallHeight == tallTop + AccountHeaderLayout.buttonSize + theme.spacing.sm)
        #expect(AccountHeaderLayout.buttonSize >= 44)
    }
}

private let offlineAppShellBaseURL = URL(string: "http://127.0.0.1:1")!

private final class ShellFavoritesRequestRecorder: @unchecked Sendable {
    private let lock = NSLock()
    private var requests: [(operationID: String, baseURL: URL)] = []

    var getFavoritesCalls: Int {
        lock.withLock { requests.count(where: { $0.operationID == "getFavorites" }) }
    }

    var getHomeFeedCalls: Int {
        lock.withLock { requests.count(where: { $0.operationID == "getHomeFeed" }) }
    }

    var allRequestsUseOfflineBaseURL: Bool {
        lock.withLock { requests.allSatisfy { $0.baseURL == offlineAppShellBaseURL } }
    }

    func record(operationID: String, baseURL: URL) {
        lock.withLock {
            requests.append((operationID, baseURL))
        }
    }
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
        recorder.record(operationID: operationID, baseURL: baseURL)

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
