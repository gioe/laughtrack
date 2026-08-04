import Foundation
import Testing

@Suite("Library saved shows")
struct LibrarySavedShowsTests {
    @Test("authenticated Library renders plans and history from saved-show periods")
    func rendersUpcomingAndPastSavedShows() throws {
        let source = try librarySource()

        #expect(source.contains("section: .nextUp"))
        #expect(source.contains("section: .history"))
        #expect(source.contains("period: .upcoming"))
        #expect(source.contains("period: .past"))
        #expect(source.contains("savedShows.upcomingPage?.shows"))
        #expect(source.contains("savedShows.pastPage?.shows"))
        #expect(source.contains("savedShows.loadSavedShows("))
        #expect(source.contains("ShowsListSkeleton(rowCount: 2)"))
        #expect(source.contains("case .empty:\n                        EmptyView()"))
        #expect(source.contains("case .failure(let failure):"))
    }

    @Test("saved-show rows reuse canonical rows and open detail")
    func savedShowRowsOpenShowDetail() throws {
        let source = try librarySource()

        #expect(source.contains("let shows: [Components.Schemas.Show]"))
        #expect(source.contains("ShowRow(show: show, presentation: .compactTicket)"))
        #expect(source.contains("coordinator.open(.show(show.id))"))
        #expect(source.contains(#".accessibilityLabel("Open \(ShowTitlePresentation.title(for: show))")"#))
    }

    @Test("plans, follows, Saved, and History retain canonical priority")
    func favoriteComedianShowsRemainDistinct() throws {
        let source = try librarySource()
        let sectionsStart = try #require(source.range(of: "private struct FavoritePrimitiveSections"))
        let sectionsEnd = try #require(source.range(of: "private struct SavedShowsSection"))
        let sections = source[sectionsStart.lowerBound..<sectionsEnd.lowerBound]

        let nextUp = try #require(sections.range(of: "section: .nextUp"))
        let follows = try #require(sections.range(of: "FavoriteShowsSection("))
        let saved = try #require(sections.range(of: "SavedFavoritesSection("))
        let history = try #require(sections.range(of: "section: .history"))

        #expect(nextUp.lowerBound < follows.lowerBound)
        #expect(follows.lowerBound < saved.lowerBound)
        #expect(saved.lowerBound < history.lowerBound)
        #expect(source.contains("Upcoming shows from comedians you follow."))
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

    @Test("authenticated screenshot persona covers both saved-show periods")
    func screenshotPersonaCoversSavedShows() throws {
        let library = try librarySource()
        let persona = try personaSource()

        #expect(library.contains("persona.upcomingSavedShows"))
        #expect(library.contains("persona.pastSavedShows"))
        #expect(persona.contains("let upcomingSavedShows = ["))
        #expect(persona.contains("let pastSavedShows = ["))
        #expect(persona.contains("lhs.upcomingSavedShows.map"))
        #expect(persona.contains("lhs.pastSavedShows.map"))
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
