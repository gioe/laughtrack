import Testing
@testable import LaughTrackApp

@Suite("Library view")
@MainActor
struct LibraryViewTests {
    @Test("library tab uses product-grade copy")
    func libraryUsesProductCopy() async throws {
        #expect(LibraryView.title == "Library")
    }

    @Test("library signed-out branch surfaces a sign-in prompt copy")
    func librarySignedOutPromptCopy() async throws {
        #expect(LibraryView.signedOutPromptTitle == "Sign in to see your saved comedians")
    }
}
