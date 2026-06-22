import SwiftUI

/// Shared "club stage" backdrop for the launch and first-entry surfaces: a
/// deep near-black canvas with a warm spotlight cone dropping from the top
/// edge, a pool of copper light where the brand mark sits, an edge vignette,
/// and a whisper of film grain. `intensity` (0...1) drives the lighting layers
/// so the splash can bloom the spotlight in over the static launch screen.
struct LaughTrackSpotlightBackdrop: View {
    @Environment(\.appTheme) private var theme

    var intensity: Double = 1
    /// Where the pool of light lands — aim it at the brand mark's position.
    var lightCenter: UnitPoint = UnitPoint(x: 0.5, y: 0.30)

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            // Base wash: canvas falling off to true black toward the floor.
            LinearGradient(
                colors: [
                    laughTrack.colors.canvas,
                    Color(red: 0.035, green: 0.025, blue: 0.018)
                ],
                startPoint: .top,
                endPoint: .bottom
            )

            // Lighting layers fade in together via a single animatable opacity.
            ZStack {
                // Pool of warm light behind the brand mark.
                RadialGradient(
                    colors: [
                        laughTrack.colors.accentStrong.opacity(0.30),
                        laughTrack.colors.accent.opacity(0.12),
                        .clear
                    ],
                    center: lightCenter,
                    startRadius: 0,
                    endRadius: 420
                )

                // Spotlight cone from the top edge.
                SpotlightConeShape()
                    .fill(
                        LinearGradient(
                            colors: [
                                Color(red: 1.0, green: 0.85, blue: 0.64).opacity(0.16),
                                .clear
                            ],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .blur(radius: 40)
            }
            .opacity(intensity)

            // Vignette pulls the corners back into the dark of the room.
            RadialGradient(
                colors: [.clear, Color.black.opacity(0.5)],
                center: .center,
                startRadius: 180,
                endRadius: 620
            )

            FilmGrain()
                .opacity(0.045)
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

private struct SpotlightConeShape: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        let topHalfWidth = rect.width * 0.10
        let bottomHalfWidth = rect.width * 0.55
        let depth = rect.height * 0.58
        path.move(to: CGPoint(x: rect.midX - topHalfWidth, y: -48))
        path.addLine(to: CGPoint(x: rect.midX + topHalfWidth, y: -48))
        path.addLine(to: CGPoint(x: rect.midX + bottomHalfWidth, y: depth))
        path.addLine(to: CGPoint(x: rect.midX - bottomHalfWidth, y: depth))
        path.closeSubpath()
        return path
    }
}

/// Static, deterministically-seeded speckle pass so the dark field reads as
/// texture instead of dead pixels. Drawn once per layout size.
private struct FilmGrain: View {
    var body: some View {
        Canvas { context, size in
            var seed: UInt64 = 0x9E3779B97F4A7C15
            func nextUnit() -> Double {
                seed = seed &* 6364136223846793005 &+ 1442695040888963407
                return Double(seed >> 11) / Double(UInt64.max >> 11)
            }

            let count = Int(size.width * size.height / 180)
            for _ in 0..<count {
                let x = nextUnit() * size.width
                let y = nextUnit() * size.height
                let alpha = 0.25 + nextUnit() * 0.75
                context.fill(
                    Path(CGRect(x: x, y: y, width: 1, height: 1)),
                    with: .color(.white.opacity(alpha))
                )
            }
        }
    }
}

struct AuthLoadingView: View {
    @Environment(\.appTheme) private var theme
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let logoNamespace: Namespace.ID

    @State private var spotlightLit = false

    var body: some View {
        let isAnimating = spotlightLit && !reduceMotion

        ZStack {
            // Match the static UILaunchScreen exactly at first render so the
            // system-splash handoff is invisible; the spotlight then blooms in.
            Color("LaunchBackground")
                .ignoresSafeArea()

            LaughTrackSpotlightBackdrop(
                intensity: spotlightLit ? 1 : 0,
                lightCenter: .center
            )
            .ignoresSafeArea()

            AnimatedLaunchSpotlight(isAnimating: isAnimating)
                .opacity(spotlightLit ? 1 : 0)
                .ignoresSafeArea()

            VStack(spacing: theme.spacing.lg) {
                AnimatedLaunchLogo(
                    logoNamespace: logoNamespace,
                    isAnimating: isAnimating
                )

                LoadingMarqueeBulbs(isAnimating: isAnimating)
                    .opacity(spotlightLit ? 1 : 0)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .onAppear {
            guard !reduceMotion else {
                spotlightLit = true
                return
            }
            withAnimation(.easeOut(duration: 0.9).delay(0.12)) {
                spotlightLit = true
            }
        }
    }
}

private struct AnimatedLaunchLogo: View {
    @Environment(\.appTheme) private var theme

    let logoNamespace: Namespace.ID
    let isAnimating: Bool

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        TimelineView(.animation(paused: !isAnimating)) { context in
            let pulse = isAnimating ? Self.pulse(at: context.date) : 0
            let glow = 0.34 + pulse * 0.14

            Image("LaunchLogo")
                .matchedGeometryEffect(id: "launch-logo", in: logoNamespace)
                .scaleEffect(1 + pulse * 0.018)
                .shadow(
                    color: laughTrack.colors.accent.opacity(glow),
                    radius: 34 + pulse * 18,
                    y: 8
                )
        }
    }

    private static func pulse(at date: Date) -> Double {
        let elapsed = date.timeIntervalSinceReferenceDate
        return (sin(elapsed * 2 * .pi / 2.6) + 1) / 2
    }
}

private struct AnimatedLaunchSpotlight: View {
    @Environment(\.appTheme) private var theme

    let isAnimating: Bool

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        TimelineView(.animation(paused: !isAnimating)) { context in
            let elapsed = context.date.timeIntervalSinceReferenceDate
            let sweep = isAnimating ? sin(elapsed * 2 * .pi / 4.8) : 0
            let shimmer = isAnimating ? (sin(elapsed * 2 * .pi / 2.2) + 1) / 2 : 0.55
            let center = UnitPoint(x: 0.5 + sweep * 0.11, y: 0.42)

            ZStack {
                RadialGradient(
                    colors: [
                        laughTrack.colors.accentStrong.opacity(0.22 + shimmer * 0.08),
                        laughTrack.colors.accent.opacity(0.12 + shimmer * 0.05),
                        .clear
                    ],
                    center: center,
                    startRadius: 0,
                    endRadius: 360
                )

                SpotlightConeShape()
                    .fill(
                        LinearGradient(
                            colors: [
                                Color(red: 1.0, green: 0.84, blue: 0.60).opacity(0.10 + shimmer * 0.05),
                                .clear
                            ],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .blur(radius: 34)
                    .rotationEffect(.degrees(sweep * 4), anchor: .top)
            }
            .allowsHitTesting(false)
            .accessibilityHidden(true)
        }
    }
}

private struct LoadingMarqueeBulbs: View {
    @Environment(\.appTheme) private var theme

    let isAnimating: Bool

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        TimelineView(.animation(paused: !isAnimating)) { context in
            let elapsed = context.date.timeIntervalSinceReferenceDate

            HStack(spacing: 12) {
                ForEach(0..<5, id: \.self) { index in
                    // Hoist every arithmetic subexpression into an explicitly
                    // typed binding. Inlining these in the .fill/.frame/.shadow
                    // modifiers forces the type-checker through combinatorial
                    // Double/CGFloat overload resolution and times out
                    // ("unable to type-check this expression in reasonable
                    // time"); the explicit Double annotations collapse it.
                    let wave: Double = isAnimating
                        ? (sin(elapsed * 2 * .pi / 1.8 + Double(index) * 0.65) + 1) / 2
                        : 0.65
                    let fillOpacity: Double = 0.35 + wave * 0.55
                    let diameter: Double = 5 + wave * 2
                    let shadowOpacity: Double = 0.35 + wave * 0.45
                    let shadowRadius: Double = 4 + wave * 7

                    Circle()
                        .fill(laughTrack.colors.accentStrong.opacity(fillOpacity))
                        .frame(width: diameter, height: diameter)
                        .shadow(
                            color: laughTrack.colors.accentStrong.opacity(shadowOpacity),
                            radius: shadowRadius
                        )
                }
            }
        }
        .accessibilityHidden(true)
    }
}
