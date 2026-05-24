import SwiftUI
import CoreImage
#if canImport(UIKit)
import UIKit
import QuartzCore
#endif

/// Reduce-motion is re-checked every tick (rather than once on start) so a runtime
/// toggle in Settings freezes the glow without needing the view to remount.
struct PodcastSpotlightView: View {
    let isActive: Bool
    let color: Color

    @StateObject private var driver = SpotlightBreathingDriver()

    var body: some View {
        GeometryReader { proxy in
            let dim = min(proxy.size.width, proxy.size.height)
            ZStack {
                RadialGradient(
                    colors: [
                        color.opacity(0.45 * driver.intensity),
                        color.opacity(0.18 * driver.intensity),
                        color.opacity(0)
                    ],
                    center: .center,
                    startRadius: dim * 0.08,
                    endRadius: dim * 0.62
                )
                .blur(radius: 24)
                .blendMode(.plusLighter)
            }
            .frame(width: proxy.size.width, height: proxy.size.height)
        }
        .allowsHitTesting(false)
        .onAppear { driver.update(isActive: isActive) }
        .onChange(of: isActive) { active in
            driver.update(isActive: active)
        }
        .onDisappear { driver.stop() }
    }
}

@MainActor
final class SpotlightBreathingDriver: ObservableObject {
    @Published private(set) var intensity: Double = 0

    #if canImport(UIKit)
    private var displayLink: CADisplayLink?
    #endif
    private var startTime: CFTimeInterval = 0

    private static let breathPeriod: CFTimeInterval = 4.2
    private static let staticReduceMotionIntensity: Double = 0.32
    private static let restingIntensity: Double = 0

    func update(isActive: Bool) {
        if isActive {
            start()
        } else {
            stop()
            intensity = Self.restingIntensity
        }
    }

    func start() {
        #if canImport(UIKit)
        stop()
        startTime = CACurrentMediaTime()
        let link = CADisplayLink(target: self, selector: #selector(tick))
        link.preferredFrameRateRange = CAFrameRateRange(minimum: 24, maximum: 30, preferred: 30)
        link.add(to: .main, forMode: .common)
        displayLink = link
        tick()
        #else
        intensity = Self.staticReduceMotionIntensity
        #endif
    }

    func stop() {
        #if canImport(UIKit)
        displayLink?.invalidate()
        displayLink = nil
        #endif
    }

    #if canImport(UIKit)
    @objc private func tick() {
        if UIAccessibility.isReduceMotionEnabled {
            intensity = Self.staticReduceMotionIntensity
            return
        }
        let elapsed = CACurrentMediaTime() - startTime
        let phase = (sin(elapsed * 2 * .pi / Self.breathPeriod) + 1) / 2
        intensity = 0.18 + phase * 0.55
    }
    #endif

    deinit {
        #if canImport(UIKit)
        MainActor.assumeIsolated {
            displayLink?.invalidate()
        }
        #endif
    }
}

#if canImport(UIKit)
/// Extract a single dominant color from an artwork image using CIAreaAverage. Run
/// off the main thread — CoreImage reduction over a 1000×1000 image is cheap but
/// not free, and the result is published back to @MainActor by the caller.
enum ArtworkDominantColor {
    private static let context = CIContext(options: [.workingColorSpace: kCFNull as Any])

    static func extract(from image: UIImage) -> UIColor? {
        guard let cgImage = image.cgImage else { return nil }
        let ciImage = CIImage(cgImage: cgImage)
        let extent = ciImage.extent
        let extentVector = CIVector(
            x: extent.origin.x,
            y: extent.origin.y,
            z: extent.size.width,
            w: extent.size.height
        )

        guard
            let filter = CIFilter(
                name: "CIAreaAverage",
                parameters: [
                    kCIInputImageKey: ciImage,
                    kCIInputExtentKey: extentVector
                ]
            ),
            let output = filter.outputImage
        else { return nil }

        var bitmap = [UInt8](repeating: 0, count: 4)
        context.render(
            output,
            toBitmap: &bitmap,
            rowBytes: 4,
            bounds: CGRect(x: 0, y: 0, width: 1, height: 1),
            format: .RGBA8,
            colorSpace: CGColorSpaceCreateDeviceRGB()
        )

        let raw = UIColor(
            red: CGFloat(bitmap[0]) / 255.0,
            green: CGFloat(bitmap[1]) / 255.0,
            blue: CGFloat(bitmap[2]) / 255.0,
            alpha: 1.0
        )

        return raw.tunedForChrome()
    }
}

extension UIColor {
    /// Push muddy artwork averages toward a saturated, readable chrome accent so the
    /// tab-bar tint doesn't decay into beige. Floors saturation and clamps lightness
    /// to a midtone band.
    func tunedForChrome() -> UIColor {
        var hue: CGFloat = 0
        var saturation: CGFloat = 0
        var brightness: CGFloat = 0
        var alpha: CGFloat = 0
        getHue(&hue, saturation: &saturation, brightness: &brightness, alpha: &alpha)

        let tunedSaturation = max(saturation, 0.55)
        let tunedBrightness = min(max(brightness, 0.45), 0.78)
        return UIColor(hue: hue, saturation: tunedSaturation, brightness: tunedBrightness, alpha: 1.0)
    }
}
#endif
