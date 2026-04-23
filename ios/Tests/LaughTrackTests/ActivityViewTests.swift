import Testing
@testable import LaughTrackApp

@Suite("Activity view")
@MainActor
struct ActivityViewTests {
    @Test("activity tab has coherent empty state copy")
    func activityTabHasEmptyStateCopy() async throws {
        #expect(ActivityView.title == "Activity")
        #expect(ActivityView.emptyStateMessage == "Alerts and reminders will appear here.")
    }
}
