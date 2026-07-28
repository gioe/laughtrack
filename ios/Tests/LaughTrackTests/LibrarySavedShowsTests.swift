import Foundation
import Testing

@Suite("Library saved shows")
struct LibrarySavedShowsTests {
    @Test("authenticated Library renders distinct saved-show periods")
    func rendersUpcomingAndPastSavedShows() throws {
        let source = try librarySource()

        #expect(source.contains(#"title: "Upcoming saved shows""#))
        #expect(source.contains(#"title: "Past saved shows""#))
        #expect(source.contains("period: .upcoming"))
        #expect(source.contains("period: .past"))
        #expect(source.contains("savedShows.upcomingPage?.shows"))
        #expect(source.contains("savedShows.pastPage?.shows"))
        #expect(source.contains("savedShows.loadSavedShows("))
        #expect(source.contains("ShowsListSkeleton(rowCount: 2)"))
        #expect(source.contains("LaughTrackStateView("))
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

    @Test("favorite-comedian shows retain inferred touring copy")
    func favoriteComedianShowsRemainDistinct() throws {
        let source = try librarySource()

        let upcoming = try #require(source.range(of: #"title: "Upcoming saved shows""#))
        let past = try #require(source.range(of: #"title: "Past saved shows""#))
        let inferred = try #require(source.range(of: #"title: "Your favorites are touring""#))

        #expect(upcoming.lowerBound < past.lowerBound)
        #expect(past.lowerBound < inferred.lowerBound)
        #expect(source.contains("Upcoming shows from comedians you follow."))
    }

    @Test("signed-out Library does not load account-bound saved shows")
    func signedOutLibraryHasNoSavedShowState() throws {
        let source = try librarySource()
        let guestStart = try #require(source.range(of: "private struct GuestFavoritesPreview"))
        let guestSource = source[guestStart.lowerBound...]

        #expect(source.contains("} else if authManager.currentSession != nil {"))
        #expect(source.contains("} else {\n                    GuestFavoritesPreview()"))
        #expect(!guestSource.contains("SavedShowStore"))
        #expect(!guestSource.contains("loadSavedShows"))
        #expect(!guestSource.contains("Upcoming saved shows"))
        #expect(!guestSource.contains("Past saved shows"))
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
