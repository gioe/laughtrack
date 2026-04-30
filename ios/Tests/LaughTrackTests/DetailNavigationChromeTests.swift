import Testing
@testable import LaughTrackApp

@Suite("Detail navigation chrome")
struct DetailNavigationChromeTests {
    @Test("club and comedian detail titles are hidden behind hero titles")
    func entityDetailNavigationTitlesAreHidden() {
        #expect(DetailNavigationChrome.title(for: .club) == "")
        #expect(DetailNavigationChrome.title(for: .comedian) == "")
    }

    @Test("entity detail hero extends behind the top safe area")
    func entityDetailHeroExtendsBehindTopSafeArea() {
        #expect(DetailNavigationChrome.extendsHeroBehindTopSafeArea)
    }
}
