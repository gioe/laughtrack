import Foundation
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

    @Test("detail status bar scrim stays transparent over the page atmosphere")
    func detailStatusBarScrimStaysTransparentOverPageAtmosphere() throws {
        let source = try String(contentsOf: detailNavigationChromeSourceURL(), encoding: .utf8)
        let block = try sourceBlock(
            in: source,
            from: "struct DetailStatusBarScrim",
            to: "struct DetailBackButton"
        )

        #expect(block.contains("LinearGradient("))
        #expect(!block.contains("LaughTrackAtmosphereBackground()"))
        #expect(!block.contains("theme.laughTrackTokens.colors.canvas"))
    }

    private func detailNavigationChromeSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot.appendingPathComponent("Sources/LaughTrackApp/Detail/Components/DetailNavigationChrome.swift")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }

    private func sourceBlock(in source: String, from startMarker: String, to endMarker: String) throws -> String {
        guard
            let start = source.range(of: startMarker),
            let end = source.range(of: endMarker, range: start.upperBound..<source.endIndex)
        else {
            throw CocoaError(.fileReadCorruptFile)
        }

        return String(source[start.lowerBound..<end.lowerBound])
    }
}
