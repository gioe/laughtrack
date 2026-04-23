import Testing
@testable import LaughTrackApp

@Suite("Activity view")
@MainActor
struct ActivityViewTests {
    @Test("activity empty state reads like a product surface")
    func activityUsesProductCopy() async throws {
        #expect(ActivityView.title == "Activity")
        #expect(ActivityView.emptyStateMessage == "Followed comics, saved reminders, and venue alerts will show up here.")
    }
}
