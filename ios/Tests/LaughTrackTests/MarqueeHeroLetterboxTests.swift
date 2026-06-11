import CoreGraphics
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
}
