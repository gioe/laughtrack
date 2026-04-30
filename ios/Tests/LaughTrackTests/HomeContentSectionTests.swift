import Testing
@testable import LaughTrackApp

@Suite("Home content sections")
struct HomeContentSectionTests {
    @Test("unfiltered home includes shows comedians and clubs")
    func unfilteredHomeIncludesShowsComediansAndClubs() {
        #expect(HomeContentSection.sections(for: nil) == [
            .shows,
            .favoriteShows,
            .comedians,
            .clubs,
        ])
    }

    @Test("home primitive filters render only their matching content section")
    func homePrimitiveFiltersRenderOnlyMatchingContentSection() {
        #expect(HomeContentSection.sections(for: .shows) == [.shows])
        #expect(HomeContentSection.sections(for: .comedians) == [.comedians])
        #expect(HomeContentSection.sections(for: .clubs) == [.clubs])
    }
}
