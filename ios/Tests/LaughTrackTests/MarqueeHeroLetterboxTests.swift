import CoreGraphics
import Foundation
import Testing
@testable import LaughTrackApp

/// Pure-helper coverage for the marquee poster's wide-wordmark letterbox
/// decision (TASK-2811), the iOS mirror of the web show header's
/// LOGO_ASPECT_THRESHOLD treatment (TASK-2787).
@Suite("Marquee poster letterbox")
struct MarqueeHeroLetterboxTests {
    @Test("wide wordmark logos letterbox (Goodnights 475x125 live repro)")
    func wideWordmarkLetterboxes() {
        #expect(MarqueePosterLayout.shouldLetterbox(imageSize: CGSize(width: 475, height: 125)))
    }

    @Test("threshold is inclusive: exactly 2:1 letterboxes, mirroring web >=")
    func exactThresholdLetterboxes() {
        #expect(MarqueePosterLayout.shouldLetterbox(imageSize: CGSize(width: 392, height: 196)))
    }

    @Test("just below the threshold keeps the cover crop")
    func justBelowThresholdFills() {
        #expect(!MarqueePosterLayout.shouldLetterbox(imageSize: CGSize(width: 391, height: 196)))
    }

    @Test("venue photos in the 1.5-2:1 band keep the cover crop")
    func venuePhotoFills() {
        #expect(!MarqueePosterLayout.shouldLetterbox(imageSize: CGSize(width: 300, height: 200)))
    }

    @Test("square headshots and covers keep the cover crop")
    func squareImageFills() {
        #expect(!MarqueePosterLayout.shouldLetterbox(imageSize: CGSize(width: 196, height: 196)))
    }

    @Test("degenerate zero-height size keeps the cover crop instead of dividing by zero")
    func zeroHeightFills() {
        #expect(!MarqueePosterLayout.shouldLetterbox(imageSize: CGSize(width: 475, height: 0)))
    }

    @Test("threshold and padding mirror the web treatment (LOGO_ASPECT_THRESHOLD = 2, p-3 = 12px)")
    func constantsMirrorWeb() {
        #expect(MarqueePosterLayout.logoAspectThreshold == 2)
        #expect(MarqueePosterLayout.letterboxPadding == 12)
    }

    @Test("detail hero exposes named thumbnail primitive styles")
    func detailHeroExposesNamedThumbnailPrimitiveStyles() throws {
        let source = try String(contentsOf: detailComponentSourceURL(named: "MarqueeHero.swift"), encoding: .utf8)
        let clubBlock = try sourceBlock(
            in: source,
            from: "struct ClubMarqueeThumbnail",
            to: "struct PodcastRailThumbnail"
        )
        let comedianBlock = try sourceBlock(
            in: source,
            from: "struct FramedComedianThumbnail",
            to: "struct ClubMarqueeThumbnail"
        )

        #expect(source.contains("enum MarqueeHeroThumbnailStyle"))
        #expect(source.contains("case marqueePoster"))
        #expect(source.contains("case framedComedian"))
        #expect(source.contains("case clubMarquee"))
        #expect(source.contains("case podcastRail"))
        #expect(source.contains("struct FramedComedianThumbnail"))
        #expect(source.contains("struct ClubMarqueeThumbnail"))
        #expect(source.contains("struct PodcastRailThumbnail"))
        #expect(comedianBlock.contains("private static let headshotSize: CGFloat = 208"))
        #expect(comedianBlock.contains("HeadshotNameplate(name: caption)"))
        #expect(comedianBlock.contains("Text(name.uppercased())"))
        #expect(!comedianBlock.contains("ClubWallHeadshotFrame("))
        #expect(clubBlock.contains("private static let clubBulbColor = Color(red: 1.0, green: 0.78, blue: 0.24)"))
        #expect(clubBlock.contains("dash: [1.2, 10]"))
        #expect(!clubBlock.contains("laughTrack.colors.accentStrong"))
    }

    @Test("entity detail screens select their requested thumbnail primitive")
    func entityDetailScreensSelectRequestedThumbnailPrimitive() throws {
        let comedian = try String(contentsOf: detailViewSourceURL(named: "ComedianDetailView.swift"), encoding: .utf8)
        let club = try String(contentsOf: detailViewSourceURL(named: "ClubDetailView.swift"), encoding: .utf8)
        let podcast = try String(contentsOf: detailViewSourceURL(named: "PodcastDetailView.swift"), encoding: .utf8)
        let show = try String(contentsOf: detailViewSourceURL(named: "ShowDetailView.swift"), encoding: .utf8)

        #expect(comedian.contains("thumbnailStyle: .framedComedian(caption: comedian.name)"))
        #expect(club.contains("thumbnailStyle: .clubMarquee"))
        #expect(podcast.contains("thumbnailStyle: .podcastRail"))
        #expect(show.contains("thumbnailStyle: ShowDetailPresentation.heroThumbnailStyle(for: show)"))
        #expect(show.contains("static func heroThumbnailStyle(for show: Components.Schemas.ShowDetail) -> MarqueeHeroThumbnailStyle"))
    }

    private func detailComponentSourceURL(named fileName: String, filePath: String = #filePath) throws -> URL {
        try sourceURL(filePath: filePath, path: "Sources/LaughTrackApp/Detail/Components/\(fileName)")
    }

    private func detailViewSourceURL(named fileName: String, filePath: String = #filePath) throws -> URL {
        try sourceURL(filePath: filePath, path: "Sources/LaughTrackApp/Detail/Views/\(fileName)")
    }

    private func sourceURL(filePath: String, path: String) throws -> URL {
        let testFileURL = URL(fileURLWithPath: filePath)
        let iosRoot = testFileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot.appendingPathComponent(path)
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
