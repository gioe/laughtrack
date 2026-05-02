import Testing
@testable import LaughTrackApp

@Suite("Comedian row")
struct ComedianRowTests {
    @Test("comedian row formats plural upcoming shows")
    func comedianRowFormatsPluralUpcomingShows() {
        #expect(ComedianRow.upcomingShowsText(for: 19) == "19 upcoming shows")
    }

    @Test("comedian row formats singular upcoming show")
    func comedianRowFormatsSingularUpcomingShow() {
        #expect(ComedianRow.upcomingShowsText(for: 1) == "1 upcoming show")
    }
}
