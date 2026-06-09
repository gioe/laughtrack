import SwiftUI
import LaughTrackBridge

/// Marquee-style hero used across detail screens (show, club, comedian,
/// podcast). Treats the entity image as a square poster framed by a ring of
/// round dotted bulbs, evoking a theater marquee. Title sits above the
/// poster, an optional eyebrow above that, and badges / action buttons /
/// host chips stack below.
struct MarqueeHero: View {
    @Environment(\.appTheme) private var theme
    @State private var imageLoadFailed = false

    let title: String
    var eyebrow: String? = nil
    let imageURL: String
    var badges: [DetailHeroBadge] = []
    var actions: [DetailHeroAction] = []
    var hosts: [DetailHeroHost] = []
    var openURL: ((URL) -> Void)? = nil
    var openComedian: ((Int) -> Void)? = nil
    var fallbackSystemImage: String = "ticket.fill"

    private static let posterSize: CGFloat = 196
    private static let frameInset: CGFloat = 10

    var body: some View {
        let laughTrack = theme.laughTrackTokens

        ZStack(alignment: .top) {
            marqueeBackground
                .ignoresSafeArea(.container, edges: .top)

            VStack(spacing: 14) {
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

                posterWithFrame

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
            .padding(.vertical, theme.spacing.lg)
            .frame(maxWidth: .infinity)
        }
    }

    private var marqueeBackground: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
            laughTrack.colors.heroStart

            RadialGradient(
                colors: [
                    laughTrack.colors.accent.opacity(0.18),
                    laughTrack.colors.accent.opacity(0.0)
                ],
                center: .center,
                startRadius: 20,
                endRadius: 260
            )
        }
    }

    private var posterWithFrame: some View {
        let laughTrack = theme.laughTrackTokens

        return ZStack {
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
                image
                    .resizable()
                    .scaledToFill()
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

    private var posterFallback: some View {
        let laughTrack = theme.laughTrackTokens

        return Rectangle()
            .fill(laughTrack.colors.surfaceMuted)
            .overlay {
                Image(systemName: fallbackSystemImage)
                    .font(.system(size: 64, weight: .semibold))
                    .foregroundStyle(laughTrack.colors.accentStrong)
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
        let diameter: CGFloat = 44

        Button {
            openComedian(host.id)
        } label: {
            VStack(spacing: 2) {
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
                    Circle().stroke(laughTrack.colors.borderSubtle, lineWidth: 1)
                )

                Text("Host")
                    .font(laughTrack.typography.metadata)
                    .foregroundStyle(.white)
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
