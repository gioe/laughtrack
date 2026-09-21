import Foundation
import Testing
@testable import LaughTrackApp

@Suite("Detail navigation chrome")
struct DetailNavigationChromeTests {
    @Test("detail chrome supplies compact titles for wrapping inline navigation")
    func entityDetailNavigationTitlesAreCompact() {
        #expect(DetailNavigationChrome.title(for: .club) == "Club")
        #expect(DetailNavigationChrome.title(for: .comedian) == "Comedian")
        #expect(DetailNavigationChrome.title(for: .show) == "Show")
    }

    @Test("entity detail hero extends behind the top safe area")
    func entityDetailHeroExtendsBehindTopSafeArea() {
        #expect(DetailNavigationChrome.extendsHeroBehindTopSafeArea)
    }

    @Test("status-bar scrim is opaque behind the clock and fades to clear")
    func statusBarScrimFadesFromOpaqueToClear() {
        let stops = DetailNavigationChrome.statusBarScrimStops

        // Fully opaque at the screen's top edge so scrolled content can
        // never collide with the status bar clock, fading to fully clear
        // at the bottom so it reads as a fade rather than a hard bar.
        #expect(stops.first?.opacity == 1.0)
        #expect(stops.first?.location == 0)
        #expect(stops.last?.opacity == 0.0)
        #expect(stops.last?.location == 1)

        // Locations must be monotonically non-decreasing for the gradient
        // to render as a single top-down fade.
        let locations = stops.map(\.location)
        #expect(locations == locations.sorted())
    }

    @Test("detail status bar scrim stays transparent over the page atmosphere")
    func detailStatusBarScrimStaysTransparentOverPageAtmosphere() throws {
        let source = try String(contentsOf: detailNavigationChromeSourceURL(), encoding: .utf8)
        let block = try sourceBlock(
            in: source,
            from: "struct DetailStatusBarScrim",
            to: "struct DetailBackButton"
        )

        #expect(block.contains("LinearGradient("))
        #expect(!block.contains("LaughTrackAtmosphereBackground()"))
        #expect(!block.contains("theme.laughTrackTokens.colors.canvas"))
    }

    private func detailNavigationChromeSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot.appendingPathComponent("Sources/LaughTrackApp/Detail/Components/DetailNavigationChrome.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }

    private func sourceBlock(in source: String, from startMarker: String, to endMarker: String) throws -> String {
        guard
            let start = source.range(of: startMarker),
            let end = source.range(of: endMarker, range: start.upperBound..<source.endIndex)
        else {
            throw CocoaError(.fileReadCorruptFile)
        }

        return String(source[start.lowerBound..<end.lowerBound])
    }
}

import SwiftUI
import LaughTrackBridge

@Suite("Detail return context")
@MainActor
struct DetailReturnContextTests {
    @Test("deep return describes the real tab and preserves search state", arguments: AppTab.allCases)
    func returnsToOrigin(_ tab: AppTab) throws {
        let shell = AppShellState()
        shell.selectTab(tab)
        let search = SearchRootModel()
        search.activePivot = .comedians
        search.query = "Taylor"
        search.selectedShortcut = "This Weekend"
        shell.setSearchPrimitive(.comedians)
        let coordinator = TypedNavigationCoordinator<AppRoute>()
        #expect(coordinator.detailHomeAction == nil)
        coordinator.push(.comedianDetail(101))
        #expect(coordinator.detailHomeAction == nil)
        coordinator.push(.podcastDetail(42))
        coordinator.push(.podcastEpisodeDetail(501))
        let presentation = DetailRootReturnPresentation(tab: shell.selectedTab)
        let expected = tab == .nearMe ? "Discover" : tab == .search ? "Search" : "Library"
        #expect(presentation.title == expected)
        #expect(presentation.accessibilityLabel == "Return to \(expected)")
        #expect(presentation.systemImage != "house")
        let returnToRoot = try #require(coordinator.detailHomeAction)
        returnToRoot()
        #expect(coordinator.routes.isEmpty)
        #expect(shell.selectedTab == tab)
        #expect(shell.resolvedSearchPrimitive == .comedians)
        #expect(search.activePivot == .comedians)
        #expect(search.query == "Taylor")
        #expect(search.selectedShortcut == "This Weekend")
        #expect(coordinator.detailHomeAction == nil)
    }

    @Test("back removes one detail and direct entry has no redundant return action")
    func backAndDirectEntry() {
        let coordinator = TypedNavigationCoordinator<AppRoute>()
        coordinator.push(.showDetail(201))
        #expect(coordinator.detailHomeAction == nil)
        coordinator.push(.clubDetail(301))
        coordinator.pop()
        #expect(decodedRoutes(in: coordinator, as: AppRoute.self) == [.showDetail(201)])
        #expect(coordinator.detailHomeAction == nil)
        coordinator.pop()
        #expect(coordinator.routes.isEmpty)
    }

    @Test("compact identity appears only after the hero exits and ignores empty titles")
    func compactIdentity() {
        let threshold = DetailNavigationChrome.stickyChromeTopOffset + 44
        #expect(DetailScrolledIdentity.resolve(title: "Comedy Cellar", heroBottom: nil) == nil)
        #expect(DetailScrolledIdentity.resolve(title: "Comedy Cellar", heroBottom: threshold + 1) == nil)
        #expect(DetailScrolledIdentity.resolve(title: "  Comedy Cellar  ", heroBottom: threshold) == "Comedy Cellar")
        #expect(DetailScrolledIdentity.resolve(title: "Comedy Cellar", heroBottom: -100) == "Comedy Cellar")
        #expect(DetailScrolledIdentity.resolve(title: "  ", heroBottom: -100) == nil)
        #expect(DetailScrolledIdentity.resolve(title: nil, heroBottom: -100) == nil)
    }
}

#if canImport(UIKit)
import UIKit

@Suite("Detail context hosted", .serialized)
@MainActor
struct DetailReturnContextHostedTests {
    @Test("scrolling reveals identity beside truthful return controls and the player", arguments: AppTab.allCases)
    func scrollingIdentity(_ tab: AppTab) async throws {
        let observer = DetailIdentityObserver()
        let coordinator = TypedNavigationCoordinator<AppRoute>()
        coordinator.push(.comedianDetail(101))
        coordinator.push(.podcastDetail(42))
        let player = PodcastPlaybackController(audioEngine: DetailContextAudioEngine(), registersRemoteCommands: false)
        player.start(PodcastPlaybackItem(id: 1, episodeID: 1, podcastID: 42, episodeTitle: "Comedy on the road",
            podcastName: "Comedy conversations", podcastImageURL: nil, displayRole: "Episode",
            audioURL: URL(string: "https://example.com/audio.mp3"), episodeURL: nil, failedAudioURL: nil))
        let host = HostedView(NavigationStack {
            DetailIdentityHarness(observer: observer)
        }
        .safeAreaInset(edge: .bottom) {
            PodcastMiniPlayerView(player: player, apiClient: LaughTrackHostedViewTestSupport.makeClient()).padding()
        }
        .environmentObject(coordinator)
        .environment(\.detailRootTab, tab)
        .environment(\.horizontalSizeClass, .compact), freshWindow: true, viewportSize: CGSize(width: 375, height: 812))
        await host.settle()
        #expect(observer.identity == nil)
        try capture(host, name: "\(tab.title)-top")
        host.scrollDown(pages: 1)
        await host.settle()
        #expect(try #require(host.scrollMetrics()).offset > 100)
        #expect(observer.identity == DetailIdentityHarness.title)
        #expect(player.isPlaying)
        try capture(host, name: "\(tab.title)-scrolled")
        host.scrollDown(pages: -1)
        await host.settle()
        #expect(observer.identity == nil)
    }

    @Test("native back admission and root player positioning survive hidden navigation bars")
    func nativeBackSupport() async throws {
        let root = UIViewController()
        let detail = UIViewController()
        let navigation = UINavigationController(rootViewController: root)
        navigation.setNavigationBarHidden(true, animated: false)
        let window = UIWindow(frame: CGRect(x: 0, y: 0, width: 375, height: 812))
        window.rootViewController = navigation
        window.makeKeyAndVisible()
        defer { window.isHidden = true; window.rootViewController = nil }
        navigation.pushViewController(detail, animated: false)
        let chrome = NavigationPlayerChrome()
        let playerView = UIView()
        chrome.attach(playerView)
        let support = NativeInteractivePopSupport.PopGestureHost()
        support.playerChrome = chrome
        detail.addChild(support)
        detail.view.addSubview(support.view)
        support.didMove(toParent: detail)
        support.installIfNeeded()
        defer { support.restore() }
        let gesture = try #require(navigation.interactivePopGestureRecognizer)
        #expect(gesture.isEnabled)
        #expect(support.gestureRecognizerShouldBegin(gesture))
        chrome.synchronize(rootVisible: false)
        #expect(playerView.transform.ty > 0)
        navigation.popViewController(animated: false)
        #expect(navigation.topViewController === root)
        #expect(!support.gestureRecognizerShouldBegin(gesture))
        chrome.synchronize(rootVisible: true)
        #expect(playerView.transform == .identity)
    }

    private func capture(_ host: HostedView, name: String) throws {
        let output = FileManager.default.temporaryDirectory.appendingPathComponent("task4027-\(name).png")
        try #require(host.snapshot().pngData()).write(to: output)
        print("Detail context capture: \(output.path)")
    }
}

@MainActor
private final class DetailIdentityObserver {
    var identity: String?
}

private struct DetailIdentityProbe: View {
    @Environment(\.detailCompactIdentity) private var identity
    let observer: DetailIdentityObserver
    var body: some View {
        Color.clear
            .onAppear { observer.identity = identity }
            .onChange(of: identity) { observer.identity = $0 }
            .allowsHitTesting(false)
    }
}

private struct DetailIdentityHarness: View {
    static let title = "Comedy conversations with Taylor and friends"
    let observer: DetailIdentityObserver
    @EnvironmentObject private var coordinator: TypedNavigationCoordinator<AppRoute>
    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                MarqueeHero(title: Self.title, imageURL: "", thumbnailStyle: .podcastRail)
                ForEach(0..<20) { index in
                    Text("Episode \(index + 1): Stories from the stage")
                        .frame(maxWidth: .infinity, minHeight: 100)
                        .background(.gray.opacity(0.2))
                }
            }
        }
        .ignoresSafeArea(.container, edges: .top)
        .modifier(DetailAtmosphereRouteBackground())
        .overlay(alignment: .top) {
            DetailChromeBar(onBack: { coordinator.pop() }, onHome: coordinator.detailHomeAction,
                favoriteState: DetailFavoriteState(isFavorite: false, isPending: false, action: {}))
                .background(DetailIdentityProbe(observer: observer))
        }
        .modifier(EntityDetailNavigationChrome(entity: .podcast, title: Self.title))
    }
}

@MainActor
private final class DetailContextAudioEngine: PodcastAudioEngine {
    func load(url: URL, onFailure: @escaping () -> Void) {}
    func play() {}
    func pause() {}
    func stop() {}
}
#endif
