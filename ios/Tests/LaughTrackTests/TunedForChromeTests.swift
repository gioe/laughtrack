#if canImport(UIKit)
import Foundation
import Testing
import UIKit
@testable import LaughTrackApp

@Suite("UIColor.tunedForChrome")
struct TunedForChromeTests {
    @Test("beige averages get pushed above 0.55 saturation")
    func beigeBoost() {
        let beige = UIColor(hue: 0.10, saturation: 0.20, brightness: 0.60, alpha: 1.0)
        let tuned = beige.tunedForChrome()
        let (hue, saturation, brightness) = hsb(of: tuned)

        #expect(saturation >= 0.55)
        #expect(brightness >= 0.45 && brightness <= 0.78)
        #expect(abs(hue - 0.10) < 0.01)
    }

    @Test("already-saturated, midtone colors pass through unchanged")
    func alreadySaturatedPassthrough() {
        let saturated = UIColor(hue: 0.50, saturation: 0.85, brightness: 0.60, alpha: 1.0)
        let tuned = saturated.tunedForChrome()
        let (hue, saturation, brightness) = hsb(of: tuned)

        #expect(abs(hue - 0.50) < 0.01)
        #expect(abs(saturation - 0.85) < 0.01)
        #expect(abs(brightness - 0.60) < 0.01)
    }

    @Test("black is tuned without producing NaN")
    func blackEdgeCase() {
        let tuned = UIColor.black.tunedForChrome()
        let (_, saturation, brightness) = hsb(of: tuned)

        #expect(abs(saturation - 0.55) < 0.001)
        #expect(abs(brightness - 0.45) < 0.001)
        assertNoNaN(in: tuned)
    }

    @Test("white is tuned without producing NaN")
    func whiteEdgeCase() {
        let tuned = UIColor.white.tunedForChrome()
        let (_, saturation, brightness) = hsb(of: tuned)

        #expect(abs(saturation - 0.55) < 0.001)
        #expect(abs(brightness - 0.78) < 0.001)
        assertNoNaN(in: tuned)
    }
}

private func hsb(of color: UIColor) -> (CGFloat, CGFloat, CGFloat) {
    var h: CGFloat = 0, s: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
    color.getHue(&h, saturation: &s, brightness: &b, alpha: &a)
    return (h, s, b)
}

private func assertNoNaN(in color: UIColor) {
    var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
    color.getRed(&r, green: &g, blue: &b, alpha: &a)
    #expect(!r.isNaN)
    #expect(!g.isNaN)
    #expect(!b.isNaN)
    #expect(!a.isNaN)
}
#endif
