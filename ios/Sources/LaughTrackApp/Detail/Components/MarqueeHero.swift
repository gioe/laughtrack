import SwiftUI
import LaughTrackBridge

/// Marquee-style hero used across detail screens (show, club, comedian,
/// podcast). Treats the entity image as a square poster framed by a ring of
/// round dotted bulbs, evoking a theater marquee. Title sits above the
/// poster, an optional eyebrow above that, and badges / action buttons /
/// host chips stack below.
struct MarqueeHero: View {
    @Environment(\.appTheme) private var theme

    let title: String
    var eyebrow: String? = nil
    var titleTopPadding: CGFloat = 18
    let imageURL: String
    var thumbnailStyle: MarqueeHeroThumbnailStyle = .marqueePoster
    var thumbnailCaption: String? = nil
    var thumbnailHeadshots: [DetailHeroHeadshot] = []
    var badges: [DetailHeroBadge] = []
    var actions: [DetailHeroAction] = []
    var hosts: [DetailHeroHost] = []
    var openURL: ((URL) -> Void)? = nil
    var openComedian: ((Int) -> Void)? = nil
    var fallbackSystemImage: String = "ticket.fill"

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        VStack(spacing: 14) {
            // Spacer that preserves the title's y-position now that the
            // back/favorite chrome lives in a sticky overlay outside the
            // ScrollView. Same height as the original chromeBar (36pt).
            Color.clear.frame(height: 36)

            if let eyebrow, !eyebrow.isEmpty {
                Text(eyebrow)
                    .font(.system(size: 11, weight: .semibold, design: .rounded))
                    .tracking(2.2)
                    .textCase(.uppercase)
                    .foregroundStyle(laughTrack.colors.accentStrong)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
                    .padding(.horizontal, 24)
            }

            Text(title)
                .font(.system(size: 24, weight: .heavy, design: .rounded))
                .tracking(0.4)
                .textCase(.uppercase)
                .multilineTextAlignment(.center)
                .foregroundStyle(.white)
                .lineLimit(3)
                .minimumScaleFactor(0.7)
                .fixedSize(horizontal: false, vertical: true)
                .shadow(color: .black.opacity(0.6), radius: 4, x: 0, y: 2)
                .padding(.horizontal, 24)
                .padding(.top, titleTopPadding)

            heroThumbnail

            if !badges.isEmpty {
                HStack(spacing: theme.spacing.sm) {
                    ForEach(Array(badges.enumerated()), id: \.offset) { _, badge in
                        if badge.isLive {
                            LiveRecordingBadge(label: badge.title)
                        } else {
                            LaughTrackBadge(
                                badge.title,
                                systemImage: badge.systemImage,
                                tone: badge.tone
                            )
                        }
                    }
                }
            }

            if let openURL, !actions.isEmpty {
                let visibleActions = actions.filter { $0.url != nil }
                if !visibleActions.isEmpty {
                    HStack(spacing: theme.spacing.md) {
                        ForEach(Array(visibleActions.enumerated()), id: \.offset) { _, action in
                            if let url = action.url {
                                actionButton(action: action, url: url, openURL: openURL)
                            }
                        }
                    }
                }
            }

            if let openComedian, !hosts.isEmpty {
                HStack(spacing: theme.spacing.md) {
                    ForEach(hosts, id: \.id) { host in
                        hostChip(host: host, openComedian: openComedian)
                    }
                }
            }
        }
        .padding(.top, Self.statusBarOffset)
        .padding(.bottom, theme.spacing.lg)
        .frame(maxWidth: .infinity)
    }

    /// Status-bar clearance. Each detail view applies
    /// `.ignoresSafeArea(.container, edges: .top)` to its scroll container,
    /// so the marquee content is laid out from the physical top of the
    /// screen and has to manually offset past the status bar. The inset is
    /// read from the key window because `ignoresSafeArea` also zeroes the
    /// inset SwiftUI propagates to descendants, so a local GeometryReader
    /// would report 0 here. The -2 reproduces the previous fixed 60pt
    /// clearance on the 62pt-inset iPhone 17-class Dynamic Island sims the
    /// marquee's chrome/title spacing was designed against (the first 36pt
    /// is the clear chrome spacer below, so no content renders inside the
    /// status bar) — while notch and SE-class devices now track their real
    /// status-bar inset instead of inheriting Dynamic Island clearance.
    @MainActor
    private static var statusBarOffset: CGFloat {
        topSafeAreaInset - 2
    }

    /// Falls back to 62 (the iPhone 17-class Dynamic Island inset) when no
    /// key window is available — e.g. previews before a window becomes key,
    /// or the macOS `swift test` build — reproducing the previous fixed
    /// 60pt total.
    @MainActor
    private static var topSafeAreaInset: CGFloat {
        #if canImport(UIKit)
        UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows)
            .first(where: \.isKeyWindow)?
            .safeAreaInsets.top ?? 62
        #else
        62
        #endif
    }

    @ViewBuilder
    private var heroThumbnail: some View {
        switch thumbnailStyle {
        case .marqueePoster:
            MarqueePosterThumbnail(
                imageURL: imageURL,
                fallbackSystemImage: fallbackSystemImage
            )
        case .framedComedian:
            if thumbnailHeadshots.count > 1 {
                FramedComedianCarouselThumbnail(
                    headshots: thumbnailHeadshots,
                    fallbackSystemImage: fallbackSystemImage
                )
            } else {
                FramedComedianThumbnail(
                    imageURL: imageURL,
                    fallbackSystemImage: fallbackSystemImage,
                    caption: thumbnailCaption
                )
            }
        case .clubMarquee:
            ClubMarqueeThumbnail(
                imageURL: imageURL,
                fallbackSystemImage: fallbackSystemImage
            )
        case .podcastRail:
            PodcastRailThumbnail(
                imageURL: imageURL,
                fallbackSystemImage: fallbackSystemImage
            )
        }
    }

    @ViewBuilder
    private func actionButton(
        action: DetailHeroAction,
        url: URL,
        openURL: @escaping (URL) -> Void
    ) -> some View {
        let laughTrack = theme.laughTrackTokens

        Button {
            openURL(url)
        } label: {
            VStack(spacing: 2) {
                Image(systemName: action.systemImage)
                    .font(.system(size: theme.iconSizes.sm, weight: .bold))
                    .foregroundStyle(laughTrack.colors.textPrimary)
                    .frame(width: 40, height: 40)
                    .background(laughTrack.colors.surface.opacity(0.94))
                    .clipShape(Circle())
                    .overlay(
                        Circle().stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                    )

                Text(action.title)
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(.white)
                    .shadow(color: .black.opacity(0.6), radius: 3, x: 0, y: 2)
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel(action.title)
    }

    @ViewBuilder
    private func hostChip(host: DetailHeroHost, openComedian: @escaping (Int) -> Void) -> some View {
        let laughTrack = theme.laughTrackTokens
        let diameter: CGFloat = 64
        let ringInset: CGFloat = 5

        Button {
            openComedian(host.id)
        } label: {
            VStack(spacing: 6) {
                ZStack {
                    Group {
                        if
                            let imageURL = host.imageURL,
                            let url = URL.normalizedExternalURL(imageURL)
                        {
                            CachedAsyncImage(url: url) { image in
                                image.resizable().scaledToFill()
                            } placeholder: {
                                hostFallback(diameter: diameter)
                            } error: { _ in
                                hostFallback(diameter: diameter)
                            }
                        } else {
                            hostFallback(diameter: diameter)
                        }
                    }
                    .frame(width: diameter, height: diameter)
                    .clipShape(Circle())
                    .overlay(
                        Circle().stroke(Color.black.opacity(0.55), lineWidth: 1)
                    )

                    // Dashed bulb-ring matches the comedian poster frames used
                    // elsewhere (show lineup tiles, home rails) so hosts read
                    // as "tap me, this is a person" instead of small generic
                    // avatars.
                    Circle()
                        .strokeBorder(
                            laughTrack.colors.accentStrong,
                            style: StrokeStyle(
                                lineWidth: 1.6,
                                lineCap: .round,
                                lineJoin: .round,
                                dash: [0.5, 5]
                            )
                        )
                        .frame(width: diameter + ringInset, height: diameter + ringInset)
                        .shadow(color: laughTrack.colors.accentStrong.opacity(0.55), radius: 3)
                        .shadow(color: laughTrack.colors.accentStrong.opacity(0.25), radius: 7)
                }
                .frame(width: diameter + ringInset, height: diameter + ringInset)

                Text(host.name)
                    .font(laughTrack.typography.metadata.weight(.semibold))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
                    .frame(maxWidth: diameter + 24)
                    .shadow(color: .black.opacity(0.6), radius: 3, x: 0, y: 2)
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(host.name), host")
    }

    private func hostFallback(diameter: CGFloat) -> some View {
        let laughTrack = theme.laughTrackTokens
        return Circle()
            .fill(laughTrack.colors.surfaceMuted)
            .frame(width: diameter, height: diameter)
            .overlay {
                Image(systemName: "person.fill")
                    .font(.system(size: theme.iconSizes.md, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }
}

enum MarqueeHeroThumbnailStyle {
    case marqueePoster
    case framedComedian
    case clubMarquee
    case podcastRail
}

struct DetailHeroHeadshot: Identifiable, Hashable {
    let id: String
    let name: String
    let imageURL: String
}

struct MarqueePosterThumbnail: View {
    let imageURL: String
    let fallbackSystemImage: String

    @Environment(\.appTheme) private var theme
    @State private var imageLoadFailed = false
    /// Whether the loaded poster letterboxes (wide wordmark) or cover-crops.
    /// nil until the bitmap's intrinsic size has been read back from
    /// ImageCache — the poster shows the loading placeholder in that window
    /// so a wordmark never flashes cover-cropped first.
    @State private var posterLetterbox: Bool?

    static let posterSize: CGFloat = 196
    static let frameInset: CGFloat = 10

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            poster
                .frame(width: Self.posterSize, height: Self.posterSize)
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .stroke(Color.black.opacity(0.55), lineWidth: 1)
                )

            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(
                    laughTrack.colors.accentStrong,
                    style: StrokeStyle(
                        lineWidth: 3,
                        lineCap: .round,
                        lineJoin: .round,
                        dash: [0.5, 9]
                    )
                )
                .frame(
                    width: Self.posterSize + Self.frameInset,
                    height: Self.posterSize + Self.frameInset
                )
                .shadow(color: laughTrack.colors.accentStrong.opacity(0.65), radius: 6)
                .shadow(color: laughTrack.colors.accentStrong.opacity(0.3), radius: 14)
        }
    }

    @ViewBuilder
    private var poster: some View {
        let laughTrack = theme.laughTrackTokens
        let url = URL.normalizedExternalURL(imageURL)

        if let url, !imageLoadFailed {
            CachedAsyncImage(url: url) { image in
                posterContent(image: image, url: url)
            } placeholder: {
                Rectangle().fill(laughTrack.colors.surfaceElevated)
            } error: { _ in
                posterFallback
                    .onAppear { imageLoadFailed = true }
            }
        } else {
            posterFallback
        }
    }

    /// Treatment for a successfully loaded poster. Wide wordmark logos
    /// (aspect ratio ≥ `MarqueePosterLayout.logoAspectThreshold`) letterbox
    /// with scaledToFit plus padding on a surfaceMuted backing — mirroring
    /// the web show header's TASK-2787 treatment (object-contain p-3 on
    /// surface-muted) — while everything below the threshold keeps the
    /// original scaledToFill cover crop. The decision needs the bitmap's
    /// intrinsic size, which CachedAsyncImage's content closure doesn't
    /// expose; the loaded image is guaranteed to already be in ImageCache by
    /// the time this renders (the load path stores before flipping to
    /// .loaded), so the .task query is a memory hit. Until it resolves,
    /// render the same placeholder as the loading phase — the web hides the
    /// image until onLoad for the same no-flash reason.
    @ViewBuilder
    private func posterContent(image: Image, url: URL) -> some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            switch posterLetterbox {
            case nil:
                Rectangle().fill(laughTrack.colors.surfaceElevated)
            case true?:
                laughTrack.colors.surfaceMuted
                image
                    .resizable()
                    .scaledToFit()
                    .padding(MarqueePosterLayout.letterboxPadding)
            case false?:
                image
                    .resizable()
                    .scaledToFill()
            }
        }
        .task(id: url) {
            // Recompute unconditionally: the query is a guaranteed memory
            // hit, and an id-change re-fire (the hero URL swapped in place
            // under a persisting view identity) must repair the decision
            // rather than keep the previous image's treatment.
            let cached = await ImageCache.shared.image(for: url)
            posterLetterbox = cached.map {
                MarqueePosterLayout.shouldLetterbox(imageSize: $0.size)
            } ?? false
        }
    }

    private var posterFallback: some View {
        DetailThumbnailFallback(systemImage: fallbackSystemImage, iconSize: 64)
    }
}

struct FramedComedianThumbnail: View {
    let imageURL: String
    let fallbackSystemImage: String
    let caption: String?

    @Environment(\.appTheme) private var theme

    private static let headshotSize: CGFloat = 208
    private static let frameWidth: CGFloat = 244
    private static let frameHeight: CGFloat = 278
    private static let cornerRadius: CGFloat = 12

    var body: some View {
        if
            let caption = caption?.trimmingCharacters(in: .whitespacesAndNewlines),
            !caption.isEmpty
        {
            ClubWallHeadshotFrame(
                caption: caption,
                photoWidth: Self.headshotSize,
                photoHeight: Self.headshotSize,
                frameWidth: Self.frameWidth,
                frameHeight: Self.frameHeight,
                captionFontSize: 14,
                captionWidth: Self.headshotSize,
                captionHeight: 24,
                rotationDegrees: -0.4
            ) {
                thumbnailImage
            }
        } else {
            thumbnailImage
                .frame(width: Self.headshotSize, height: Self.headshotSize)
                .clipShape(RoundedRectangle(cornerRadius: Self.cornerRadius, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: Self.cornerRadius, style: .continuous)
                        .stroke(Color.black.opacity(0.58), lineWidth: 1.5)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: Self.cornerRadius + 4, style: .continuous)
                        .stroke(theme.laughTrackTokens.colors.accentStrong.opacity(0.62), lineWidth: 1)
                        .padding(-5)
                )
                .shadow(color: .black.opacity(0.42), radius: 12, y: 7)
                .rotationEffect(.degrees(-0.4))
        }
    }

    private var thumbnailImage: some View {
        DetailThumbnailImage(
            imageURL: imageURL,
            fallbackSystemImage: fallbackSystemImage,
            contentMode: .fill
        )
    }
}

private struct FramedComedianCarouselThumbnail: View {
    let headshots: [DetailHeroHeadshot]
    let fallbackSystemImage: String

    @State private var selectedIndex = 0
    @State private var pauseAutoAdvanceUntil = Date.distantPast

    private static let autoAdvanceInterval: UInt64 = 2_500_000_000
    private static let manualPauseDuration: TimeInterval = 5

    var body: some View {
        let selected = headshots[min(max(selectedIndex, 0), headshots.count - 1)]

        ZStack {
            FramedComedianThumbnail(
                imageURL: selected.imageURL,
                fallbackSystemImage: fallbackSystemImage,
                caption: selected.name
            )
            .id(selected.id)
            .transition(
                .asymmetric(
                    insertion: .move(edge: .trailing).combined(with: .opacity),
                    removal: .move(edge: .leading).combined(with: .opacity)
                )
            )
        }
        .animation(.spring(response: 0.38, dampingFraction: 0.84), value: selected.id)
        .highPriorityGesture(swipeGesture)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(selected.name), \(selectedIndex + 1) of \(headshots.count)")
        .task {
            await autoAdvance()
        }
    }

    private var swipeGesture: some Gesture {
        DragGesture(minimumDistance: 20)
            .onEnded { value in
                guard abs(value.translation.width) > abs(value.translation.height) else { return }
                pauseAutoAdvanceUntil = Date().addingTimeInterval(Self.manualPauseDuration)
                if value.translation.width < -32 {
                    advance()
                } else if value.translation.width > 32 {
                    retreat()
                }
            }
    }

    private func autoAdvance() async {
        while !Task.isCancelled {
            try? await Task.sleep(nanoseconds: Self.autoAdvanceInterval)
            guard !Task.isCancelled, Date() >= pauseAutoAdvanceUntil else { continue }
            advance()
        }
    }

    private func advance() {
        guard headshots.count > 1 else { return }
        selectedIndex = (selectedIndex + 1) % headshots.count
    }

    private func retreat() {
        guard headshots.count > 1 else { return }
        selectedIndex = (selectedIndex - 1 + headshots.count) % headshots.count
    }
}

struct ClubMarqueeThumbnail: View {
    let imageURL: String
    let fallbackSystemImage: String

    @Environment(\.appTheme) private var theme

    private static let clubBulbColor = Color(red: 1.0, green: 0.78, blue: 0.24)

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack {
            DetailThumbnailImage(
                imageURL: imageURL,
                fallbackSystemImage: fallbackSystemImage,
                contentMode: .fit
            )
            .frame(width: MarqueePosterThumbnail.posterSize, height: MarqueePosterThumbnail.posterSize)
            .background(laughTrack.colors.surfaceMuted)
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(Color.black.opacity(0.55), lineWidth: 1)
            )

            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(
                    Self.clubBulbColor,
                    style: StrokeStyle(
                        lineWidth: 2,
                        lineCap: .round,
                        lineJoin: .round,
                        dash: [1.2, 10]
                    )
                )
                .frame(
                    width: MarqueePosterThumbnail.posterSize + MarqueePosterThumbnail.frameInset,
                    height: MarqueePosterThumbnail.posterSize + MarqueePosterThumbnail.frameInset
                )
                .shadow(color: Self.clubBulbColor.opacity(0.70), radius: 4)
                .shadow(color: Self.clubBulbColor.opacity(0.34), radius: 9)
        }
    }
}

struct PodcastRailThumbnail: View {
    let imageURL: String
    let fallbackSystemImage: String

    @Environment(\.appTheme) private var theme

    private static let coverSize: CGFloat = 150
    private static let coverCornerRadius: CGFloat = 12
    private static let stageWidth: CGFloat = 224
    private static let stageHeight: CGFloat = 210

    var body: some View {
        ZStack {
            HomeMarqueeStageBackground(glowOpacity: 0.18)

            VStack(spacing: 12) {
                podcastCover
                waveformStrip
            }
        }
        .frame(width: Self.stageWidth, height: Self.stageHeight)
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

    private var podcastCover: some View {
        DetailThumbnailImage(
            imageURL: imageURL,
            fallbackSystemImage: fallbackSystemImage,
            contentMode: .fill
        )
        .frame(width: Self.coverSize, height: Self.coverSize)
        .clipShape(RoundedRectangle(cornerRadius: Self.coverCornerRadius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: Self.coverCornerRadius, style: .continuous)
                .stroke(Color.black.opacity(0.55), lineWidth: 1)
        )
        .overlay(alignment: .topTrailing) {
            rssBadge
                .padding(7)
        }
        .shadow(color: .black.opacity(0.42), radius: 10, y: 6)
    }

    private var rssBadge: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            Circle()
                .fill(Color.black.opacity(0.72))

            Image(systemName: "dot.radiowaves.left.and.right")
                .font(.system(size: 13, weight: .heavy))
                .foregroundStyle(laughTrack.colors.accentStrong)
        }
        .frame(width: 30, height: 30)
        .overlay(
            Circle()
                .stroke(laughTrack.colors.accentStrong.opacity(0.92), lineWidth: 1)
        )
        .shadow(color: laughTrack.colors.accentStrong.opacity(0.35), radius: 6)
    }

    private var waveformStrip: some View {
        let laughTrack = theme.laughTrackTokens

        return HStack(spacing: 4) {
            Image(systemName: "waveform")
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(laughTrack.colors.accentStrong.opacity(0.92))

            HStack(alignment: .center, spacing: 3) {
                ForEach(0..<9, id: \.self) { index in
                    Capsule(style: .continuous)
                        .fill(laughTrack.colors.accentStrong.opacity(0.92))
                        .frame(width: 3, height: CGFloat([8, 16, 11, 22, 13, 18, 9, 14, 7][index]))
                }
            }
        }
        .padding(.horizontal, 10)
        .frame(height: 24)
        .background(Color.black.opacity(0.36), in: Capsule(style: .continuous))
    }
}

private enum DetailThumbnailContentMode {
    case fill
    case fit
}

private struct DetailThumbnailImage: View {
    let imageURL: String
    let fallbackSystemImage: String
    var contentMode: DetailThumbnailContentMode = .fill

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens
        let url = URL.normalizedExternalURL(imageURL)

        Group {
            if let url {
                CachedAsyncImage(url: url) { image in
                    switch contentMode {
                    case .fill:
                        image.resizable().scaledToFill()
                    case .fit:
                        image.resizable().scaledToFit()
                    }
                } placeholder: {
                    Rectangle()
                        .fill(laughTrack.colors.surfaceMuted)
                        .overlay {
                            ProgressView()
                                .tint(laughTrack.colors.accent)
                        }
                } error: { _ in
                    DetailThumbnailFallback(systemImage: fallbackSystemImage)
                }
            } else {
                DetailThumbnailFallback(systemImage: fallbackSystemImage)
            }
        }
    }
}

private struct DetailThumbnailFallback: View {
    let systemImage: String
    var iconSize: CGFloat = 44

    @Environment(\.appTheme) private var theme

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: systemImage)
                    .font(.system(size: iconSize, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
            }
    }
}

// MARK: - Poster letterbox layout

/// Wide-wordmark exception to the square poster cover crop, mirroring the
/// web show header's LOGO_ASPECT_THRESHOLD treatment (TASK-2787): a 2026-06
/// survey of all 192 club CDN PNGs found every image at or beyond 2:1 is a
/// wordmark logo (Goodnights 3.8:1, Mic Drop 5.75:1) that cover-crops to an
/// illegible strip, while the 1.5–2:1 band is venue photos that center-crop
/// fine — so aspect ratio alone separates the populations and no background
/// heuristic is needed. Kept as a pure helper so the threshold decision is
/// unit-testable without rendering (TASK-2811).
enum MarqueePosterLayout {
    /// Width:height ratio at or beyond which the poster letterboxes. Must
    /// match the web's LOGO_ASPECT_THRESHOLD
    /// (apps/web/ui/pages/entity/show/header/index.tsx).
    static let logoAspectThreshold: CGFloat = 2

    /// Breathing room around a letterboxed wordmark — the pt mirror of the
    /// web's `p-3` (12px).
    static let letterboxPadding: CGFloat = 12

    /// Whether a loaded poster bitmap should letterbox (scaledToFit on a
    /// muted backing) instead of cover-cropping. Degenerate sizes (zero or
    /// negative height) keep the cover crop. Ratio of points is identical to
    /// ratio of pixels, so UIImage scale never skews the decision.
    static func shouldLetterbox(imageSize: CGSize) -> Bool {
        guard imageSize.height > 0 else { return false }
        return imageSize.width / imageSize.height >= logoAspectThreshold
    }
}

/// Pulsing red-dot "LIVE" badge used in place of the standard countdown badge
/// when a show is currently happening. The dot fades in and out on a 1.2s
/// loop, evoking a TV/recording on-air indicator.
private struct LiveRecordingBadge: View {
    let label: String

    @State private var isPulsing = false

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(Color.red)
                .frame(width: 9, height: 9)
                .shadow(color: .red.opacity(0.7), radius: 4)
                .opacity(isPulsing ? 0.35 : 1.0)
                .animation(
                    .easeInOut(duration: 0.6).repeatForever(autoreverses: true),
                    value: isPulsing
                )

            Text(label)
                .font(.system(size: 12, weight: .heavy, design: .rounded))
                .tracking(1.2)
                .foregroundStyle(.white)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(
            Capsule(style: .continuous)
                .fill(Color.red.opacity(0.18))
                .overlay(
                    Capsule(style: .continuous)
                        .stroke(Color.red.opacity(0.65), lineWidth: 1)
                )
        )
        .onAppear { isPulsing = true }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(label), happening now")
    }
}
