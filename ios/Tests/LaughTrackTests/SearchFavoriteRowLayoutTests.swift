import Foundation
import Testing
@testable import LaughTrackApp

@Suite("Search favorite row layout")
struct SearchFavoriteRowLayoutTests {
    @Test("shared entity rows use dense vertical padding without reducing readable text")
    func sharedEntityRowsUseDenseVerticalMetrics() {
        let metrics = LaughTrackSearchEntityRowMetrics.standard

        #expect(metrics.verticalCardPadding == 4)
        #expect(metrics.titleLineLimit == 2)
        #expect(metrics.subtitleLineLimit == 2)
    }

    @Test("entity search result rows use the shared adaptive composition")
    func entitySearchRowsUseSharedAdaptiveComposition() throws {
        for fileName in [
            "ComediansDiscoveryView.swift",
            "ClubsDiscoveryView.swift",
            "PodcastSearchView.swift",
        ] {
            let source = try String(contentsOf: searchViewSourceURL(named: fileName), encoding: .utf8)
            #expect(source.contains("AdaptiveSearchResults(spacing: theme.spacing.md)"))
        }
    }

    @Test("comedian search favorite button is integrated into the entity row")
    func comedianSearchFavoriteButtonIsIntegratedIntoEntityRow() throws {
        let source = try String(contentsOf: searchViewSourceURL(named: "ComediansDiscoveryView.swift"), encoding: .utf8)
        let block = source[source.range(of: "struct ComedianRow: View")!.lowerBound...]

        #expect(block.contains("LaughTrackSearchEntityRow("))
        #expect(block.contains("action: openDetail"))
        #expect(block.contains("FavoriteButton("))
    }

    @Test("comedian search row uses captionless club wall headshot frame")
    func comedianSearchRowUsesCaptionlessClubWallHeadshotFrame() throws {
        let source = try String(contentsOf: browseComponentsSourceURL(), encoding: .utf8)
        let block = try sourceBlock(in: source, from: "struct LaughTrackSearchEntityRow", to: "struct LaughTrackEntityRowDesign")

        #expect(block.contains("ClubWallHeadshotFrame("))
        #expect(block.contains("caption: title"))
        #expect(block.contains("captionVisibility: .hidden"))
        #expect(block.contains("frameWidth: 76"))
        #expect(block.contains("frameHeight: 73"))
        #expect(block.contains(".frame(width: 69, height: 69)"))
        #expect(block.contains(".padding(.horizontal, laughTrack.browseDensity.compactCardPadding)"))
        #expect(block.contains(".padding(.vertical, metrics.verticalCardPadding)"))
        #expect(block.contains("artworkImage"))
        #expect(block.contains("Text(title)"))
        #expect(!block.contains("upcomingShowsText"))
        #expect(!block.contains("upcoming show"))
        #expect(!block.contains("rotationDegrees:"))
        #expect(!block.contains("HomeClubWallHeadshotFrame("))
    }

    @Test("shared entity rows announce distinguishing subtitle metadata")
    func sharedEntityRowsIncludeSubtitleInAccessibilityLabel() throws {
        let source = try String(contentsOf: browseComponentsSourceURL(), encoding: .utf8)
        let block = try sourceBlock(in: source, from: "struct LaughTrackSearchEntityRow", to: "struct LaughTrackEntityRowDesign")

        #expect(block.contains(".accessibilityLabel(rowAccessibilityLabel)"))
        #expect(block.contains("return \"\\(title), \\(subtitle)\""))
    }

    @Test("club wall headshot frame supports visible and hidden nameplate variants")
    func clubWallHeadshotFrameSupportsVisibleAndHiddenNameplateVariants() throws {
        let source = try String(contentsOf: componentSourceURL(named: "ClubWallHeadshotFrame.swift"), encoding: .utf8)

        #expect(source.contains("enum ClubWallHeadshotCaptionVisibility"))
        #expect(source.contains("case visible"))
        #expect(source.contains("case hidden"))
        #expect(source.contains("var captionVisibility: ClubWallHeadshotCaptionVisibility = .visible"))
        #expect(source.contains("var rotationDegrees: Double = 0"))
        #expect(source.contains("private var framedContent: some View"))
        #expect(source.contains("private var matInset: CGFloat"))
        #expect(source.contains("private var captionBottomMatInset: CGFloat"))
        #expect(source.contains("frameWidth > 110 ? 8 : 6"))
        #expect(source.contains(".padding(.top, matInset)"))
        #expect(source.contains(".padding(.horizontal, matInset)"))
        #expect(source.contains(".padding(.bottom, captionBottomMatInset)"))
        #expect(source.contains("if captionVisibility == .visible"))
        #expect(source.contains("captionText"))
        #expect(!source.contains("ZStack(alignment: .bottom)"))
        #expect(!source.contains("captionPlateBottomInset"))
        #expect(!source.contains("matBottomInset"))
    }

    @Test("podcast search favorite button is integrated into the entity row")
    func podcastSearchFavoriteButtonIsIntegratedIntoEntityRow() throws {
        let source = try String(contentsOf: searchViewSourceURL(named: "PodcastSearchView.swift"), encoding: .utf8)
        let block = try sourceBlock(in: source, from: "struct PodcastSearchRow: View", to: "private func toggle")

        #expect(block.contains("private func openPodcastDetail()"))
        #expect(block.contains("openPodcastDetail()"))
        #expect(block.contains("FavoriteButton("))
    }

    private func searchViewSourceURL(named fileName: String, filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Search/Views/\(fileName)")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }

    private func componentSourceURL(named fileName: String, filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("Sources/LaughTrackApp/Components/\(fileName)")
        guard FileManager.default.fileExists(atPath: sourceURL.path) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return sourceURL
    }

    private func browseComponentsSourceURL(filePath: String = #filePath) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        return iosRoot.appendingPathComponent(
            "Sources/LaughTrackApp/DesignSystem/LaughTrackBrowseComponents.swift"
        )
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
