import Foundation
import Testing
import LaughTrackBridge
@testable import LaughTrackApp
#if canImport(UIKit)
import SwiftUI
#endif

@Suite("Library saved shows")
struct LibrarySavedShowsTests {
    @Test("saved-show action opens the typed detail route")
    @MainActor
    func savedShowNavigationIsExecutable() {
        let coordinator = TypedNavigationCoordinator<AppRoute>()

        openLibrarySnapshotShow(id: 41_002, coordinator: coordinator)

        #expect(decodedRoutes(in: coordinator) == [.showDetail(41_002)])
    }

    @Test("saved-show paging stays within the loaded collection after refresh")
    func savedShowPagingClampsToLoadedRows() {
        #expect(librarySavedShowsDisplayPage(
            requestedPage: 1,
            loadedItemCount: 6,
            totalPages: 2,
            pageSize: 5
        ) == 1)
        #expect(librarySavedShowsDisplayPage(
            requestedPage: 1,
            loadedItemCount: 5,
            totalPages: 2,
            pageSize: 5
        ) == 0)
        #expect(librarySavedShowsDisplayPage(
            requestedPage: 2,
            loadedItemCount: 6,
            totalPages: 3,
            pageSize: 5
        ) == 1)
    }

    @Test("authenticated Library renders upcoming saved-show plans only")
    func rendersUpcomingSavedShows() throws {
        let source = try librarySource()

        #expect(source.contains("section: .nextUp"))
        #expect(source.contains("period: .upcoming"))
        #expect(source.contains("page: savedShows.upcomingPage"))
        #expect(!source.contains("savedShows.pastPage?.shows"))
        #expect(!source.contains("From Your Follows"))
        #expect(source.contains("savedShows.loadSavedShows("))
        #expect(source.contains("ShowsListSkeleton(rowCount: 2)"))
        #expect(source.contains("if shows.isEmpty"))
        #expect(source.contains("case .failure(let failure):"))
    }

    @Test("saved shows render five ticket rows per page with paging controls")
    func savedShowsUseTicketPagination() throws {
        let source = try librarySource()

        #expect(source.contains("static let pageSize = 5"))
        #expect(source.contains("visibleShows"))
        #expect(source.contains("LaughTrackPagedControls("))
        #expect(source.contains("onPrevious: showPreviousPage"))
        #expect(source.contains("onNext: showNextPage"))
        #expect(source.contains("await store.loadNextSavedShowsPage("))
        #expect(source.contains("size: Self.pageSize"))
        #expect(!source.contains("\"Load more\""))
    }

    @Test("next-page errors keep rows visible and provide an in-place retry")
    func nextPageErrorsPreserveRowsAndRetry() throws {
        let source = try librarySource()

        #expect(source.contains("failureContent(failure, loadingMore: true)"))
        #expect(source.contains("\"Retry loading more\""))
        #expect(source.contains("loadNextPage(force: true, displayAfterLoad: true)"))
        #expect(source.contains("failureContent(failure, loadingMore: false)"))
        #expect(source.contains("await store.loadSavedShows("))
    }

    @Test("saved-show rows reuse canonical rows and open detail")
    func savedShowRowsOpenShowDetail() throws {
        let source = try librarySource()

        #expect(source.contains("private var shows: [Components.Schemas.Show]"))
        #expect(source.contains("ShowRow(show: show, presentation: .compactTicket)"))
        #expect(source.contains("coordinator.open(.show(show.id))"))
        #expect(source.contains(#".accessibilityLabel("Open \(ShowTitlePresentation.title(for: show))")"#))
    }

    @Test("Shows lead the independent saved-entity rails")
    func explicitCollectionsRetainCanonicalPriority() throws {
        let source = try librarySource()
        let sectionsStart = try #require(source.range(of: "private struct FavoritePrimitiveSections"))
        let sectionsEnd = try #require(source.range(of: "private struct SavedShowsSection"))
        let sections = source[sectionsStart.lowerBound..<sectionsEnd.lowerBound]

        let nextUp = try #require(sections.range(of: "section: .nextUp"))
        let saved = try #require(sections.range(of: "SavedFavoritesSection("))

        #expect(nextUp.lowerBound < saved.lowerBound)
        #expect(!sections.contains("section: .history"))
        #expect(!source.contains("From Your Follows"))
        #expect(!source.contains("HomeFavoriteShowsModel"))
    }

    @Test("signed-out Library does not load account-bound saved shows")
    func signedOutLibraryHasNoSavedShowState() throws {
        let source = try librarySource()
        let guestStart = try #require(source.range(of: "private struct LibraryEmptyState"))
        let guestSource = source[guestStart.lowerBound...]

        #expect(source.contains("} else if authManager.currentSession != nil {"))
        #expect(source.contains("requiresSignIn: true"))
        #expect(!guestSource.contains("SavedShowStore"))
        #expect(!guestSource.contains("loadSavedShows"))
        #expect(guestSource.contains("Shows near me"))
        #expect(guestSource.contains("Follow comedians"))
    }

    @Test("authenticated screenshot supports both saved-show fixture generations")
    func screenshotPersonaSupportsSavedShows() throws {
        let library = try librarySource()
        let persona = try personaSource()

        #expect(library.contains("persona.upcomingSavedShows"))
        #expect(library.contains("shows: [Components.Schemas.Show]"))
        #expect(library.contains("shows: [(title: String, detail: String)]"))
        #expect(persona.contains("upcomingSavedShows"))
        #expect(!library.contains("persona.pastSavedShows"))
    }

    private func librarySource(filePath: String = #filePath) throws -> String {
        try source(
            "Sources/LaughTrackApp/LibraryView.swift",
            filePath: filePath
        )
    }

    private func personaSource(filePath: String = #filePath) throws -> String {
        try source(
            "Sources/LaughTrackApp/AuthenticatedScreenshotPersona.swift",
            filePath: filePath
        )
    }

    private func source(_ relativePath: String, filePath: String) throws -> String {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot.appendingPathComponent(relativePath)
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return try String(contentsOf: sourceURL, encoding: .utf8)
    }
}

#if canImport(UIKit)
@Suite("Library hosted interactions", .serialized)
@MainActor
struct LibraryHostedInteractionTests {
    @Test("saved-show pager selects compact controls for accessibility text sizes")
    func savedShowPagerPresentationAdaptsToDynamicType() {
        #expect(LaughTrackPagedControlsPresentation.resolve(for: .large) == .expanded)
        #expect(LaughTrackPagedControlsPresentation.resolve(for: .accessibility1) == .compact)
        #expect(LaughTrackPagedControlsPresentation.resolve(for: .accessibility5) == .compact)
    }

    @Test("rendered saved-show pager wires Previous and Next actions")
    func savedShowPagerButtonsAreExecutable() async throws {
        var actions: [String] = []
        let host = HostedView(
            LaughTrackPagedControls(
                currentPage: 1,
                pageCount: 3,
                onPrevious: { actions.append("previous") },
                onNext: { actions.append("next") },
                accessibilityIdentifierPrefix: "test.library.pager"
            )
            .padding()
            .environment(\.appTheme, LaughTrackTheme())
        )
        await host.settle(iterations: 4)

        try host.requireLabel("Page 2 of 3")
        try host.tapControl(withIdentifier: "test.library.pager.previous")
        try host.tapControl(withIdentifier: "test.library.pager.next")

        #expect(actions == ["previous", "next"])
    }

    @Test("compact saved-show pager fits narrow accessibility layouts and keeps clear actions")
    func compactSavedShowPagerFitsAndRemainsAccessible() async throws {
        var actions: [String] = []
        let controls = LaughTrackPagedControls(
            currentPage: 1,
            pageCount: 3,
            onPrevious: { actions.append("previous") },
            onNext: { actions.append("next") },
            accessibilityIdentifierPrefix: "test.library.compact-pager"
        )
        .environment(\.appTheme, LaughTrackTheme())
        .environment(\.dynamicTypeSize, .accessibility5)

        let sizingController = UIHostingController(rootView: controls.fixedSize())
        let fittingSize = sizingController.sizeThatFits(
            in: CGSize(width: 1_000, height: 1_000)
        )
        #expect(fittingSize.width <= 320)

        let host = HostedView(controls.frame(width: 320))
        await host.settle(iterations: 4)

        try host.requireLabel("Previous page")
        try host.requireLabel("Page 2 of 3")
        try host.requireLabel("Next page")
        try host.tapControl(withIdentifier: "test.library.compact-pager.previous")
        try host.tapControl(withIdentifier: "test.library.compact-pager.next")

        #expect(actions == ["previous", "next"])
    }

    @Test("fallback entity rows expose metadata labels and open typed routes")
    func fallbackEntityRowsOpenTypedRoutes() async throws {
        let coordinator = TypedNavigationCoordinator<AppRoute>()
        let host = HostedView(
            VStack {
                LaughTrackSearchEntityRow(
                    title: "Taylor Tomlinson",
                    subtitle: "Following · notifications on",
                    imageURL: nil,
                    kind: .comedian,
                    action: { coordinator.open(.comedian(101)) },
                    accessibilityIdentifier: "test.library.comedian"
                )
                LaughTrackSearchEntityRow(
                    title: "The Comedy Cellar",
                    subtitle: "Saved venue",
                    imageURL: nil,
                    kind: .club,
                    action: { coordinator.open(.club(201)) },
                    accessibilityIdentifier: "test.library.club"
                )
                LaughTrackSearchEntityRow(
                    title: "Good One: A Podcast About Jokes",
                    subtitle: "Vulture · 248 episodes",
                    imageURL: nil,
                    kind: .podcast,
                    action: { coordinator.open(.podcast(301)) },
                    accessibilityIdentifier: "test.library.podcast"
                )
            }
            .padding()
            .environment(\.appTheme, LaughTrackTheme())
        )
        await host.settle(iterations: 4)

        try host.requireLabel("Taylor Tomlinson, Following · notifications on")
        try host.tapControl(withIdentifier: "test.library.comedian")
        #expect(decodedRoutes(in: coordinator) == [.comedianDetail(101)])

        try host.requireLabel("The Comedy Cellar, Saved venue")
        try host.tapControl(withIdentifier: "test.library.club")
        #expect(decodedRoutes(in: coordinator) == [.comedianDetail(101), .clubDetail(201)])

        try host.requireLabel("Good One: A Podcast About Jokes, Vulture · 248 episodes")
        try host.tapControl(withIdentifier: "test.library.podcast")
        #expect(decodedRoutes(in: coordinator) == [
            .comedianDetail(101),
            .clubDetail(201),
            .podcastDetail(301),
        ])
    }
}
#endif
