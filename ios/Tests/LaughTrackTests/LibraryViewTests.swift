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
        #expect(LibrarySection.allCases == [.nextUp, .fromFollows, .saved, .history])
        #expect(LibrarySection.allCases.map(\.title) == [
            "Next Up",
            "From Your Follows",
            "Saved",
            "History",
        ])
    }

    @Test("fully empty state waits for every group to resolve empty")
    func fullyEmptyStateRequiresAllGroups() {
        #expect(LibraryContentState(
            nextUp: .empty,
            fromFollows: .empty,
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
                fromFollows: .empty,
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
}
