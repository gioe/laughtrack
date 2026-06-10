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

    @Test("status-bar scrim is opaque behind the clock and fades to clear")
    func statusBarScrimFadesFromOpaqueToClear() {
        let stops = DetailNavigationChrome.statusBarScrimStops

        // Fully opaque at the screen's top edge so scrolled content can
        // never collide with the status bar clock, fading to fully clear
        // at the bottom so it reads as a fade rather than a hard bar.
        #expect(stops.first?.opacity == 1.0)
        #expect(stops.first?.location == 0)
        #expect(stops.last?.opacity == 0.0)
        #expect(stops.last?.location == 1)

        // Locations must be monotonically non-decreasing for the gradient
        // to render as a single top-down fade.
        let locations = stops.map(\.location)
        #expect(locations == locations.sorted())
    }
}
