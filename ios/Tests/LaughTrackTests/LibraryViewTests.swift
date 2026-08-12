import Foundation
import Testing
@testable import LaughTrackApp

@Suite("Library view")
@MainActor
struct LibraryViewTests {
    @Test("Library uses the durable collection label")
    func libraryUsesProductCopy() async throws {
        #expect(LibraryView.title == "Library")
    }

    @Test("signed-out Library explains account persistence")
    func librarySignedOutPromptCopy() async throws {
        #expect(LibraryView.signedOutPromptTitle == "Sign in to build your Library")
    }

    @Test("Library groups have one canonical priority order")
    func librarySectionPriority() {
        #expect(LibrarySection.allCases == [.nextUp, .saved, .history])
        #expect(LibrarySection.allCases.map(\.title) == [
            "Next Up",
            "Saved",
            "History",
        ])
    }

    @Test("fully empty state waits for every group to resolve empty")
    func fullyEmptyStateRequiresAllGroups() {
        #expect(LibraryContentState(
            nextUp: .empty,
            saved: .empty,
            history: .empty
        ).isFullyEmpty)

        for unresolved in [
            LibraryGroupResolution.loading,
            .content,
            .failure,
        ] {
            #expect(!LibraryContentState(
                nextUp: unresolved,
                saved: .empty,
                history: .empty
            ).isFullyEmpty)
        }
    }

    @Test("empty Library offers blank, seeded Search entry points")
    func emptyLibrarySearchSeeds() {
        #expect(LibrarySearchSeed.pivots == [.shows, .comedians, .clubs, .podcasts])

        for pivot in LibrarySearchSeed.pivots {
            let seed = LibrarySearchSeed.seed(for: pivot)
            #expect(seed.pivot == pivot)
            #expect(seed.query.isEmpty)
            #expect(seed.shortcut == (pivot == .shows ? "Near Me" : nil))
        }
    }

    @Test("saved rows keep detail navigation separate from removal")
    func savedRowsHaveSeparatePrimaryAndSecondaryActions() throws {
        let sourceURL = try savedFavoritesSectionSourceURL()
        let source = try String(contentsOf: sourceURL, encoding: .utf8)

        #expect(source.contains("action: { coordinator.open(.comedian(comedian.id)) }"))
        #expect(source.contains("action: { coordinator.open(.club(club.id)) }"))
        #expect(source.contains("action: { coordinator.open(.podcast(podcast.id)) }"))
        #expect(source.contains("FavoriteButton("))
        #expect(source.contains("currentValue: true"))
        #expect(!source.contains("coordinator.push("))
    }

    private func savedFavoritesSectionSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot.appendingPathComponent(
            "Sources/LaughTrackApp/Components/Settings/SavedFavoritesSection.swift"
        )
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }
}
