import Testing
@testable import LaughTrackApp

@Suite("Detail navigation chrome")
struct DetailNavigationChromeTests {
    @Test("detail chrome supplies compact titles for wrapping inline navigation")
    func entityDetailNavigationTitlesAreCompact() {
        #expect(DetailNavigationChrome.title(for: .club) == "Club")
        #expect(DetailNavigationChrome.title(for: .comedian) == "Comedian")
        #expect(DetailNavigationChrome.title(for: .show) == "Show")
    }

    @Test("entity detail hero extends behind the top safe area")
    func entityDetailHeroExtendsBehindTopSafeArea() {
        #expect(DetailNavigationChrome.extendsHeroBehindTopSafeArea)
    }
}
