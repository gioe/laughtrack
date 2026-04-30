import Testing
@testable import LaughTrackApp

@Suite("Favorites view")
@MainActor
struct LibraryViewTests {
    @Test("favorites tab uses product-grade copy")
    func libraryUsesProductCopy() async throws {
        #expect(LibraryView.title == "Favorites")
    }

    @Test("favorites signed-out branch surfaces a sign-in prompt copy")
    func librarySignedOutPromptCopy() async throws {
        #expect(LibraryView.signedOutPromptTitle == "Sign in to see your favorites")
    }
}
