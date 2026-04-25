import Testing
@testable import LaughTrackApp

@Suite("Library view")
@MainActor
struct LibraryViewTests {
    @Test("library tab uses product-grade copy")
    func libraryUsesProductCopy() async throws {
        #expect(LibraryView.title == "Library")
    }
}
